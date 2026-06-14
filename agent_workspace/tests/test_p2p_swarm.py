import os
import sys
import json
import pytest
import asyncio
import hashlib
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

# Ensure agent_workspace is in sys.path
workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)

from api import app
from core.p2p_router import get_p2p_router, SwarmP2PCrypto
from core.agent_crew import AgentCrew, CrewRegistry
from core.broker import InMemorySwarmBroker
from core.discussion_room import ProofOfConsensus

@pytest.fixture(autouse=True)
def reset_p2p_router():
    router = get_p2p_router()
    router.peers.clear()
    router.pending_requests.clear()
    ProofOfConsensus.reset_keys()
    yield
    router.peers.clear()
    router.pending_requests.clear()


def test_p2p_handshake_success_and_failure():
    client = TestClient(app)
    
    # 1. Invalid role or signature handshake rejection
    with pytest.raises(Exception):
        with client.websocket_connect("/v1/swarm/p2p/tunnel") as ws:
            ws.receive_json()  # server hello
            ws.send_json({"handshake": "client_hello", "public_key": "bad-key"})
            ws.send_json({
                "handshake": "verify",
                "role": "dev",
                "node_id": "test-node",
                "host": "127.0.0.1",
                "port": 9000,
                "payload_hash": "bad-hash",
                "signature": "bad-sig"
            })
            # Should close or error
            ws.receive_json()

    # 2. Valid handshake
    with client.websocket_connect("/v1/swarm/p2p/tunnel") as ws:
        server_hello = ws.receive_json()
        assert server_hello["handshake"] == "server_hello"
        server_pub = server_hello["public_key"]
        
        client_crypto = SwarmP2PCrypto()
        ws.send_json({
            "handshake": "client_hello",
            "public_key": client_crypto.get_public_bytes()
        })
        
        shared_key = client_crypto.compute_shared_key(server_pub)
        payload_hash = hashlib.sha256(f"{client_crypto.get_public_bytes()}:{server_pub}".encode("utf-8")).hexdigest()
        sig = ProofOfConsensus.generate_member_signature("dev", payload_hash)
        
        ws.send_json({
            "handshake": "verify",
            "role": "dev",
            "node_id": "test-node-client",
            "host": "127.0.0.1",
            "port": 9001,
            "payload_hash": payload_hash,
            "signature": sig
        })
        
        resp = ws.receive_json()
        assert resp["handshake"] == "verified"
        assert resp["status"] == "success"


@pytest.mark.asyncio
async def test_gossip_discovery():
    router = get_p2p_router(node_id="node-test-main", role="ceo", host="127.0.0.1", port=8000)
    router.peers.clear()
    
    # Simulate receiving a ping from Node B
    ws_mock = MagicMock()
    async def mock_send(data):
        pass
    ws_mock.send = mock_send
    shared_key = b"0" * 32  # 32 bytes dummy key
    
    ping_payload = {
        "type": "ping",
        "sender_id": "node-B",
        "role": "dev",
        "host": "127.0.0.1",
        "port": 8001,
        "known_peers": [
            {"node_id": "node-C", "role": "qa", "host": "127.0.0.1", "port": 8002}
        ]
    }
    
    await router._process_ws_message(ping_payload, "node-B", ws_mock, shared_key)
    
    # Router should have registered Node B (connected) and Node C (disconnected, discovered via gossip)
    assert "node-B" in router.peers
    assert router.peers["node-B"]["status"] == "connected"
    assert router.peers["node-B"]["role"] == "dev"
    
    assert "node-C" in router.peers
    assert router.peers["node-C"]["status"] == "disconnected"
    assert router.peers["node-C"]["role"] == "qa"


@pytest.mark.asyncio
async def test_direct_websocket_task_execution():
    router = get_p2p_router(node_id="node-test-main", role="ceo", host="127.0.0.1", port=8000)
    router.peers.clear()
    
    ws_mock = MagicMock()
    shared_key = b"0" * 32
    
    router.add_peer("node-B", "dev", "127.0.0.1", 8001, status="connected", ws=ws_mock, shared_key=shared_key)
    
    sent_payloads = []
    async def mock_send(data):
        sent_payloads.append(data)
    ws_mock.send = mock_send
    
    dispatch_coro = router.dispatch_task(
        role="dev",
        task_instructions="P2P Task instructions",
        input_parameters={},
        security_restrictions={},
        mock_directives={"force_mock_response": "P2P Output"},
        validation_assertions=[]
    )
    
    task = asyncio.create_task(dispatch_coro)
    await asyncio.sleep(0.1)
    assert len(sent_payloads) == 1
    
    encrypted_payload = json.loads(sent_payloads[0])
    decrypted_str = SwarmP2PCrypto.decrypt_message(shared_key, encrypted_payload)
    request_msg = json.loads(decrypted_str)
    assert request_msg["type"] == "task_request"
    task_id = request_msg["task_id"]
    
    response_msg = {
        "type": "task_response",
        "task_id": task_id,
        "status": "completed",
        "output": "P2P Success Output",
        "error": None
    }
    
    await router._process_ws_message(response_msg, "node-B", ws_mock, shared_key)
    
    res = await task
    assert res["status"] == "completed"
    assert res["output"] == "P2P Success Output"


def test_hybrid_routing_fallback_offline_broker():
    broker = InMemorySwarmBroker()
    
    import sys
    old_brokers = {}
    for name, module in list(sys.modules.items()):
        if name.endswith("core.broker"):
            old_brokers[name] = getattr(module, "_global_broker", None)
            module._global_broker = broker
            
    try:
        router = get_p2p_router(node_id="node-test-main", role="ceo", host="127.0.0.1", port=8000)
        router.peers.clear()
        
        ws_mock = MagicMock()
        shared_key = b"0" * 32
        router.add_peer("node-B", "dev", "127.0.0.1", 8001, status="connected", ws=ws_mock, shared_key=shared_key)
        
        async def mock_dispatch_task(role, task_instructions, input_parameters, security_restrictions, mock_directives, validation_assertions):
            return {
                "status": "completed",
                "output": "Success from P2P Dev Node"
            }
        
        with patch.object(router, "dispatch_task", new=mock_dispatch_task):
            crew = AgentCrew()
            res = crew.dispatch_to_role(
                role="dev",
                task_instructions="Task via P2P fallback",
                input_parameters={},
                security_restrictions={},
                mock_directives={},
                validation_assertions=[]
            )
            
            assert res["status"] == "completed"
            assert res["output"] == "Success from P2P Dev Node"
            
    finally:
        for name, val in old_brokers.items():
            if sys.modules.get(name):
                sys.modules[name]._global_broker = val


def test_http_api_peers_endpoint():
    router = get_p2p_router(node_id="node-test-main", role="ceo", host="127.0.0.1", port=8000)
    router.peers.clear()
    
    router.add_peer("node-B", "dev", "127.0.0.1", 8001, status="connected")
    router.peers["node-B"]["latency"] = 1.2
    
    client = TestClient(app)
    response = client.get("/v1/swarm/peers")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert len(data["peers"]) == 1
    assert data["peers"][0]["node_id"] == "node-B"
    assert data["peers"][0]["role"] == "dev"
    assert data["peers"][0]["address"] == "127.0.0.1:8001"
    assert data["peers"][0]["latency_ms"] == 1.2
    assert data["peers"][0]["status"] == "connected"
