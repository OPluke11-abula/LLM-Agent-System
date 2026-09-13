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
from agent_workspace.routes.chat import router
from agent_workspace.routes.dependencies import get_tenant_context, get_authenticated_principal

app = FastAPI()
app.include_router(router)
app.dependency_overrides[get_tenant_context] = lambda: "test-tenant"
app.dependency_overrides[get_authenticated_principal] = lambda: {"tenant_id": "test-tenant", "role": "admin"}
client = TestClient(app)


def test_health_check_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") in ["healthy", "ok"] or "version" in data


def test_api_version_endpoint():
    response = client.get("/api/version")
    assert response.status_code == 200
    assert "version" in response.json()
