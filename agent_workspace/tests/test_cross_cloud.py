import os
import sys
import pytest
import json
import hashlib
import time
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi.testclient import TestClient

# Add project root to sys.path
workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)

from api import app
from core.cross_cloud_gateway import CROSS_CLOUD_GATEWAY
from observability import get_cost_router
from core.account_manager import AccountManager
from core.router import AgentRouter
from core.providers import ProviderResponse

@pytest.fixture
def anyio_backend():
    return "asyncio"

@pytest.fixture
def api_client():
    return TestClient(app)

def test_handshake_validation():
    """Verify handshakes are validated correctly based on cert sha and signature."""
    client_cert = "cert12345"
    payload = "handshake-payload"
    expected_sig = hashlib.sha256(f"{payload}:{client_cert}".encode("utf-8")).hexdigest()
    
    assert CROSS_CLOUD_GATEWAY.validate_handshake(client_cert, expected_sig, payload) is True
    assert CROSS_CLOUD_GATEWAY.validate_handshake(client_cert, "wrong-signature", payload) is False
    assert CROSS_CLOUD_GATEWAY.validate_handshake(None, expected_sig, payload) is False

def test_peer_discovery_and_routing():
    """Verify seed node peer discovery and packet routing logic."""
    import asyncio
    # Reset peers
    CROSS_CLOUD_GATEWAY.peers.clear()
    
    seed_nodes = [
        {"url": "ws://aws-node/v1/cross-cloud/tunnel", "cloud": "AWS"},
        {"url": "ws://gcp-node/v1/cross-cloud/tunnel", "cloud": "GCP"}
    ]
    
    # Register local cloud as LOCAL
    CROSS_CLOUD_GATEWAY.register_local_cloud("LOCAL")
    
    loop = asyncio.new_event_loop()
    try:
        count = loop.run_until_complete(CROSS_CLOUD_GATEWAY.discover_peers(seed_nodes, "my-cert"))
        assert count == 2
        assert "AWS" in CROSS_CLOUD_GATEWAY.peers
        assert "GCP" in CROSS_CLOUD_GATEWAY.peers
        
        # Test routing locally
        local_packet = {
            "source_cloud": "AWS",
            "target_cloud": "LOCAL",
            "payload": {"data": "hello-local"},
            "signature": hashlib.sha256(json.dumps({"data": "hello-local"}, sort_keys=True).encode("utf-8")).hexdigest()
        }
        routed = loop.run_until_complete(CROSS_CLOUD_GATEWAY.route_packet(local_packet))
        assert routed is True
        
        # Test routing to peer
        peer_packet = {
            "source_cloud": "LOCAL",
            "target_cloud": "AWS",
            "payload": {"data": "hello-aws"},
            "signature": hashlib.sha256(json.dumps({"data": "hello-aws"}, sort_keys=True).encode("utf-8")).hexdigest()
        }
        routed_peer = loop.run_until_complete(CROSS_CLOUD_GATEWAY.route_packet(peer_packet))
        assert routed_peer is True
        
        # Test invalid packet signature
        bad_packet = {
            "source_cloud": "LOCAL",
            "target_cloud": "AWS",
            "payload": {"data": "hello-aws"},
            "signature": "bad-signature"
        }
        routed_bad = loop.run_until_complete(CROSS_CLOUD_GATEWAY.route_packet(bad_packet))
        assert routed_bad is False
    finally:
        loop.close()

def test_websocket_tunnel_endpoint(api_client):
    """Verify websocket tunnel endpoint accepts valid signature and routes packets."""
    client_cert = "ws-cert"
    payload = "ws-payload"
    signature = hashlib.sha256(f"{payload}:{client_cert}".encode("utf-8")).hexdigest()
    
    # Correct signature connects
    params = f"?client_cert={client_cert}&signature={signature}&payload={payload}&cloud_name=GCP"
    with api_client.websocket_connect(f"/v1/cross-cloud/tunnel{params}") as websocket:
        # GCP registered in peers
        assert "GCP" in CROSS_CLOUD_GATEWAY.peers
        assert CROSS_CLOUD_GATEWAY.peers["GCP"]["status"] == "connected"
        
        # Test receiving and routing packets
        packet = {
            "source_cloud": "GCP",
            "target_cloud": "LOCAL",
            "payload": {"cmd": "execute"},
            "signature": hashlib.sha256(json.dumps({"cmd": "execute"}, sort_keys=True).encode("utf-8")).hexdigest()
        }
        websocket.send_text(json.dumps(packet))
        time.sleep(0.1)

    # Disconnect removes peer
    assert "GCP" not in CROSS_CLOUD_GATEWAY.peers

def test_websocket_tunnel_endpoint_rejection(api_client):
    """Verify websocket tunnel endpoint rejects invalid handshake signature."""
    params = "?client_cert=cert&signature=wrong&payload=payload&cloud_name=GCP"
    with pytest.raises(Exception):
        with api_client.websocket_connect(f"/v1/cross-cloud/tunnel{params}"):
            pass

