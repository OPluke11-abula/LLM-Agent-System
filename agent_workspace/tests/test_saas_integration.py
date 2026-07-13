import os
import sys
import json
import time
import hmac
import hashlib
os.environ.setdefault("LAS_JWT_SECRET", "test-only-secret-for-phase-72-auth-claims")
os.environ.setdefault("STRIPE_WEBHOOK_SECRET", "whsec_test_secret")
os.environ.setdefault("STRIPE_SUB_ITEM_TENANT_A", "si_tenant_a")
os.environ.setdefault("STRIPE_SUB_ITEM_TENANT_B", "si_tenant_b")
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi.testclient import TestClient
from fastapi import WebSocketDisconnect

# Add project root to sys.path
workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)

from api import API_KEYS, app, generate_jwt, verify_jwt, sync_billing_to_stripe
from routes.admin import verify_stripe_signature
from core.ledger import FinancialLedger
from core.billing import TenantStatusManager
from core.audit_ledger import AuditLedger
from core.account_manager import AccountManager
from core.providers import BaseLLMProvider, ProviderFactory

STRIPE_TEST_SECRET = "whsec_test_secret"


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def auth_test_config(monkeypatch):
    monkeypatch.setenv("LAS_JWT_SECRET", "test-only-secret-for-phase-72-auth-claims")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test_secret")
    monkeypatch.setattr("routes.admin.STRIPE_WEBHOOK_SECRET", STRIPE_TEST_SECRET)
    monkeypatch.setattr("routes.admin.STRIPE_TENANT_SUBSCRIPTION_ITEMS", {"tenant_a": "si_tenant_a", "tenant_b": "si_tenant_b"})
    API_KEYS.clear()
    API_KEYS.update({
        "key-tenant-a": "tenant_a",
        "key-tenant-b": "tenant_b",
        "key-admin": {"tenant_id": "admin_tenant", "role": "admin", "scope": "admin:read admin:write auth:mint"},
    })
    yield
    API_KEYS.clear()


@pytest.fixture
def api_client():
    return TestClient(app)


@pytest.fixture
def test_workspace(tmp_path):
    # Patch workspace in api
    with patch("api.workspace", str(tmp_path)):
        # Set environment variable for providers/account_manager
        old_env = os.environ.get("AGENT_WORKSPACE_DIR")
        os.environ["AGENT_WORKSPACE_DIR"] = str(tmp_path)
        
        # Initialize ledgers
        fl = FinancialLedger(str(tmp_path))
        al = AuditLedger(str(tmp_path))
        
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
                },
                {
                    "id": "fallback-acc",
                    "provider": "openai",
                    "model": "gpt-4o",
                    "api_key": "fallback-key",
                    "token_budget": 50000,
                    "tokens_used": 0,
                    "is_active": False
                }
            ],
            "active_account_id": "primary-acc"
        }
        accounts_file = tmp_path / "accounts.json"
        accounts_file.write_text(json.dumps(accounts_data, indent=2), encoding="utf-8")
        
        yield tmp_path
        
        # Cleanup
        if old_env is not None:
            os.environ["AGENT_WORKSPACE_DIR"] = old_env
        else:
            os.environ.pop("AGENT_WORKSPACE_DIR", None)
        
        # Reset AccountManager failovers
        AccountManager.clear_failovers()


def test_workspace_config_endpoint(test_workspace, api_client):
    """Verify that the /v1/workspace/config endpoint returns filtered tasks by tenant_id."""
    workspace_path = test_workspace / "agent_workspace"
    workspace_path.mkdir(exist_ok=True)
    
    workspace_dir = test_workspace / "workspace"
    workspace_dir.mkdir(exist_ok=True)
    
    workspace_json = workspace_dir / "workspace.json"
    dummy_config = {
        "tasks": [
            {"id": "task-a1", "tenant_id": "tenant_a", "name": "Task A1"},
            {"id": "task-b1", "tenant_id": "tenant_b", "name": "Task B1"},
            {"id": "task-default", "tenant_id": "default_tenant", "name": "Task Default"}
        ]
    }
    workspace_json.write_text(json.dumps(dummy_config), encoding="utf-8")
    
    with patch("api.workspace", str(workspace_path)):
        # Test with Tenant A
        headers_a = {"x-api-key": "key-tenant-a", "x-enforce-auth": "true"}
        response_a = api_client.get("/v1/workspace/config", headers=headers_a)
        assert response_a.status_code == 200
        data_a = response_a.json()
        assert len(data_a["tasks"]) == 1
        assert data_a["tasks"][0]["id"] == "task-a1"
        
        # Test with Tenant B
        headers_b = {"x-api-key": "key-tenant-b", "x-enforce-auth": "true"}
        response_b = api_client.get("/v1/workspace/config", headers=headers_b)
        assert response_b.status_code == 200
        data_b = response_b.json()
        assert len(data_b["tasks"]) == 1
        assert data_b["tasks"][0]["id"] == "task-b1"


