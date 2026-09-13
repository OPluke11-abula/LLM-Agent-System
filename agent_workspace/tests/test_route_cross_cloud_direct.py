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
from agent_workspace.routes.cross_cloud import router
from agent_workspace.routes.dependencies import get_tenant_context

app = FastAPI()
app.include_router(router)
app.dependency_overrides[get_tenant_context] = lambda: "test-tenant"
client = TestClient(app)


def test_cross_cloud_cert_status():
    response = client.get("/v1/cross-cloud/cert/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "cert_status" in data


def test_cross_cloud_cert_rotate():
    response = client.post("/v1/cross-cloud/cert/rotate")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "cert_sha" in data


def test_cross_cloud_revoked_list():
    response = client.get("/v1/cross-cloud/revoked")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "revoked_certificates" in data


def test_cross_cloud_revoke_and_reinstate():
    sha = "test-cert-sha-12345"
    revoke_res = client.post("/v1/cross-cloud/revoke", json={"client_cert_sha": sha})
    assert revoke_res.status_code == 200
    assert revoke_res.json()["status"] == "success"

    reinstate_res = client.post("/v1/cross-cloud/reinstate", json={"client_cert_sha": sha})
    assert reinstate_res.status_code == 200
    assert reinstate_res.json()["status"] == "success"
