import asyncio
from pathlib import Path

import pytest
from types import SimpleNamespace

from agent_workspace import api
from agent_workspace.core import broker
from agent_workspace.core.runtime_config import FeatureFlagError, RuntimeFeatureFlags
from agent_workspace import service


def test_runtime_features_default_disabled():
    flags = RuntimeFeatureFlags.from_env({})
    assert flags.enable_stripe is False
    assert flags.enable_redis_swarm is False
    assert flags.enable_multi_worker is False
    assert flags.enable_audit_consensus is False


@pytest.mark.parametrize("value", ["false", "0", "no", "off", "FALSE", " Off "])
def test_runtime_features_explicit_false(value):
    flags = RuntimeFeatureFlags.from_env({"LAS_ENABLE_STRIPE": value})
    assert flags.enable_stripe is False


def test_runtime_features_all_explicit_false():
    values = {
        "LAS_ENABLE_STRIPE": "off",
        "LAS_ENABLE_REDIS_SWARM": "0",
        "LAS_ENABLE_MULTI_WORKER": "no",
        "LAS_ENABLE_AUDIT_CONSENSUS": "false",
    }
    assert RuntimeFeatureFlags.from_env(values) == RuntimeFeatureFlags()


@pytest.mark.parametrize("value", ["true", "1", "yes", "on", "TRUE", " On "])
def test_runtime_features_explicit_true(value):
    flags = RuntimeFeatureFlags.from_env({"LAS_ENABLE_STRIPE": value})
    assert flags.enable_stripe is True


def test_runtime_features_reject_invalid_boolean():
    with pytest.raises(FeatureFlagError, match="LAS_ENABLE_STRIPE"):
        RuntimeFeatureFlags.from_env({"LAS_ENABLE_STRIPE": "enabled"})


@pytest.mark.asyncio
async def test_api_lifespan_default_does_not_start_optional_services(monkeypatch):
    created = []

    class DummyTask:
        def cancel(self):
            created.append("cancel")

    def forbidden(*args, **kwargs):
        raise AssertionError("optional service started")

    def no_task(coroutine):
        coroutine.close()
        created.append("task")
        return DummyTask()

    monkeypatch.setattr(api, "get_runtime_feature_flags", lambda: RuntimeFeatureFlags(), raising=False)
    monkeypatch.setattr(api.asyncio, "create_task", no_task)
    monkeypatch.setattr("agent_workspace.routes.admin.start_stripe_billing_scheduler", forbidden)
    monkeypatch.setattr("agent_workspace.routes.collaboration.collab_manager.start_redis_listener", forbidden)
    monkeypatch.setattr("agent_workspace.core.broker.get_broker", forbidden)
    monkeypatch.setattr("agent_workspace.core.audit_ledger.AuditConsensusDaemon", forbidden)

    async with api.lifespan(api.app):
        assert created == []


@pytest.mark.asyncio
async def test_api_lifespan_enabled_services_are_cancelled(monkeypatch):
    flags = RuntimeFeatureFlags(True, True, True, True)
    events = []
    tasks = []
    real_create_task = asyncio.create_task

    async def wait_forever(name):
        events.append(name)
        await asyncio.Event().wait()

    class FakeBroker:
        async def start(self):
            events.append("broker_start")

        async def stop(self):
            events.append("broker_stop")

        async def subscribe(self, *args):
            events.append("broker_subscribe")

    class FakeAuditDaemon:
        def __init__(self, ledger, node_id):
            events.append("audit_init")

        async def start(self):
            await wait_forever("audit_start")

        async def stop(self):
            events.append("audit_stop")

    def track(coroutine):
        task = real_create_task(coroutine)
        tasks.append(task)
        return task

    monkeypatch.setattr(api, "get_runtime_feature_flags", lambda: flags, raising=False)
    monkeypatch.setattr(api.asyncio, "create_task", track)
    monkeypatch.setattr("agent_workspace.routes.admin.start_stripe_billing_scheduler", lambda: wait_forever("stripe"))
    monkeypatch.setattr("agent_workspace.routes.collaboration.collab_manager.start_redis_listener", lambda: wait_forever("redis"))
    monkeypatch.setattr("agent_workspace.core.broker.get_broker", lambda **kwargs: FakeBroker())
    monkeypatch.setattr("agent_workspace.core.audit_ledger.AuditLedger", lambda workspace: SimpleNamespace())
    monkeypatch.setattr("agent_workspace.core.audit_ledger.AuditConsensusDaemon", FakeAuditDaemon)
    monkeypatch.setattr(
        "agent_workspace.core.swarm_coordinator.SwarmCoordinator",
        SimpleNamespace(
            check_heartbeats=lambda: events.append("heartbeat"),
            register_or_update_node=lambda **kwargs: events.append("discovery"),
        ),
    )

    async with api.lifespan(api.app):
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        assert {"stripe", "redis", "audit_start"}.issubset(events)
        assert "heartbeat" in events
        assert "broker_subscribe" in events

    await asyncio.gather(*tasks, return_exceptions=True)
    assert all(task.done() for task in tasks)
    assert "broker_stop" in events
    assert "audit_stop" in events


@pytest.mark.asyncio
async def test_swarm_service_default_does_not_import_redis(monkeypatch):
    monkeypatch.setattr(service, "get_runtime_feature_flags", lambda: RuntimeFeatureFlags(), raising=False)
    real_import = __import__

    def reject_redis(name, *args, **kwargs):
        if name.startswith("redis"):
            raise AssertionError("redis imported in local profile")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", reject_redis)
    worker = service.SwarmAgentService("dev", "redis://unused")
    await worker.start()
    assert worker.client is None
    assert worker._is_running is False


def test_broker_default_does_not_select_redis(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("redis broker selected in local profile")

    monkeypatch.setattr(broker, "get_runtime_feature_flags", lambda: RuntimeFeatureFlags(), raising=False)
    monkeypatch.setattr(broker, "REDIS_AVAILABLE", True)
    monkeypatch.setattr(broker, "RedisSwarmBroker", forbidden)
    monkeypatch.setattr(broker, "_global_broker", None)
    result = broker.get_broker(reset=True)
    assert isinstance(result, broker.InMemorySwarmBroker)


def test_container_defaults_disable_optional_services():
    root = Path(__file__).parents[2]
    for filename in ("Dockerfile", "docker-compose.yml", "docker-compose.microservices.yml"):
        content = (root / filename).read_text(encoding="utf-8")
        assert "LAS_ENABLE_STRIPE" in content
        assert "LAS_ENABLE_REDIS_SWARM" in content
        assert "LAS_ENABLE_MULTI_WORKER" in content
        assert "LAS_ENABLE_AUDIT_CONSENSUS" in content
