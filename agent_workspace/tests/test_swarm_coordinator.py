import os
import sys
import time
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

# Ensure agent_workspace is in sys.path
TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TEST_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.swarm_coordinator import SwarmCoordinator
from core.agent_crew import AgentCrew, CrewRegistry
from api import app
from conftest import auth_headers

client = TestClient(app, headers=auth_headers())


@pytest.fixture(autouse=True)
def clean_coordinator():
    # Clear SwarmCoordinator nodes and failures between runs
    SwarmCoordinator._nodes.clear()
    SwarmCoordinator._failure_logs.clear()
    yield


def test_swarm_coordinator_registration():
    # Register idle node
    SwarmCoordinator.register_or_update_node("developer", "node-1", "idle")
    nodes = SwarmCoordinator.get_active_nodes()
    assert len(nodes) == 1
    assert nodes[0]["node_id"] == "node-1"
    assert nodes[0]["role"] == "developer"
    assert nodes[0]["status"] == "idle"
    assert nodes[0]["load"] == 0

    # Register busy node
    SwarmCoordinator.register_or_update_node("developer", "node-1", "busy")
    nodes = SwarmCoordinator.get_active_nodes()
    assert len(nodes) == 1
    assert nodes[0]["status"] == "busy"
    assert nodes[0]["load"] == 1

    # Mark offline
    SwarmCoordinator.mark_node_offline("node-1", "manual_test")
    assert len(SwarmCoordinator.get_active_nodes()) == 0
    failures = SwarmCoordinator.get_failure_logs()
    assert len(failures) == 1
    assert failures[0]["node_id"] == "node-1"
    assert failures[0]["reason"] == "manual_test"


def test_swarm_coordinator_stale_heartbeats():
    # Register node
    SwarmCoordinator.register_or_update_node("developer", "node-1", "idle")
    
    # Simulate age out by backdating last_seen
    SwarmCoordinator._nodes["node-1"]["last_seen"] = time.time() - 20.0
    
    # Trigger heartbeat check with timeout=15.0
    SwarmCoordinator.check_heartbeats(timeout=15.0)
    assert len(SwarmCoordinator.get_active_nodes()) == 0
    failures = SwarmCoordinator.get_failure_logs()
    assert len(failures) == 1
    assert failures[0]["node_id"] == "node-1"
    assert failures[0]["reason"] == "heartbeat_timeout"


def test_swarm_coordinator_load_balancing():
    # Register two developer nodes
    SwarmCoordinator.register_or_update_node("developer", "node-1", "busy")  # load 1
    SwarmCoordinator.register_or_update_node("developer", "node-2", "idle")  # load 0

    # Best node should be the idle one
    best = SwarmCoordinator.get_best_node("developer")
    assert best == "node-2"
    
    # Check that load is reserved/incremented
    nodes = {n["node_id"]: n for n in SwarmCoordinator.get_active_nodes()}
    assert nodes["node-2"]["load"] == 1
    assert nodes["node-2"]["status"] == "busy"

    # Next choice has equal loads, should return one of them
    best2 = SwarmCoordinator.get_best_node("developer")
    assert best2 in ("node-1", "node-2")


def test_swarm_coordinator_scaling():
    # Scale up
    res = SwarmCoordinator.simulate_scaling("developer", "up")
    assert res["status"] == "success"
    assert res["direction"] == "up"
    assert "node_id" in res
    assert len(SwarmCoordinator.get_active_nodes()) == 1

    # Scale down
    res_down = SwarmCoordinator.simulate_scaling("developer", "down")
    assert res_down["status"] == "success"
    assert res_down["direction"] == "down"
    assert len(SwarmCoordinator.get_active_nodes()) == 0


def test_swarm_coordinator_api_endpoints():
    # Setup test nodes
    SwarmCoordinator.register_or_update_node("developer", "node-1", "idle")

    # 1. GET /v1/swarm/nodes
    resp = client.get("/v1/swarm/nodes", headers=auth_headers())
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert len(data["nodes"]) == 1
    assert data["nodes"][0]["node_id"] == "node-1"

    # 2. POST /v1/swarm/scale
    resp_scale = client.post(
        "/v1/swarm/scale",
        json={"role": "developer", "direction": "up"},
        headers=auth_headers()
    )
    assert resp_scale.status_code == 200
    assert resp_scale.json()["status"] == "success"

    # 3. GET /v1/swarm/health
    resp_health = client.get("/v1/swarm/health", headers=auth_headers())
    assert resp_health.status_code == 200
    health_data = resp_health.json()
    assert health_data["status"] == "success"
    assert health_data["active_nodes_count"] == 2


@pytest.mark.asyncio
async def test_agent_crew_failover_routing():
    # Register two active developer nodes
    SwarmCoordinator.register_or_update_node("Developer", "node-good", "idle")
    SwarmCoordinator.register_or_update_node("Developer", "node-bad", "idle")

    crew = AgentCrew(session_id="test-failover-session")
    
    # We mock _async_dispatch_to_role to raise a timeout on node-bad, but succeed on node-good
    original_dispatch = crew._async_dispatch_to_role
    
    async def mock_async_dispatch(broker, node_id, role, task_instructions, parent_node_id, input_parameters, security_restrictions, mock_directives, validation_assertions, target_node_id=None):
        if target_node_id == "node-bad":
            raise asyncio.TimeoutError("Timeout simulating worker failure.")
        return {"status": "completed", "output": "Success from good node"}

    # Mock the RedisSwarmBroker to pass the isinstance check in agent_crew.py
    from core.broker import RedisSwarmBroker
    mock_broker = MagicMock(spec=RedisSwarmBroker)
    
    # Force first node choice to be node-bad
    with patch("core.swarm_coordinator.SwarmCoordinator.get_best_node", side_effect=["node-bad", "node-good"]):
        with patch.object(crew, "_async_dispatch_to_role", new=mock_async_dispatch):
            with patch("core.broker.get_broker", return_value=mock_broker):
                res = crew.dispatch_to_role(
                    role="Developer",
                    task_instructions="Perform code task",
                    input_parameters={},
                    security_restrictions={},
                    mock_directives={},
                    validation_assertions=[]
                )
                
                assert res["status"] == "completed"
                # Check that node-bad was marked offline
                failures = SwarmCoordinator.get_failure_logs()
                assert any(f["node_id"] == "node-bad" and f["reason"] == "dispatch_timeout" for f in failures)
