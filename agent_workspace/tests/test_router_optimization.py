import os
import sys
import json
import time
import asyncio
from datetime import datetime, timezone
import tempfile
import shutil
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

# Add project root to sys.path
workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)

from api import app
from core.router import ROUTE_REGISTRY, SwarmRouteRegistry, AgentRouter
from core.engine import AgentEngine
from core.providers import ProviderResponse

@pytest.fixture(autouse=True)
def run_before_and_after_tests():
    # Clear the global registry before and after every test
    ROUTE_REGISTRY.routes.clear()
    ROUTE_REGISTRY.pruned_history.clear()
    yield
    ROUTE_REGISTRY.routes.clear()
    ROUTE_REGISTRY.pruned_history.clear()

@pytest.fixture
def temp_workspace():
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a mock .agent directory structure
        pap_dir = os.path.join(temp_dir, ".agent")
        skills_dir = os.path.join(pap_dir, "skills")
        os.makedirs(skills_dir)
        
        # Create config.yaml with long term memory disabled to avoid WinError sqlite file locks
        with open(os.path.join(temp_dir, "config.yaml"), "w", encoding="utf-8") as f:
            f.write("llm:\n  provider: google-genai\n  model: gemini-2.5-flash\n")
            f.write("memory:\n  long_term_enabled: false\n")
            
        # Copy the real agent.jinja2 template
        src_template = os.path.join(workspace_dir, "agent.jinja2")
        if os.path.isfile(src_template):
            shutil.copy(src_template, os.path.join(temp_dir, "agent.jinja2"))
        else:
            # Fallback mock template if source isn't found
            with open(os.path.join(temp_dir, "agent.jinja2"), "w", encoding="utf-8") as f:
                f.write("Hello, agent. Current time: {{ current_time }}\n")
                
        yield temp_dir

def test_swarm_route_registry_logic():
    """Test registry registers, updates, and prunes routes based on latency and success rate."""
    registry = SwarmRouteRegistry()
    node = "test_worker"
    
    # Assert initial registration
    registry.register_route(node)
    assert node in registry.routes
    assert registry.routes[node]["status"] == "active"
    assert registry.routes[node]["active_load"] == 0

    # Start dispatch
    registry.start_dispatch(node)
    assert registry.routes[node]["active_load"] == 1
    
    # End dispatch (successful, fast)
    registry.end_dispatch(node, 0.1, True)
    assert registry.routes[node]["active_load"] == 0
    assert registry.routes[node]["success_count"] == 1
    assert registry.routes[node]["success_rate"] == 1.0
    
    # Now simulate 2 more dispatches with high latency (> 0.5s) to trigger auto-pruning.
    # Since minimum dispatches is 3, 3 runs of > 500ms should trigger auto-pruning.
    registry.start_dispatch(node)
    registry.end_dispatch(node, 0.6, True)
    
    registry.start_dispatch(node)
    registry.end_dispatch(node, 0.7, True)
    
    # Total of 3 runs: 0.1, 0.6, 0.7 -> average = 0.467s. Let's do another run of 0.6s
    registry.start_dispatch(node)
    registry.end_dispatch(node, 0.6, True)
    # Now last 3 are 0.6, 0.7, 0.6 -> avg = 0.633s > 0.5s.
    assert registry.routes[node]["status"] == "pruned"
    assert len(registry.pruned_history) == 1
    assert registry.pruned_history[0]["node_id"] == node
    assert "High latency" in registry.pruned_history[0]["reason"]

    # Test auto-pruning based on success rate
    node_fail = "fail_worker"
    registry.register_route(node_fail)
    
    # Simulating 3 runs: 2 fails, 1 success -> success rate 33.3% < 70%
    registry.start_dispatch(node_fail)
    registry.end_dispatch(node_fail, 0.05, False)
    
    registry.start_dispatch(node_fail)
    registry.end_dispatch(node_fail, 0.05, False)
    
    registry.start_dispatch(node_fail)
    registry.end_dispatch(node_fail, 0.05, True)
    
    assert registry.routes[node_fail]["status"] == "pruned"
    assert len(registry.pruned_history) == 2
    assert "Low success rate" in registry.pruned_history[1]["reason"]

@pytest.mark.asyncio
async def test_agent_router_wrapping(temp_workspace):
    """Verify that routing metrics are recorded when AgentRouter executes runs."""
    engine = AgentEngine(workspace_path=temp_workspace)
    
    mock_provider = MagicMock()
    async def mock_generate_content(*args, **kwargs):
        return ProviderResponse("text", "Task complete successfully")
    mock_provider.generate_content = mock_generate_content
    
    with patch("core.router.ProviderFactory.get_provider", return_value=mock_provider), \
         patch("agent_workspace.core.router.ProviderFactory.get_provider", return_value=mock_provider):
         
        router = AgentRouter(engine, session_id="test_opt_session", agent_name="optimizer_agent")
        router._provider = mock_provider
        
        async def mock_classify_intent(user_input):
            return "CHAT"
        router._classify_intent = mock_classify_intent
        
        try:
            # Run agent loop
            res = await router.run_agent_loop("Hello world")
            assert "Task complete successfully" in res
            
            # Check that metrics were registered
            assert "optimizer_agent" in ROUTE_REGISTRY.routes
            route = ROUTE_REGISTRY.routes["optimizer_agent"]
            assert route["success_count"] == 1
            assert route["failure_count"] == 0
            assert route["success_rate"] == 1.0
            assert len(route["latency_history"]) == 1

            # Test failure routing recording
            async def mock_generate_content_fail(*args, **kwargs):
                return ProviderResponse("error", "Simulated internal LLM error")
            mock_provider.generate_content = mock_generate_content_fail
            
            res_fail = await router.run_agent_loop("Trigger fail")
            assert "Simulated internal LLM error" in res_fail
            
            # Check failure count
            assert route["failure_count"] == 1
            assert route["success_rate"] == 0.5
        finally:
            router.close()

