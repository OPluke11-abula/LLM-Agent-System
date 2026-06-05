import os
import sys
import json
import pytest
import asyncio
from unittest.mock import patch
from fastapi.testclient import TestClient

# Add project root to sys.path
workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)

from api import app, API_KEYS
from core.ledger import FinancialLedger
from core.audit_ledger import AuditLedger
from core.router import AgentRouter, ACTIVE_APPROVALS

@pytest.fixture
def api_client():
    return TestClient(app)

@pytest.fixture
def test_workspace(tmp_path):
    with patch("api.workspace", str(tmp_path)):
        old_env = os.environ.get("AGENT_WORKSPACE_DIR")
        os.environ["AGENT_WORKSPACE_DIR"] = str(tmp_path)
        
        # Initialize database tables
        fl = FinancialLedger(str(tmp_path))
        al = AuditLedger(str(tmp_path))
        
        yield tmp_path
        
        if old_env is None:
            os.environ.pop("AGENT_WORKSPACE_DIR", None)
        else:
            os.environ["AGENT_WORKSPACE_DIR"] = old_env

def test_admin_get_tenants_auth_gating(test_workspace, api_client):
    # 1. Reject without credentials
    resp = api_client.get("/v1/admin/tenants", headers={"x-enforce-auth": "true"})
    assert resp.status_code == 401
    
    # 2. Reject standard tenant
    resp = api_client.get("/v1/admin/tenants", headers={"x-api-key": "key-tenant-a"})
    assert resp.status_code == 403
    
    # 3. Accept admin tenant
    resp = api_client.get("/v1/admin/tenants", headers={"x-api-key": "key-admin"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "tenants" in data
    
    tenant_ids = [t["tenant_id"] for t in data["tenants"]]
    assert "tenant_a" in tenant_ids
    assert "tenant_b" in tenant_ids
    assert "admin_tenant" in tenant_ids

def test_admin_api_key_rotation(test_workspace, api_client):
    assert API_KEYS.get("key-tenant-a") == "tenant_a"
    try:
        # Rotate key for tenant_a
        resp = api_client.post(
            "/v1/admin/tenants/rotate-key",
            headers={"x-api-key": "key-admin"},
            json={"tenant_id": "tenant_a"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        new_key = data["api_key"]
        assert new_key.startswith("key-tenant_a-")
        
        assert "key-tenant-a" not in API_KEYS
        assert API_KEYS[new_key] == "tenant_a"
        
        # Verify authentication with the new key works, but old one fails
        resp = api_client.get("/v1/admin/tenants", headers={"x-api-key": "key-tenant-a"})
        assert resp.status_code == 401
    finally:
        # Restore key-tenant-a for backward compatibility after test
        keys_to_delete = [k for k, v in API_KEYS.items() if v == "tenant_a"]
        for k in keys_to_delete:
            del API_KEYS[k]
        API_KEYS["key-tenant-a"] = "tenant_a"

def test_admin_manual_subscription_simulation(test_workspace, api_client):
    resp = api_client.get("/v1/admin/tenants", headers={"x-api-key": "key-admin"})
    t_a = [t for t in resp.json()["tenants"] if t["tenant_id"] == "tenant_a"][0]
    assert t_a["status"] == "active"
    
    # Simulate freeze status
    resp = api_client.post(
        "/v1/admin/tenants/update-subscription",
        headers={"x-api-key": "key-admin"},
        json={"tenant_id": "tenant_a", "status": "frozen"}
    )
    assert resp.status_code == 200
    
    # Query status again
    resp = api_client.get("/v1/admin/tenants", headers={"x-api-key": "key-admin"})
    t_a = [t for t in resp.json()["tenants"] if t["tenant_id"] == "tenant_a"][0]
    assert t_a["status"] == "frozen"
    
    # Verify standard request is blocked
    resp = api_client.get("/v1/admin/tenants", headers={"x-api-key": "key-tenant-a"})
    assert resp.status_code == 403
    
    # Restore status to active
    resp = api_client.post(
        "/v1/admin/tenants/update-subscription",
        headers={"x-api-key": "key-admin"},
        json={"tenant_id": "tenant_a", "status": "active"}
    )
    assert resp.status_code == 200

def test_pause_resume_endpoints(test_workspace, api_client):
    session_id = "test-swarm-session"
    assert not AgentRouter.is_paused(session_id)
    
    # Pause
    resp = api_client.post(f"/v1/sessions/{session_id}/pause", headers={"x-api-key": "key-admin"})
    assert resp.status_code == 200
    assert resp.json()["swarm_status"] == "paused"
    assert AgentRouter.is_paused(session_id)
    
    # Resume
    resp = api_client.post(f"/v1/sessions/{session_id}/resume", headers={"x-api-key": "key-admin"})
    assert resp.status_code == 200
    assert resp.json()["swarm_status"] == "running"
    assert not AgentRouter.is_paused(session_id)

def test_hijack_endpoint(test_workspace, api_client):
    session_id = "test-hijack-session"
    loop = asyncio.new_event_loop()
    future = loop.create_future()
    
    ACTIVE_APPROVALS[session_id] = {
        "future": future,
        "tool_name": "mock_sensitive_skill",
        "arguments": {"x": 10},
        "status": "awaiting_approval"
    }
    
    resp = api_client.post(
        f"/v1/sessions/{session_id}/hijack",
        headers={"x-api-key": "key-admin"},
        json={"hijack_value": "hijacked-result-payload"}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"
    assert resp.json()["hijack_value"] == "hijacked-result-payload"
    
    assert future.done()
    res = future.result()
    assert res == {"hijacked": True, "hijack_value": "hijacked-result-payload"}
    
    ACTIVE_APPROVALS.pop(session_id, None)
