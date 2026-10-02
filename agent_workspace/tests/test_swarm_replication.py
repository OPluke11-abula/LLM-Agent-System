import os
import sys
import json
import pytest
import asyncio
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

# Ensure agent_workspace is in sys.path
workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)

from core.agent_crew import AgentCrew, CrewRegistry
from core.broker import InMemorySwarmBroker, get_broker
from core.swarm_coordinator import SwarmCoordinator
from core.discussion_room import ProofOfConsensus
from api import app
from conftest import auth_headers


@pytest.fixture(autouse=True)
def clean_swarm_state():
    CrewRegistry.clear()
    SwarmCoordinator._nodes.clear()
    SwarmCoordinator._failure_logs.clear()
    ProofOfConsensus.reset_keys()
    yield
    CrewRegistry.clear()
    SwarmCoordinator._nodes.clear()
    SwarmCoordinator._failure_logs.clear()


def test_checkpoint_signature_verification():
    """Verify that AgentCrew correctly signs and cryptographically validates checkpoints."""
    checkpoint_data = {
        "session_id": "test-session-123",
        "node_id": "node-dev-1",
        "role": "dev",
        "task_instructions": "Implement feature X",
        "input_parameters": {"lang": "python"},
        "completed_subtasks": ["initialize"],
        "intermediate_outputs": {"initialize": "done"}
    }
    
    # Generate signature using PoC Dev key
    sig = AgentCrew.generate_checkpoint_signature(checkpoint_data, "dev")
    checkpoint_data["signature"] = sig
    checkpoint_data["signer"] = "dev"
    
    # Verify signature
    assert AgentCrew.verify_checkpoint_signature(checkpoint_data) is True
    
    # Verify signature fails if data is tampered
    tampered_data = checkpoint_data.copy()
    tampered_data["task_instructions"] = "Implement feature Y"
    assert AgentCrew.verify_checkpoint_signature(tampered_data) is False


@pytest.mark.asyncio
async def test_state_checkpointing_in_broker():
    """Verify state checkpointing replicates correctly to the broker kv_store and publishes sync broadcasts."""
    broker = InMemorySwarmBroker()
    crew = AgentCrew(session_id="test-session-456")
    
    published_msgs = []
    async def mock_pub(channel, msg):
        published_msgs.append((channel, msg))
    broker.publish = mock_pub
    
    checkpoint = await crew.save_checkpoint(
        broker=broker,
        node_id="node-dev-1",
        role="dev",
        task_instructions="Task instructions",
        input_parameters={"input": 1},
        completed_subtasks=["initialize"],
        intermediate_outputs={"initialize": "ok"},
        signer="dev"
    )
    
    # Check that it is stored in kv_store
    redis_key = f"swarm:session:test-session-456:checkpoint"
    assert redis_key in broker.kv_store
    stored = json.loads(broker.kv_store[redis_key])
    assert stored["signature"] == checkpoint["signature"]
    
    # Retrieve checkpoint
    retrieved = await crew.get_checkpoint(broker)
    assert retrieved is not None
    assert retrieved["signature"] == checkpoint["signature"]
    
    # Assert broadcast
    assert len(published_msgs) == 1
    assert published_msgs[0][0] == "swarm:session:checkpoint:sync"
    assert published_msgs[0][1]["type"] == "checkpoint_sync"


@pytest.mark.asyncio
async def test_automated_failover_and_resumption():
    """Verify that when a node failover event occurs, the secondary node resumes from the checkpoint."""
    broker = InMemorySwarmBroker()
    
    # Patch global broker
    import sys
    old_brokers = {}
    for name, module in list(sys.modules.items()):
        if name.endswith("core.broker") or name.endswith("service"):
            old_brokers[name] = getattr(module, "_global_broker", None)
            module._global_broker = broker
            
    try:
        # Register two dev nodes
        SwarmCoordinator.register_or_update_node("dev", "node-dev-1", "idle")
        SwarmCoordinator.register_or_update_node("dev", "node-dev-2", "idle")
        
        # Keep track of which node executed
        nodes_contacted = []
        
        # We mock _async_dispatch_to_role to simulate worker execution and failures
        async def mock_async_dispatch(
            broker,
            node_id,
            role,
            task_instructions,
            parent_node_id,
            input_parameters,
            security_restrictions,
            mock_directives,
            validation_assertions,
            target_node_id=None,
            checkpoint=None
        ):
            nodes_contacted.append(target_node_id)
            
            # Validation Gate
            if checkpoint:
                is_valid = AgentCrew.verify_checkpoint_signature(checkpoint)
                if not is_valid:
                    return {
                        "type": "task_response",
                        "status": "error",
                        "node_id": node_id,
                        "error": "Checkpoint signature verification failed"
                    }
            
            # Subtask progression
            subtasks = ["initialize", "execute", "finalize"]
            completed = []
            outputs = {}
            if checkpoint:
                completed = checkpoint.get("completed_subtasks", [])
                outputs = checkpoint.get("intermediate_outputs", {})
                
            remaining = [s for s in subtasks if s not in completed]
            
            for s in remaining:
                completed.append(s)
                outputs[s] = f"Done {s}"
                
                # Save checkpoint
                crew_inst = AgentCrew(session_id="test-session-resumption")
                await crew_inst.save_checkpoint(
                    broker=broker,
                    node_id=target_node_id,
                    role="dev",
                    task_instructions=task_instructions,
                    input_parameters=input_parameters,
                    completed_subtasks=completed,
                    intermediate_outputs=outputs,
                    signer="dev"
                )
                
                # Check for simulated crash
                if mock_directives.get("fail_after_subtask") == s and target_node_id == "node-dev-1":
                    SwarmCoordinator.mark_node_offline("node-dev-1", reason="dispatch_timeout")
                    raise asyncio.TimeoutError("Timeout simulating worker failure.")
            
            return {
                "type": "task_response",
                "status": "completed",
                "node_id": node_id,
                "output": f"Resumed execution from checkpoint. Completed: {completed}. Output: Success",
                "error": None
            }
            
        crew = AgentCrew(session_id="test-session-resumption")
        with patch.object(crew, "_async_dispatch_to_role", new=mock_async_dispatch):
            res = crew.dispatch_to_role(
                role="dev",
                task_instructions="Perform test task",
                input_parameters={},
                security_restrictions={},
                mock_directives={"fail_after_subtask": "initialize"},
                validation_assertions=[]
            )
        
        # Verify that node-dev-1 was contacted, failed, node-dev-2 was contacted, and resumed
        assert "node-dev-1" in nodes_contacted
        assert "node-dev-2" in nodes_contacted
        assert res["status"] == "completed"
        assert "Resumed execution from checkpoint." in res["output"]
        assert "Completed: ['initialize', 'execute', 'finalize']" in res["output"]
        
    finally:
        for name, val in old_brokers.items():
            if sys.modules.get(name):
                sys.modules[name]._global_broker = val


