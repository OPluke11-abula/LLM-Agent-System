import os
import sys
import json
import pytest
import asyncio
import inspect
from unittest.mock import AsyncMock, MagicMock, patch

# Ensure agent_workspace is in sys.path
workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)

from core.broker import RedisSwarmBroker, InMemorySwarmBroker, get_broker
from fastapi.testclient import TestClient
from api import app


@pytest.mark.asyncio
async def test_disabled_broker_reset_replaces_and_closes_cached_instance(monkeypatch):
    import core.broker as broker_module

    class TrackingBroker(InMemorySwarmBroker):
        def __init__(self):
            super().__init__()
            self.closed = False

        async def stop(self):
            self.closed = True
            await super().stop()

    previous = broker_module._global_broker
    try:
        monkeypatch.setenv("LAS_ENABLE_REDIS_SWARM", "false")
        cached = TrackingBroker()
        broker_module._global_broker = cached

        fresh = get_broker(reset=True)
        await asyncio.sleep(0)

        assert fresh is not cached
        assert cached.closed is True
    finally:
        broker_module._global_broker = previous


def test_disabled_broker_reuses_cached_instance_without_reset(monkeypatch):
    import core.broker as broker_module

    previous = broker_module._global_broker
    try:
        monkeypatch.setenv("LAS_ENABLE_REDIS_SWARM", "false")
        cached = InMemorySwarmBroker()
        broker_module._global_broker = cached

        assert get_broker() is cached
    finally:
        broker_module._global_broker = previous


def test_disabled_broker_does_not_load_redis(monkeypatch):
    import core.broker as broker_module

    previous = broker_module._global_broker
    try:
        monkeypatch.setenv("LAS_ENABLE_REDIS_SWARM", "false")
        broker_module._global_broker = None
        monkeypatch.setattr(
            broker_module,
            "_load_redis",
            lambda: (_ for _ in ()).throw(AssertionError("Redis must remain unloaded")),
        )

        broker = get_broker(reset=True)

        assert isinstance(broker, InMemorySwarmBroker)
    finally:
        broker_module._global_broker = previous


@pytest.mark.asyncio
async def test_redis_broker_broadcasting():
    """Verify that RedisSwarmBroker successfully subscribes, publishes, and handles incoming pub/sub messages."""
    mock_redis = MagicMock()
    mock_pubsub = AsyncMock()
    
    mock_redis.ping = AsyncMock()
    mock_redis.pubsub = MagicMock(return_value=mock_pubsub)
    mock_redis.publish = AsyncMock()
    mock_redis.close = AsyncMock()
    mock_pubsub.close = AsyncMock()
    
    queue = asyncio.Queue()
    
    # Custom get_message mock to accept keyword args
    async def mock_get_message(*args, **kwargs):
        try:
            return await asyncio.wait_for(queue.get(), timeout=1.0)
        except asyncio.TimeoutError:
            return None

    mock_pubsub.get_message = mock_get_message
    mock_pubsub.subscribe = AsyncMock()
    mock_pubsub.unsubscribe = AsyncMock()
    
    with patch("redis.asyncio.from_url", return_value=mock_redis):
        broker = RedisSwarmBroker("redis://mock-connection")
        await broker.start()
        
        received = []
        async def on_msg(msg):
            received.append(msg)
            
        await broker.subscribe("test-channel", on_msg)
        mock_pubsub.subscribe.assert_called_with("test-channel")
        
        await broker.publish("test-channel", {"hello": "world"})
        mock_redis.publish.assert_called_with("test-channel", '{"hello": "world"}')
        
        # Simulate incoming pubsub message
        await queue.put({
            "type": "message",
            "channel": "test-channel",
            "data": '{"hello": "world"}'
        })
        
        # Allow loop to handle message callback
        await asyncio.sleep(0.1)
        assert len(received) == 1
        assert received[0] == {"hello": "world"}
        
        await broker.stop()


