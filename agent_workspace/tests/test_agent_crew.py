import os
import sys
import json
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

# Ensure agent_workspace is in sys.path
workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)

from core.agent_crew import AgentCrew, CrewRegistry
from skills.delegate_task import delegate_task, DelegateTaskArgs
from api import app, SwarmP2PCrypto


@pytest.fixture(autouse=True)
def clean_registry():
    CrewRegistry.clear()
    yield
    CrewRegistry.clear()


def test_swarm_p2p_crypto_keys():
    """Verify that SwarmP2PCrypto successfully generates and derives ECDH shared keys."""
    crypto1 = SwarmP2PCrypto()
    crypto2 = SwarmP2PCrypto()

    pub1 = crypto1.get_public_bytes()
    pub2 = crypto2.get_public_bytes()

    assert pub1.startswith("-----BEGIN PUBLIC KEY-----")
    assert pub2.startswith("-----BEGIN PUBLIC KEY-----")

    key1_derived = crypto1.compute_shared_key(pub2)
    key2_derived = crypto2.compute_shared_key(pub1)

    assert key1_derived == key2_derived
    assert len(key1_derived) == 32


def test_agent_crew_orchestration_dispatches():
    """Test AgentCrew dispatch to CEO, Developer, Auditor, and CFO, verifying states and schema validations."""
    crew = AgentCrew()
    
    # 1. Successful dispatch with validation assertions and mock directives
    res = crew.dispatch_to_role(
        role="Developer",
        task_instructions="Write a binary search algorithm",
        input_parameters={"language": "python"},
        security_restrictions={"allow_network": False},
        mock_directives={"force_mock_response": "def binary_search(): pass"},
        validation_assertions=["algorithm returns correct index", "time complexity is O(log n)"]
    )
    assert res["status"] == "completed"
    assert res["output"] == "def binary_search(): pass"

    topology = CrewRegistry.get_topology(crew.session_id)
    assert len(topology["nodes"]) == 1
    assert topology["nodes"][0]["role"] == "Developer"
    assert topology["nodes"][0]["status"] == "completed"

    # 2. Dispatch with failing validation assertions
    res_fail = crew.dispatch_to_role(
        role="Auditor",
        task_instructions="Audit the generated code",
        input_parameters={},
        security_restrictions={},
        mock_directives={},
        validation_assertions=["failing check: must error out"]
    )
    assert res_fail["status"] == "error"
    assert "Validation assertion failed" in res_fail["error"]

    topology_updated = CrewRegistry.get_topology(crew.session_id)
    auditor_node = [n for n in topology_updated["nodes"] if n["role"] == "Auditor"][0]
    assert auditor_node["status"] == "error"

    # 3. Dispatch violating sandbox restrictions
    res_restricted = crew.dispatch_to_role(
        role="CFO",
        task_instructions="Verify billing ledger records",
        input_parameters={},
        security_restrictions={"block_all": True},
        mock_directives={},
        validation_assertions=[]
    )
    assert res_restricted["status"] == "error"
    assert "Execution blocked by policy rules" in res_restricted["error"]

    # 4. Enforce missing schema fields
    with pytest.raises(ValueError, match="input_parameters"):
        crew.dispatch_to_role(role="CEO", task_instructions="Coordinate task")


def test_delegate_task_tool_schema_enforcement():
    """Verify that delegate_task tool requires full validation schemas and tracks executions."""
    mock_engine = MagicMock()
    mock_engine.workspace_path = "mock_workspace"
    context = {"engine": mock_engine, "session_id": "session-tool-test", "parent_node_id": "parent-node-1"}

    # Complete schema
    args = DelegateTaskArgs(
        worker_name="researcher",
        task_instructions="Gather search queries",
        input_parameters={"query": "pytest"},
        security_restrictions={},
        mock_directives={"force_mock_response": "Research complete."},
        validation_assertions=[]
    )

    with patch("skills.delegate_task.load_worker_config", return_value={"allowed_tools": [], "timeout": 30.0}):
        res = delegate_task(args, context)
        assert "[Worker 'researcher' Result]:\nResearch complete." in res

    topology = CrewRegistry.get_topology("session-tool-test")
    assert len(topology["nodes"]) == 1
    assert topology["nodes"][0]["role"] == "researcher"
    assert topology["nodes"][0]["status"] == "completed"
    assert len(topology["edges"]) == 1
    assert topology["edges"][0]["source"] == "parent-node-1"