@pytest.mark.asyncio
async def test_agent_router_streaming_wrapping(temp_workspace):
    """Verify that routing metrics are recorded when AgentRouter executes streaming runs."""
    engine = AgentEngine(workspace_path=temp_workspace)
    
    mock_provider = MagicMock()
    async def mock_stream(*args, **kwargs):
        yield ProviderResponse("text", "Chunk 1")
        yield ProviderResponse("text", "Chunk 2")
    mock_provider.generate_content_stream = mock_stream
    
    with patch("core.router.ProviderFactory.get_provider", return_value=mock_provider), \
         patch("agent_workspace.core.router.ProviderFactory.get_provider", return_value=mock_provider):
         
        router = AgentRouter(engine, session_id="test_opt_session", agent_name="stream_optimizer_agent")
        router._provider = mock_provider
        
        async def mock_classify_intent(user_input):
            return "CHAT"
        router._classify_intent = mock_classify_intent
        
        try:
            # Consume streaming events
            events = []
            async for event in router.stream_agent_loop("Stream query"):
                events.append(event)
                
            assert len(events) > 0
            assert "stream_optimizer_agent" in ROUTE_REGISTRY.routes
            route = ROUTE_REGISTRY.routes["stream_optimizer_agent"]
            assert route["success_count"] == 1
            assert route["failure_count"] == 0
        finally:
            router.close()

def test_router_api_endpoints():
    """Assert REST endpoints fetch router status and perform administrative pruning sweeps."""
    client = TestClient(app)
    
    # 1. Seed some initial mock routes
    ROUTE_REGISTRY.register_route("node_a")
    ROUTE_REGISTRY.register_route("node_b")
    
    # Mark node_b as stale by modifying last_seen manually
    now = datetime.now(timezone.utc)
    from datetime import timedelta
    stale_time = (now - timedelta(seconds=40)).isoformat()
    ROUTE_REGISTRY.routes["node_b"]["last_seen"] = stale_time
    
    # Verify GET status
    resp_get = client.get("/v1/router/status")
    assert resp_get.status_code == 200
    data = resp_get.json()
    assert "routes" in data
    assert "pruned_history" in data
    assert len(data["routes"]) == 2
    
    # Verify POST prune stale (default force = False)
    resp_prune = client.post("/v1/router/prune")
    assert resp_prune.status_code == 200
    data_prune = resp_prune.json()
    assert data_prune["status"] == "success"
    assert data_prune["pruned_any"] is True
    
    # node_b should be pruned now
    assert ROUTE_REGISTRY.routes["node_b"]["status"] == "pruned"
    assert ROUTE_REGISTRY.routes["node_a"]["status"] == "active"
    
    # Verify POST force prune all
    resp_force = client.post("/v1/router/prune?force=true")
    assert resp_force.status_code == 200
    data_force = resp_force.json()
    assert data_force["pruned_any"] is True
    assert ROUTE_REGISTRY.routes["node_a"]["status"] == "pruned"

@pytest.mark.asyncio
async def test_concurrent_dispatches_concurrency(temp_workspace):
    """Simulate heavy concurrent dispatches to assert load is tracked and pruned under concurrency."""
    engine = AgentEngine(workspace_path=temp_workspace)
    
    mock_provider = MagicMock()
    async def mock_generate_content_delay(*args, **kwargs):
        await asyncio.sleep(0.1)  # Simulate active load duration
        return ProviderResponse("text", "Done")
    mock_provider.generate_content = mock_generate_content_delay
    
    with patch("core.router.ProviderFactory.get_provider", return_value=mock_provider), \
         patch("agent_workspace.core.router.ProviderFactory.get_provider", return_value=mock_provider):
         
        router = AgentRouter(engine, session_id="test_concurrent_opt", agent_name="concurrency_agent")
        router._provider = mock_provider
        
        async def mock_classify_intent(user_input):
            return "CHAT"
        router._classify_intent = mock_classify_intent
        
        try:
            # Run multiple loops concurrently
            tasks = [
                router.run_agent_loop("Input 1"),
                router.run_agent_loop("Input 2"),
                router.run_agent_loop("Input 3")
            ]
            
            # Gather them
            results = await asyncio.gather(*tasks)
            assert len(results) == 3
            
            # Verify that concurrency agent has success_count = 3
            route = ROUTE_REGISTRY.routes["concurrency_agent"]
            assert route["success_count"] == 3
            assert route["active_load"] == 0
        finally:
            router.close()
