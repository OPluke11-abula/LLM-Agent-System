import sys
from pathlib import Path

# Add project root and workspace to sys.path
root_dir = Path(__file__).resolve().parents[2]
workspace_dir = root_dir / "agent_workspace"
for p in (str(root_dir), str(workspace_dir)):
    if p not in sys.path:
        sys.path.insert(0, p)

import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
from agent_workspace.routes.audit import router
from agent_workspace.routes.dependencies import get_tenant_context

app = FastAPI()
app.include_router(router)
app.dependency_overrides[get_tenant_context] = lambda: "test-tenant"
client = TestClient(app)


def test_audit_logs_endpoint(monkeypatch, tmp_path):
    monkeypatch.setattr("agent_workspace.routes.audit.get_workspace", lambda: str(tmp_path))
    response = client.get("/v1/audit/logs")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "logs" in data


def test_audit_verify_endpoint(monkeypatch, tmp_path):
    monkeypatch.setattr("agent_workspace.routes.audit.get_workspace", lambda: str(tmp_path))
    response = client.get("/v1/audit/verify")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "valid" in data


def test_audit_status_endpoint(monkeypatch, tmp_path):
    monkeypatch.setattr("agent_workspace.routes.audit.get_workspace", lambda: str(tmp_path))
    response = client.get("/v1/audit/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "merkle_root" in data


def test_audit_sync_endpoint():
    response = client.post("/v1/audit/sync")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
