import os
import sys
import json
import time
import hmac
import hashlib
import sqlite3
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi.testclient import TestClient
from fastapi import WebSocketDisconnect

# Add project root to sys.path
workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)

from api import app, generate_jwt, STRIPE_WEBHOOK_SECRET
from core.ledger import FinancialLedger
from core.audit_ledger import AuditLedger
from core.account_manager import AccountManager
from core.billing import (
    TenantStatusManager,
    TenantRateLimiter,
    TenantRateLimitError,
    TenantSubscriptionInactiveError
)
from core.providers import ProviderFactory

@pytest.fixture
def anyio_backend():
    return "asyncio"

@pytest.fixture
def api_client():
    return TestClient(app)

@pytest.fixture
def test_workspace(tmp_path):
    with patch("api.workspace", str(tmp_path)):
        old_env = os.environ.get("AGENT_WORKSPACE_DIR")
        os.environ["AGENT_WORKSPACE_DIR"] = str(tmp_path)
        
        fl = FinancialLedger(str(tmp_path))
        al = AuditLedger(str(tmp_path))
        am = AccountManager(str(tmp_path))
        
        # Write dummy accounts.json
        accounts_data = {
            "accounts": [
                {
                    "id": "primary-acc",
                    "provider": "google-genai",
                    "model": "gemini-2.5-flash",
                    "api_key": "primary-key",
                    "token_budget": 10000,
                    "tokens_used": 0,
                    "is_active": True
                }
            ]
        }
        with open(os.path.join(str(tmp_path), "accounts.json"), "w") as f:
            json.dump(accounts_data, f)
            
        yield tmp_path
        
        if old_env:
            os.environ["AGENT_WORKSPACE_DIR"] = old_env
        else:
            os.environ.pop("AGENT_WORKSPACE_DIR", None)

def dispatch_webhook(client, workspace_path, event_type, data_object):
    payload = {
        "id": f"evt_{event_type}",
        "type": event_type,
        "data": {
            "object": data_object
        }
    }
    payload_bytes = json.dumps(payload).encode("utf-8")
    timestamp = str(int(time.time()))
    secret = STRIPE_WEBHOOK_SECRET
    sig_basestring = f"{timestamp}.".encode("utf-8") + payload_bytes
    computed_hash = hmac.new(secret.encode("utf-8"), sig_basestring, hashlib.sha256).hexdigest()
    sig_header = f"t={timestamp},v1={computed_hash}"
    
    with patch("api.workspace", str(workspace_path)):
        response = client.post(
            "/v1/billing/stripe/webhook",
            content=payload_bytes,
            headers={"stripe-signature": sig_header, "Content-Type": "application/json"}
        )
    return response

def test_stripe_subscription_webhook_lifecycle(test_workspace, api_client):
    ledger = FinancialLedger(str(test_workspace))
    status_mgr = TenantStatusManager(ledger)
    
    # 1. customer.subscription.created -> active
    response = dispatch_webhook(api_client, test_workspace, "customer.subscription.created", {
        "id": "sub_test1",
        "customer": "cus_tenant_a",
        "metadata": {"tenant_id": "tenant_a"}
    })
    assert response.status_code == 200
    assert status_mgr.get_tenant_status("tenant_a") == "active"
    
    # 2. customer.subscription.updated with active status -> active
    response = dispatch_webhook(api_client, test_workspace, "customer.subscription.updated", {
        "id": "sub_test1",
        "customer": "cus_tenant_a",
        "status": "trialing",
        "metadata": {"tenant_id": "tenant_a"}
    })
    assert response.status_code == 200
    assert status_mgr.get_tenant_status("tenant_a") == "active"
    
    # 3. customer.subscription.updated with past_due -> frozen
    response = dispatch_webhook(api_client, test_workspace, "customer.subscription.updated", {
        "id": "sub_test1",
        "customer": "cus_tenant_a",
        "status": "past_due",
        "metadata": {"tenant_id": "tenant_a"}
    })
    assert response.status_code == 200
    assert status_mgr.get_tenant_status("tenant_a") == "frozen"
    
    # 4. invoice.payment_failed -> frozen
    response = dispatch_webhook(api_client, test_workspace, "invoice.payment_failed", {
        "subscription": "sub_test1",
        "customer": "cus_tenant_a",
        "metadata": {"tenant_id": "tenant_a"}
    })
    assert response.status_code == 200
    assert status_mgr.get_tenant_status("tenant_a") == "frozen"
    
    # 5. customer.subscription.deleted -> canceled
    response = dispatch_webhook(api_client, test_workspace, "customer.subscription.deleted", {
        "id": "sub_test1",
        "customer": "cus_tenant_a",
        "metadata": {"tenant_id": "tenant_a"}
    })
    assert response.status_code == 200
    assert status_mgr.get_tenant_status("tenant_a") == "canceled"