# Define MockRedisSwarmBroker to pass isinstance checks in dispatch
class MockRedisSwarmBroker(RedisSwarmBroker):
    def __init__(self):
        self.subscribers = {}
        
    async def start(self):
        pass
        
    async def stop(self):
        pass
        
    async def publish(self, channel, message):
        if channel in self.subscribers:
            for cb in list(self.subscribers[channel]):
                if inspect.iscoroutinefunction(cb):
                    await cb(message)
                else:
                    cb(message)
        
    async def subscribe(self, channel, callback):
        if channel not in self.subscribers:
            self.subscribers[channel] = []
        self.subscribers[channel].append(callback)
        
    async def unsubscribe(self, channel):
        self.subscribers.pop(channel, None)


@pytest.mark.asyncio
async def test_microservice_fault_tolerance_and_recovery():
    """Verify AgentCrew task delegation fault-tolerance and recovery during microservice container failure."""
    broker = MockRedisSwarmBroker()
    
    received_tasks = []
    async def mock_dev_service(msg):
        received_tasks.append(msg)
        node_id = msg["node_id"]
        resp = {
            "type": "task_response",
            "status": "completed",
            "node_id": node_id,
            "output": "Simulated Dev Output",
            "error": None
        }
        await broker.publish(f"swarm:task:{node_id}:response", resp)

    # 1. Connect the microservice daemon to the developer channel
    await broker.subscribe("swarm:role:developer", mock_dev_service)
    
    # Inject our mock broker inside core modules
    import sys
    old_brokers = {}
    for name, module in list(sys.modules.items()):
        if name.endswith("core.broker"):
            old_brokers[name] = getattr(module, "_global_broker", None)
            module._global_broker = broker

    try:
        from core.agent_crew import AgentCrew
        crew = AgentCrew()
        
        # Task should execute via microservice broker
        res1 = crew.dispatch_to_role(
            role="Developer",
            task_instructions="Task 1",
            input_parameters={},
            security_restrictions={},
            mock_directives={},
            validation_assertions=[]
        )
        assert res1["status"] == "completed"
        assert res1["output"] == "Simulated Dev Output"
        assert len(received_tasks) == 1
        
        # 2. Simulate container fail/crash by unsubscribing the microservice daemon
        await broker.unsubscribe("swarm:role:developer")
        
        # Should fail to reach microservice and fallback gracefully to local simulation
        res2 = crew.dispatch_to_role(
            role="Developer",
            task_instructions="Task 2",
            input_parameters={},
            security_restrictions={},
            mock_directives={},
            validation_assertions=[]
        )
        assert res2["status"] == "completed"
        assert "Execution result for role [Developer]" in res2["output"]
        
        # 3. Simulate container auto-recovery by restarting the service
        await broker.subscribe("swarm:role:developer", mock_dev_service)
        
        # Task should be served by the recovered microservice again
        res3 = crew.dispatch_to_role(
            role="Developer",
            task_instructions="Task 3",
            input_parameters={},
            security_restrictions={},
            mock_directives={},
            validation_assertions=[]
        )
        assert res3["status"] == "completed"
        assert res3["output"] == "Simulated Dev Output"
        assert len(received_tasks) == 2
    finally:
        for name, val in old_brokers.items():
            if sys.modules.get(name):
                sys.modules[name]._global_broker = val


def test_prometheus_telemetry_metrics_serialization():
    """Verify that Prometheus metrics include tenant tokens, sandbox execution counts, and API response latencies."""
    client = TestClient(app)
    
    # 1. Trigger token transactions to populate metrics
    from core.ledger import FinancialLedger
    ledger = FinancialLedger(".")
    ledger.record_transaction("test-session", "test-account", "test-provider", "gemini-2.5-flash", 100, 200, tenant_id="test-tenant")
    
    # 2. Trigger sandbox runs
    from core.sandbox import SandboxGuard
    try:
        SandboxGuard.execute_safe(".", "import os", tenant_id="test-tenant")
    except Exception:
        pass
        
    # 3. Trigger endpoint hits for response latency
    client.get("/v1/health")
    
    # 4. Request /metrics endpoint
    resp_metrics = client.get("/metrics")
    assert resp_metrics.status_code == 200
    
    from observability import PROMETHEUS_AVAILABLE
    if PROMETHEUS_AVAILABLE:
        content = resp_metrics.text
        # Validate that the metrics are registered and contain label values
        assert "las_tenant_tokens_total" in content
        assert 'tenant_id="test-tenant"' in content
        assert "las_sandbox_executions_total" in content
        assert "las_api_response_latency_seconds" in content