def test_stripe_webhook_signature_verification(test_workspace, api_client):
    """Verify that Stripe webhook signature validation accepts valid and rejects invalid signatures."""
    payload = {"id": "evt_test", "type": "payment_intent.succeeded"}
    payload_bytes = json.dumps(payload).encode("utf-8")
    
    timestamp = str(int(time.time()))
    secret = STRIPE_TEST_SECRET
    
    # Construct valid Stripe signature
    sig_basestring = f"{timestamp}.".encode("utf-8") + payload_bytes
    computed_hash = hmac.new(secret.encode("utf-8"), sig_basestring, hashlib.sha256).hexdigest()
    valid_header = f"t={timestamp},v1={computed_hash}"
    
    with patch("api.workspace", str(test_workspace)):
        # Test valid webhook signature
        response = api_client.post(
            "/v1/billing/stripe/webhook",
            content=payload_bytes,
            headers={"stripe-signature": valid_header, "Content-Type": "application/json"}
        )
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        assert response.json()["event"] == "payment_intent.succeeded"
        
        # Test invalid webhook signature
        invalid_header = f"t={timestamp},v1=invalid_hash_value"
        response = api_client.post(
            "/v1/billing/stripe/webhook",
            content=payload_bytes,
            headers={"stripe-signature": invalid_header, "Content-Type": "application/json"}
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "Invalid Stripe signature"
        
        # Test missing signature header
        response = api_client.post(
            "/v1/billing/stripe/webhook",
            content=payload_bytes,
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "Missing Stripe signature header"


def test_stripe_signature_rejects_stale_timestamp():
    payload_bytes = b'{"id":"evt_stale","type":"payment_intent.succeeded"}'
    timestamp = str(int(time.time()) - 301)
    digest = hmac.new(
        STRIPE_TEST_SECRET.encode(),
        f"{timestamp}.".encode() + payload_bytes,
        hashlib.sha256,
    ).hexdigest()
    assert not verify_stripe_signature(payload_bytes, f"t={timestamp},v1={digest}", STRIPE_TEST_SECRET)


def test_stripe_webhook_replay_and_tenant_binding(test_workspace, api_client):
    payload = {
        "id": "evt_replay",
        "type": "customer.subscription.created",
        "data": {"object": {"id": "sub_replay", "customer": "cus_replay", "metadata": {"tenant_id": "tenant_a"}}},
    }
    payload_bytes = json.dumps(payload).encode()
    timestamp = str(int(time.time()))
    digest = hmac.new(STRIPE_TEST_SECRET.encode(), f"{timestamp}.".encode() + payload_bytes, hashlib.sha256).hexdigest()
    headers = {"stripe-signature": f"t={timestamp},v1={digest}", "Content-Type": "application/json"}
    with patch("api.workspace", str(test_workspace)):
        first = api_client.post("/v1/billing/stripe/webhook", content=payload_bytes, headers=headers)
        second = api_client.post("/v1/billing/stripe/webhook", content=payload_bytes, headers=headers)
    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["status"] == "duplicate"

    ledger = FinancialLedger(str(test_workspace))
    TenantStatusManager(ledger).update_tenant_status("tenant_a", "active", stripe_customer_id="cus_bound")
    conflicting = {**payload, "id": "evt_conflict", "data": {"object": {"id": "sub_bound", "customer": "cus_bound", "metadata": {"tenant_id": "tenant_b"}}}}
    conflicting_bytes = json.dumps(conflicting).encode()
    digest = hmac.new(STRIPE_TEST_SECRET.encode(), f"{timestamp}.".encode() + conflicting_bytes, hashlib.sha256).hexdigest()
    with patch("api.workspace", str(test_workspace)):
        response = api_client.post(
            "/v1/billing/stripe/webhook",
            content=conflicting_bytes,
            headers={"stripe-signature": f"t={timestamp},v1={digest}", "Content-Type": "application/json"},
        )
    assert response.status_code == 400


def test_stripe_billing_sync(test_workspace):
    """Verify Stripe usage sync aggregates transactions and tracks synced metadata state."""
    workspace_path = test_workspace / "agent_workspace"
    workspace_path.mkdir(exist_ok=True)
    
    ledger = FinancialLedger(str(workspace_path))
    
    # Record transactions for tenant_a and tenant_b
    ledger.record_transaction(
        session_id="session-a",
        account_id="primary-acc",
        provider="google-genai",
        model="gemini-2.5-flash",
        prompt_tokens=1000,
        completion_tokens=2000,
        tenant_id="tenant_a",
        markup_multiplier=1.5
    )
    
    ledger.record_transaction(
        session_id="session-b",
        account_id="primary-acc",
        provider="google-genai",
        model="gemini-2.5-flash",
        prompt_tokens=5000,
        completion_tokens=5000,
        tenant_id="tenant_b",
        markup_multiplier=1.5
    )
    
    with patch("api.workspace", str(workspace_path)):
        import api
        orig_key = api.STRIPE_API_KEY
        
        api.STRIPE_API_KEY = "mock_stripe_key"
        
        import asyncio
        asyncio.run(sync_billing_to_stripe())
        
        # Verify SQLite metadata was written
        import sqlite3
        conn = sqlite3.connect(str(ledger.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("SELECT tenant_id, last_synced_id FROM stripe_sync_metadata")
        rows = cursor.fetchall()
        sync_state = {r["tenant_id"]: r["last_synced_id"] for r in rows}
        conn.close()
        
        assert sync_state == {}
        
        # 2. Test live httpx synchronization path for new transactions
        ledger.record_transaction(
            session_id="session-a-2",
            account_id="primary-acc",
            provider="google-genai",
            model="gemini-2.5-flash",
            prompt_tokens=100,
            completion_tokens=200,
            tenant_id="tenant_a",
            markup_multiplier=1.5
        )  # ID = 3
        
        api.STRIPE_API_KEY = "sk_test_actual_key"
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "OK"
        
        mock_post = AsyncMock(return_value=mock_response)
        
        with patch("httpx.AsyncClient.post", mock_post):
            asyncio.run(sync_billing_to_stripe())
            
            # Verify POST HTTP payload and parameters
            assert mock_post.call_count == 2
            calls = {call.args[0]: call for call in mock_post.call_args_list}
            called = calls["https://api.stripe.com/v1/subscription_items/si_tenant_a/usage_records"]
            called_headers = called.kwargs["headers"]
            called_body = called.kwargs["content"]
            
            assert "si_tenant_a" in called.args[0]
            assert called_headers["Authorization"] == "Bearer sk_test_actual_key"
            assert "quantity=3300" in called_body
            assert "action=increment" in called_body
            
        # Verify db metadata updated
        conn = sqlite3.connect(str(ledger.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("SELECT tenant_id, last_synced_id FROM stripe_sync_metadata WHERE tenant_id = 'tenant_a'")
        row = cursor.fetchone()
        conn.close()
        assert row["last_synced_id"] == 3
        
        # Restore API Key
        api.STRIPE_API_KEY = orig_key


@pytest.mark.asyncio
async def test_model_sla_failover_guard(test_workspace):
    """Verify that provider failure triggers failover, audit logs event and adjusted markup multiplier in ledger."""
    workspace_path = test_workspace
    
    # Initialize AccountManager with the mock workspace directory
    am = AccountManager(str(workspace_path))
    AccountManager.register_session_tenant("failover-session-id", "tenant_a")
    
    # Setup custom providers
    class MockFailingProvider(BaseLLMProvider):
        async def complete(self, system_prompt, messages, tool_schemas, config):
            return ("error", "HTTP 429 Rate Limit Exceeded")
            
        async def stream(self, system_prompt, messages, tool_schemas, config):
            yield ("error", "HTTP 429 Rate Limit Exceeded")
            
    class MockSuccessProvider(BaseLLMProvider):
        async def complete(self, system_prompt, messages, tool_schemas, config):
            return ("text", "Fallback success content")
            
        async def stream(self, system_prompt, messages, tool_schemas, config):
            yield ("text", "Fallback success content")
            
    failing_inst = MockFailingProvider()
    success_inst = MockSuccessProvider()
    
    def mock_get_provider(provider_name, api_key=None, base_url=None):
        if provider_name == "google-genai":
            return failing_inst
        elif provider_name == "openai":
            return success_inst
        raise ValueError(f"Unknown provider {provider_name}")
        
    from core.providers import ProviderFactory
    orig_get_provider = ProviderFactory.get_provider
    ProviderFactory.get_provider = mock_get_provider
    try:
        # Execute generate_content on the failing provider instance, which should trigger failover
        config = {"session_id": "failover-session-id", "model": "gemini-2.5-flash"}
        res = await failing_inst.generate_content("system", [], [], config)
        
        # Verify fallback response is returned
        assert res == ("text", "Fallback success content")
        
        # Verify AuditLedger has a 'system_call' record with 'sla_failover' event for tenant_a
        al = AuditLedger(str(workspace_path))
        logs = al.get_logs(tenant_id="tenant_a")
        failover_logs = [
            log for log in logs 
            if isinstance(log["payload"], dict) and log["payload"].get("event") == "sla_failover"
        ]
        
        assert len(failover_logs) == 1
        payload_data = failover_logs[0]["payload"]
        assert payload_data["event"] == "sla_failover"
        assert payload_data["original_account_id"] == "primary-acc"
        assert payload_data["fallback_account_id"] == "fallback-acc"
        assert payload_data["markup_multiplier"] == 1.8
        
        # Verify record_usage maps to fallback-acc and records markup_multiplier of 1.8 in financial ledger
        am.record_usage(
            account_id="primary-acc",
            prompt_tokens=100,
            completion_tokens=200,
            session_id="failover-session-id"
        )
        
        # Verify tokens used is updated on fallback-acc in accounts.json
        accounts_data = am._load_data()
        accounts_map = {acc["id"]: acc for acc in accounts_data["accounts"]}
        
        assert accounts_map["primary-acc"]["tokens_used"] == 0
        assert accounts_map["fallback-acc"]["tokens_used"] == 300
        
        # Verify financial ledger has the transaction with markup_multiplier = 1.8
        fl = FinancialLedger(str(workspace_path))
        records = fl.get_all_records(tenant_id="tenant_a")
        assert len(records) == 1
        assert records[0]["account_id"] == "fallback-acc"
        assert records[0]["markup_multiplier"] == 1.8
    finally:
        ProviderFactory.get_provider = orig_get_provider


def test_websocket_auth_handshake(test_workspace, api_client):
    """Verify WebSocket handshake connection auth rejecting on bad/missing token and accepting on valid token."""
    # Test connection rejection
    with api_client.websocket_connect("/v1/stream", headers={"Authorization": "Bearer invalid_jwt_token"}) as ws:
        with pytest.raises(WebSocketDisconnect) as excinfo:
            ws.receive_json()
        assert excinfo.value.code == 4001
        
    with api_client.websocket_connect("/v1/stream", headers={"x-api-key": "invalid_key"}) as ws:
        with pytest.raises(WebSocketDisconnect) as excinfo:
            ws.receive_json()
        assert excinfo.value.code == 4001
        
    # Generate a valid JWT token
    token = generate_jwt({"tenant_id": "tenant_a", "exp": time.time() + 60})
    with api_client.websocket_connect("/v1/stream", headers={"Authorization": f"Bearer {token}"}) as ws:
        # Handshake accepted, send invalid formatting message to verify connection is open and active
        ws.send_json({"invalid": "format"})
        res = ws.receive_json()
        assert "error" in res