def test_tenant_access_control_gating(test_workspace, api_client):
    ledger = FinancialLedger(str(test_workspace))
    status_mgr = TenantStatusManager(ledger)
    
    # Setup token for tenant_blocked
    token = generate_jwt({"tenant_id": "tenant_blocked", "exp": time.time() + 60})
    headers = {"Authorization": f"Bearer {token}", "x-enforce-auth": "true"}
    
    # Active status (default or explicit) should succeed
    status_mgr.update_tenant_status("tenant_blocked", "active")
    with patch("api.workspace", str(test_workspace)):
        response = api_client.get("/v1/billing/saas/invoice", headers=headers)
        assert response.status_code == 200
        
    # Frozen status should return 403 Forbidden
    status_mgr.update_tenant_status("tenant_blocked", "frozen")
    with patch("api.workspace", str(test_workspace)):
        response = api_client.get("/v1/billing/saas/invoice", headers=headers)
        assert response.status_code == 403
        assert "frozen" in response.json()["detail"].lower()
        
    # Canceled status should return 403 Forbidden
    status_mgr.update_tenant_status("tenant_blocked", "canceled")
    with patch("api.workspace", str(test_workspace)):
        response = api_client.get("/v1/billing/saas/invoice", headers=headers)
        assert response.status_code == 403
        assert "canceled" in response.json()["detail"].lower()

def test_websocket_inactive_subscription_close(test_workspace, api_client):
    ledger = FinancialLedger(str(test_workspace))
    status_mgr = TenantStatusManager(ledger)
    
    token = generate_jwt({"tenant_id": "tenant_blocked_ws", "exp": time.time() + 60})
    
    # Frozen closed with 4003
    status_mgr.update_tenant_status("tenant_blocked_ws", "frozen")
    with patch("api.workspace", str(test_workspace)):
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with api_client.websocket_connect(f"/v1/stream?token={token}&enforce_auth=true") as ws:
                ws.receive_json()
        assert exc_info.value.code == 4003
        
    # Canceled closed with 4003
    status_mgr.update_tenant_status("tenant_blocked_ws", "canceled")
    with patch("api.workspace", str(test_workspace)):
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with api_client.websocket_connect(f"/v1/stream?token={token}&enforce_auth=true") as ws:
                ws.receive_json()
        assert exc_info.value.code == 4003

def test_rate_limiting_rest_and_websockets(test_workspace, api_client):
    ledger = FinancialLedger(str(test_workspace))
    status_mgr = TenantStatusManager(ledger)
    
    token = generate_jwt({"tenant_id": "tenant_limited", "exp": time.time() + 60})
    headers = {"Authorization": f"Bearer {token}", "x-enforce-auth": "true"}
    
    status_mgr.update_tenant_status("tenant_limited", "active")
    
    # 1. Under limit: should succeed
    with patch("api.workspace", str(test_workspace)):
        response = api_client.get("/v1/billing/saas/invoice", headers=headers)
        assert response.status_code == 200
        
    # Inject token usage (5000+ tokens)
    ledger.record_transaction(
        session_id="s1",
        account_id="primary-acc",
        provider="google-genai",
        model="gemini-2.5-flash",
        prompt_tokens=3000,
        completion_tokens=2500,
        tenant_id="tenant_limited"
    )
    
    # 2. Over limit: REST returns 429 Too Many Requests
    with patch("api.workspace", str(test_workspace)):
        response = api_client.get("/v1/billing/saas/invoice", headers=headers)
        assert response.status_code == 429
        assert "rate limit exceeded" in response.json()["detail"].lower()
        
    # 3. Over limit: WebSocket closes with code 4029
    with patch("api.workspace", str(test_workspace)):
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with api_client.websocket_connect(f"/v1/stream?token={token}&enforce_auth=true") as ws:
                ws.receive_json()
        assert exc_info.value.code == 4029

@pytest.mark.anyio
async def test_rate_limit_llm_provider_blocking_no_failover(test_workspace):
    ledger = FinancialLedger(str(test_workspace))
    status_mgr = TenantStatusManager(ledger)
    
    # Ensure tenant has active subscription status but has exceeded rate limit
    status_mgr.update_tenant_status("tenant_llm_limited", "active")
    ledger.record_transaction(
        session_id="session-limited",
        account_id="primary-acc",
        provider="google-genai",
        model="gemini-2.5-flash",
        prompt_tokens=4000,
        completion_tokens=1500,
        tenant_id="tenant_llm_limited"
    )
    
    am = AccountManager(str(test_workspace))
    am.register_session_tenant("session-limited", "tenant_llm_limited")
    
    # Create the provider
    prov = ProviderFactory.get_provider("google-genai", api_key="test")
    
    # Mock the underlying complete method to ensure it doesn't get called if rate limited
    prov.complete = AsyncMock(return_value=("text", "ok"))
    
    # Verify rate limit error is raised and complete is not called
    with pytest.raises(TenantRateLimitError):
        await prov.generate_content("system", [], [], {"session_id": "session-limited"})
        
    assert not prov.complete.called