def test_crew_api_endpoints():
    """Verify registry POST and topology GET endpoints for visual canvas control-plane."""
    client = TestClient(app)
    
    # 1. Register node via POST API
    reg_payload = {
        "session_id": "api-session",
        "role": "CEO",
        "parent_node_id": None,
        "status": "pending",
        "description": "Start crew",
        "input_parameters": {"budget": 100},
        "security_restrictions": {},
        "mock_directives": {},
        "validation_assertions": []
    }
    
    resp_reg = client.post("/v1/crew/register", json=reg_payload)
    assert resp_reg.status_code == 200
    data_reg = resp_reg.json()
    assert data_reg["status"] == "success"
    node_id = data_reg["node_id"]

    # 2. Get topology matching visual frontend canvas
    resp_top = client.get("/v1/crew/topology?session_id=api-session")
    assert resp_top.status_code == 200
    data_top = resp_top.json()
    assert "nodes" in data_top
    assert "edges" in data_top
    assert len(data_top["nodes"]) == 1
    assert data_top["nodes"][0]["id"] == node_id
    assert data_top["nodes"][0]["role"] == "CEO"


def test_crew_sync_websocket_handshake_and_broadcast():
    """Verify ECDH handshake, AES-GCM payload encryption, and broadcast of checkpoints between concurrent peers."""
    from api import crew_sync_manager
    from core.p2p_router import SwarmP2PCrypto
    import asyncio

    session_id = "test-session-sync"

    # 1. Create two mock WebSockets
    ws1 = MagicMock()
    ws2 = MagicMock()

    # 2. Key exchange simulation
    crypto1 = SwarmP2PCrypto()
    crypto2 = SwarmP2PCrypto()
    server_crypto1 = SwarmP2PCrypto()
    server_crypto2 = SwarmP2PCrypto()

    key1 = crypto1.compute_shared_key(server_crypto1.get_public_bytes())
    server_key1 = server_crypto1.compute_shared_key(crypto1.get_public_bytes())

    key2 = crypto2.compute_shared_key(server_crypto2.get_public_bytes())
    server_key2 = server_crypto2.compute_shared_key(crypto2.get_public_bytes())

    assert key1 == server_key1
    assert key2 == server_key2

    # 3. Connect them to crew_sync_manager
    crew_sync_manager.connect(session_id, ws1, server_key1)
    crew_sync_manager.connect(session_id, ws2, server_key2)

    # 4. Broadcast a message from ws1
    sync_payload = {
        "action": "sync_state",
        "checkpoint": "checkpoint-file-data",
        "data": {"state": "in_progress"}
    }

    # Simulate ws1 sending encrypted payload
    decrypted_str = json.dumps(sync_payload)

    # Mock ws2.send_json to capture the sent broadcast
    sent_messages = []
    async def mock_send_json(msg):
        sent_messages.append(msg)
    ws2.send_json = mock_send_json

    # Execute broadcast asynchronously
    asyncio.run(crew_sync_manager.broadcast(session_id, ws1, decrypted_str))

    # Verify ws2 received the broadcast
    assert len(sent_messages) == 1
    broadcast_enc = sent_messages[0]

    assert "ciphertext" in broadcast_enc
    assert "nonce" in broadcast_enc

    # ws2 decrypts the broadcast using key2
    decrypted_str_recv = SwarmP2PCrypto.decrypt_message(key2, broadcast_enc)
    decrypted_data = json.loads(decrypted_str_recv)

    assert decrypted_data["action"] == "sync_state"
    assert decrypted_data["checkpoint"] == "checkpoint-file-data"
    assert decrypted_data["data"]["state"] == "in_progress"

    # Cleanup
    crew_sync_manager.disconnect(session_id, ws1)
    crew_sync_manager.disconnect(session_id, ws2)



