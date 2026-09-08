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
from agent_workspace.routes.swarm import router
from agent_workspace.routes.dependencies import get_tenant_context

app = FastAPI()
app.include_router(router)
app.dependency_overrides[get_tenant_context] = lambda: "test-tenant"
client = TestClient(app)


def test_swarm_nodes_endpoint():
    response = client.get("/v1/swarm/nodes")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "nodes" in data


def test_swarm_health_endpoint():
    response = client.get("/v1/swarm/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "healthy" in data


def test_swarm_peers_endpoint():
    response = client.get("/v1/swarm/peers")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "peers" in data


def test_swarm_scale_endpoint():
    response = client.post("/v1/swarm/scale", json={"role": "dev", "direction": "up"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