def test_cost_router_utility_scores():
    """Verify CloudCostRouter select_optimal_provider selects correct provider based on weights."""
    router = get_cost_router()
    router.metrics["google-genai"]["latency_history"].clear()
    router.metrics["aws-bedrock"]["latency_history"].clear()
    router.metrics["local-ollama"]["latency_history"].clear()
    
    # Test with just google-genai and aws-bedrock
    providers = ["google-genai", "aws-bedrock"]
    
    # 1. Compilation: weight speed=0.9, cost=0.1 -> google-genai is fastest base speed 80
    opt_comp = router.select_optimal_provider("compilation", providers)
    assert opt_comp == "google-genai"
    
    # 2. Text Inference: with only GCP and AWS, GCP wins since it is cheaper
    opt_text_no_local = router.select_optimal_provider("text_inference", providers)
    assert opt_text_no_local == "google-genai"

    # 3. If local-ollama is also available, it has cost 0.0, so it will be selected due to cost utility
    providers_with_local = ["google-genai", "aws-bedrock", "local-ollama"]
    opt_text = router.select_optimal_provider("text_inference", providers_with_local)
    assert opt_text == "local-ollama"

    # 4. UI Layout: weight speed=0.6, cost=0.4 -> google-genai is optimal
    opt_ui = router.select_optimal_provider("ui_layout", providers)
    assert opt_ui == "google-genai"

def test_account_manager_optimal_selection(tmp_path):
    """Verify get_optimal_account_for_task resolves correct account based on task type."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text("llm:\n  provider: google-genai\n  model: gemini-2.5-flash\n", encoding="utf-8")

    accounts_data = {
        "accounts": [
            {
                "id": "gcp-acc",
                "provider": "google-genai",
                "model": "gemini-2.5-flash",
                "api_key": "some-key",
                "is_active": True
            },
            {
                "id": "aws-acc",
                "provider": "aws-bedrock",
                "model": "claude-3-opus",
                "api_key": "aws-key",
                "is_active": False
            },
            {
                "id": "local-acc",
                "provider": "local-ollama",
                "model": "llama3",
                "api_key": "",
                "is_active": False
            }
        ],
        "active_account_id": "gcp-acc"
    }
    accounts_file = tmp_path / "accounts.json"
    accounts_file.write_text(json.dumps(accounts_data, indent=2), encoding="utf-8")
    
    am = AccountManager(str(tmp_path))
    
    # Text inference choosing local-ollama (local-acc)
    acc_text = am.get_optimal_account_for_task("text_inference")
    assert acc_text["id"] == "local-acc"
    
    # If we only have GCP and AWS, compilation chooses GCP
    accounts_data_no_local = {
        "accounts": [
            {
                "id": "gcp-acc",
                "provider": "google-genai",
                "model": "gemini-2.5-flash",
                "api_key": "some-key",
                "is_active": True
            },
            {
                "id": "aws-acc",
                "provider": "aws-bedrock",
                "model": "claude-3-opus",
                "api_key": "aws-key",
                "is_active": False
            }
        ],
        "active_account_id": "gcp-acc"
    }
    accounts_file.write_text(json.dumps(accounts_data_no_local, indent=2), encoding="utf-8")
    
    am_no_local = AccountManager(str(tmp_path))
    acc_comp = am_no_local.get_optimal_account_for_task("compilation")
    assert acc_comp["id"] == "gcp-acc"

@pytest.mark.asyncio
async def test_router_detect_task_type_and_record_latency(tmp_path):
    """Verify AgentRouter detects task type and logs latency to the cost router."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text("""
llm:
  provider: google-genai
  model: gemini-2.5-flash
memory:
  long_term_enabled: false
""", encoding="utf-8")
    
    accounts_data = {
        "accounts": [
            {
                "id": "gcp-acc",
                "provider": "google-genai",
                "model": "gemini-2.5-flash",
                "api_key": "some-key",
                "is_active": True
            }
        ],
        "active_account_id": "gcp-acc"
    }
    accounts_file = tmp_path / "accounts.json"
    accounts_file.write_text(json.dumps(accounts_data, indent=2), encoding="utf-8")

    mock_provider = AsyncMock()
    mock_provider.generate_content.return_value = ProviderResponse("text", "Simulated output content")
    
    from core.providers import ProviderFactory
    with patch.object(ProviderFactory, "get_provider", return_value=mock_provider):
        engine = MagicMock()
        engine.workspace_path = str(tmp_path)
        engine.render_prompt.return_value = "System prompt"
        engine.get_tool_schemas.return_value = []
        
        router = AgentRouter(
            engine=engine,
            agent_name="TestAgent"
        )
        
        router._classify_intent = AsyncMock(return_value="CHAT")
        
        response = await router.run_agent_loop(
            user_input="Please compile this code and run it"
        )
        
        assert "Simulated output content" in response
        
        c_router = get_cost_router()
        assert len(c_router.metrics["google-genai"]["latency_history"]) > 0
        assert c_router.metrics["google-genai"]["latency_history"][-1] >= 0