@pytest.mark.asyncio
async def test_consensus_validation_gate_failure():
    """Verify that the verification gate rejects checkpoints with invalid signatures."""
    broker = InMemorySwarmBroker()
    
    import sys
    old_brokers = {}
    for name, module in list(sys.modules.items()):
        if name.endswith("core.broker") or name.endswith("service"):
            old_brokers[name] = getattr(module, "_global_broker", None)
            module._global_broker = broker
            
    try:
        SwarmCoordinator.register_or_update_node("dev", "node-dev-1", "idle")
        
        # Pre-populate an invalid checkpoint
        crew = AgentCrew(session_id="tampered-session")
        checkpoint_data = {
            "session_id": "tampered-session",
            "node_id": "node-dev-1",
            "role": "dev",
            "task_instructions": "instructions",
            "input_parameters": {},
            "completed_subtasks": ["initialize"],
            "intermediate_outputs": {},
            "signature": "fake-tampered-signature",
            "signer": "dev"
        }
        redis_key = f"swarm:session:tampered-session:checkpoint"
        broker.kv_store[redis_key] = json.dumps(checkpoint_data)
        
        async def mock_async_dispatch(
            broker,
            node_id,
            role,
            task_instructions,
            parent_node_id,
            input_parameters,
            security_restrictions,
            mock_directives,
            validation_assertions,
            target_node_id=None,
            checkpoint=None
        ):
            # Validation Gate
            if checkpoint:
                is_valid = AgentCrew.verify_checkpoint_signature(checkpoint)
                if not is_valid:
                    return {
                        "type": "task_response",
                        "status": "error",
                        "node_id": node_id,
                        "error": "Checkpoint signature verification failed"
                    }
            
            return {
                "type": "task_response",
                "status": "completed",
                "node_id": node_id,
                "output": "Success",
                "error": None
            }
            
        with patch.object(crew, "_async_dispatch_to_role", new=mock_async_dispatch):
            res = crew.dispatch_to_role(
                role="dev",
                task_instructions="Perform test task",
                input_parameters={},
                security_restrictions={},
                mock_directives={},
                validation_assertions=[]
            )
        
        # Verify it failed due to checkpoint validation error
        assert res["status"] == "error"
        assert "Checkpoint signature verification failed" in res["error"]
        
    finally:
        for name, val in old_brokers.items():
            if sys.modules.get(name):
                sys.modules[name]._global_broker = val



def test_http_api_endpoints():
    """Verify HTTP GET /v1/swarm/sessions and POST /v1/swarm/sessions/resume endpoints."""
    broker = InMemorySwarmBroker()
    
    import sys
    old_brokers = {}
    for name, module in list(sys.modules.items()):
        if name.endswith("core.broker") or name.endswith("api"):
            old_brokers[name] = getattr(module, "_global_broker", None)
            module._global_broker = broker
            
    try:
        client = TestClient(app, headers=auth_headers(tenant_id="admin_tenant"))
        
        # 1. Populate a mock checkpoint
        session_id = "test-api-session"
        checkpoint_data = {
            "session_id": session_id,
            "node_id": "node-dev-1",
            "role": "dev",
            "task_instructions": "API task",
            "input_parameters": {},
            "completed_subtasks": ["initialize"],
            "intermediate_outputs": {},
            "signature": "api-sig",
            "signer": "dev"
        }
        redis_key = f"swarm:session:{session_id}:checkpoint"
        broker.kv_store[redis_key] = json.dumps(checkpoint_data)
        
        # Register node
        SwarmCoordinator.register_or_update_node("dev", "node-dev-1", "idle")
        
        # 2. Query sessions endpoint
        response = client.get("/v1/swarm/sessions")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert len(data["sessions"]) == 1
        assert data["sessions"][0]["session_id"] == session_id
        
        # 3. Trigger manual failover resumption
        res_response = client.post("/v1/swarm/sessions/resume", json={"session_id": session_id})
        assert res_response.status_code == 200
        res_data = res_response.json()
        assert res_data["status"] == "success"
        assert res_data["session_id"] == session_id
        
        # Verify node-dev-1 was marked offline
        active_nodes = SwarmCoordinator.get_active_nodes()
        node_ids = [n["node_id"] for n in active_nodes]
        assert "node-dev-1" not in node_ids
        
    finally:
        for name, val in old_brokers.items():
            if sys.modules.get(name):
                sys.modules[name]._global_broker = val
