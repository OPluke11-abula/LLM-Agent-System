import asyncio
from dataclasses import dataclass

import pytest

from agent_workspace.core.discussion_room import DiscussionRoom
from agent_workspace.core.debate_budget import (
    BudgetExhausted,
    DEFAULT_MAX_CONCURRENT_PROVIDER_CALLS,
    DEFAULT_MAX_HEALING_CALLS,
    DEFAULT_MAX_NESTED_DEPTH,
    DEFAULT_MAX_PROVIDER_CALLS,
    DEFAULT_MAX_RETRIES,
    DebateExecutionBudget,
    PermanentProviderError,
    ProviderResponse,
    RetryableProviderError,
    classify_provider_failure,
)


class AuthenticationFailure(PermanentProviderError):
    pass


class MalformedRequestFailure(PermanentProviderError):
    pass


@dataclass(frozen=True)
class CallObservation:
    initial_participants: int
    retry_attempts: int
    healing_calls: int
    nested_calls: int
    total_provider_calls: int
    max_concurrent_calls: int
    pending_task_count: int
    cancellation_propagated: bool


class FakeAccountManager:
    def __init__(self):
        self.account = {
            "id": "test-account",
            "provider": "fake",
            "model": "fake-model",
            "is_active": True,
            "tokens_used": 0,
            "token_budget": -1,
        }

    def get_active_account(self):
        return self.account

    def get_account(self, account_id):
        return self.account if account_id == self.account["id"] else None

    def record_usage(self, account_id, prompt_tokens, completion_tokens):
        self.account["tokens_used"] += prompt_tokens + completion_tokens

    def swap_to_fallback(self):
        return False


class InstrumentedProvider:
    def __init__(
        self,
        *,
        transient_failures=0,
        permanent_error=None,
        barrier_target=None,
        failure_usage=None,
    ):
        self.remaining_transient_failures = transient_failures
        self.permanent_error = permanent_error
        self.barrier_target = barrier_target
        self.failure_usage = failure_usage
        self.calls = 0
        self.non_healing_calls = 0
        self.failed_non_healing_calls = 0
        self.healing_calls = 0
        self.active_calls = 0
        self.max_concurrent_calls = 0
        self.started = asyncio.Event()
        self.barrier_ready = asyncio.Event()
        self.release = asyncio.Event()
        self.cancelled = asyncio.Event()
        self._tasks = []

    @staticmethod
    def _is_healing(system_prompt, messages):
        content = messages[0]["content"] if messages else ""
        return "self-healing engine" in system_prompt.lower() or "component/skill failed" in content.lower()

    @property
    def pending_task_count(self):
        current = asyncio.current_task()
        return len({id(task) for task in self._tasks if task is not current and not task.done()})

    async def complete(self, system_prompt, messages, tool_schemas, config):
        task = asyncio.current_task()
        self._tasks.append(task)
        self.calls += 1
        is_healing = self._is_healing(system_prompt, messages)
        if is_healing:
            self.healing_calls += 1
        else:
            self.non_healing_calls += 1

        self.active_calls += 1
        self.max_concurrent_calls = max(self.max_concurrent_calls, self.active_calls)
        self.started.set()
        if self.barrier_target and self.active_calls >= self.barrier_target:
            self.barrier_ready.set()
        try:
            if self.barrier_target:
                await self.release.wait()

            if is_healing:
                return ProviderResponse(
                    "success",
                    "{}",
                    {"prompt_tokens": 6, "completion_tokens": 2, "total_tokens": 8},
                )
            if self.permanent_error is not None:
                self.failed_non_healing_calls += 1
                error = self.permanent_error("permanent provider failure")
                if self.failure_usage is not None:
                    error.usage = self.failure_usage
                raise error
            if self.remaining_transient_failures:
                self.remaining_transient_failures -= 1
                self.failed_non_healing_calls += 1
                error = RetryableProviderError("transient provider failure")
                if self.failure_usage is not None:
                    error.usage = self.failure_usage
                raise error
            return ProviderResponse(
                "success",
                "provider response",
                {"prompt_tokens": 10, "completion_tokens": 4, "total_tokens": 14},
            )
        except asyncio.CancelledError:
            self.cancelled.set()
            raise
        finally:
            self.active_calls -= 1


def _make_room(tmp_path, provider):
    room = DiscussionRoom(workspace_path=str(tmp_path))
    room.account_manager = FakeAccountManager()
    room.telemetry_callbacks = []
    room._resolve_agent_provider = lambda *args, **kwargs: (
        provider,
        {"model": "fake-model", "max_tokens": 1024},
        "test-account",
    )
    return room


def _agents(count=1):
    return [{"role": "analyst", "name": f"Agent {index}"} for index in range(count)]


def _observe(provider, initial_participants, nested_calls=0, cancellation_propagated=False):
    return CallObservation(
        initial_participants=initial_participants,
        retry_attempts=provider.failed_non_healing_calls,
        healing_calls=provider.healing_calls,
        nested_calls=nested_calls,
        total_provider_calls=provider.calls,
        max_concurrent_calls=provider.max_concurrent_calls,
        pending_task_count=provider.pending_task_count,
        cancellation_propagated=cancellation_propagated,
    )


@pytest.mark.asyncio
async def test_characterization_successful_debate_path(tmp_path):
    provider = InstrumentedProvider()
    room = _make_room(tmp_path, provider)

    result = await room.run(topic="success", agents=_agents(), max_rounds=1)
    observation = _observe(provider, initial_participants=1)

    assert result["transcript"]
    assert observation == CallObservation(1, 0, 0, 0, 2, 1, 0, False)


@pytest.mark.asyncio
async def test_characterization_one_transient_failure_and_healing(tmp_path):
    provider = InstrumentedProvider(transient_failures=1)
    room = _make_room(tmp_path, provider)

    await room.run(topic="one transient", agents=_agents(), max_rounds=1)
    observation = _observe(provider, initial_participants=1)

    assert observation == CallObservation(1, 1, 1, 0, 4, 1, 0, False)


@pytest.mark.asyncio
async def test_characterization_repeated_transient_failures(tmp_path):
    provider = InstrumentedProvider(transient_failures=4)
    room = _make_room(tmp_path, provider)

    await room.run(topic="repeated transient", agents=_agents(), max_rounds=1)
    observation = _observe(provider, initial_participants=1)

    assert observation == CallObservation(1, 4, 3, 0, 8, 1, 0, False)


@pytest.mark.asyncio
async def test_characterization_permanent_authentication_failure_is_not_retried(tmp_path):
    provider = InstrumentedProvider(permanent_error=AuthenticationFailure)
    room = _make_room(tmp_path, provider)

    result = await room.run(topic="auth failure", agents=_agents(), max_rounds=1)
    observation = _observe(provider, initial_participants=1)

    assert "Connection Error" in result["transcript"][0]["content"]
    assert "Error synthesizing consensus" in result["consensus_summary"]
    assert observation == CallObservation(1, 2, 0, 0, 2, 1, 0, False)


@pytest.mark.asyncio
async def test_characterization_malformed_request_failure_is_not_retried(tmp_path):
    provider = InstrumentedProvider(permanent_error=MalformedRequestFailure)
    room = _make_room(tmp_path, provider)

    result = await room.run(topic="malformed request", agents=_agents(), max_rounds=1)
    observation = _observe(provider, initial_participants=1)

    assert "Connection Error" in result["transcript"][0]["content"]
    assert "Error synthesizing consensus" in result["consensus_summary"]
    assert observation == CallObservation(1, 2, 0, 0, 2, 1, 0, False)


@pytest.mark.asyncio
async def test_budget_exhaustion_is_deterministic(tmp_path):
    provider = InstrumentedProvider(transient_failures=10)
    room = _make_room(tmp_path, provider)
    budget = DebateExecutionBudget(max_provider_calls=1, max_retries=1, max_healing_calls=1)

    with pytest.raises(BudgetExhausted, match="budget_exhausted: provider_calls"):
        await room.run(topic="bounded", agents=_agents(), max_rounds=1, _execution_budget=budget)
    assert provider.calls == 1


@pytest.mark.asyncio
async def test_characterization_nested_sub_swarm_calls_are_included(tmp_path):
    provider = InstrumentedProvider()
    room = _make_room(tmp_path, provider)

    await room.run(
        topic="nested",
        agents=_agents(),
        max_rounds=1,
        sub_problems=[{"topic": "subtask", "agents": _agents(), "max_rounds": 1}],
    )
    observation = _observe(provider, initial_participants=1, nested_calls=1)

    assert observation == CallObservation(1, 0, 0, 1, 4, 1, 0, False)


@pytest.mark.asyncio
async def test_characterization_nested_failure_includes_healing_call(tmp_path):
    provider = InstrumentedProvider(transient_failures=1)
    room = _make_room(tmp_path, provider)

    await room.run(
        topic="nested failure",
        agents=_agents(),
        max_rounds=1,
        sub_problems=[{"topic": "subtask", "agents": _agents(), "max_rounds": 1}],
    )
    observation = _observe(provider, initial_participants=1, nested_calls=1)

    assert observation == CallObservation(1, 1, 1, 1, 6, 1, 0, False)


@pytest.mark.asyncio
async def test_characterization_nested_sub_swarms_measure_global_concurrency(tmp_path):
    provider = InstrumentedProvider(barrier_target=3)
    room = _make_room(tmp_path, provider)
    sub_problems = [
        {"topic": f"subtask-{index}", "agents": _agents(), "max_rounds": 1}
        for index in range(3)
    ]

    task = asyncio.create_task(
        room.run(topic="parallel nested", agents=_agents(), max_rounds=1, sub_problems=sub_problems)
    )
    await provider.barrier_ready.wait()
    assert provider.max_concurrent_calls == 3
    provider.release.set()
    await task
    observation = _observe(provider, initial_participants=1, nested_calls=3)

    assert observation == CallObservation(1, 0, 0, 3, 8, 3, 0, False)


@pytest.mark.asyncio
async def test_characterization_parent_cancellation_propagates_and_leaves_no_pending_provider_tasks(tmp_path):
    provider = InstrumentedProvider(barrier_target=1)
    room = _make_room(tmp_path, provider)
    budget = DebateExecutionBudget()
    task = asyncio.create_task(
        room.run(topic="cancel", agents=_agents(), max_rounds=1, _execution_budget=budget)
    )

    await provider.barrier_ready.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    observation = _observe(
        provider,
        initial_participants=1,
        cancellation_propagated=provider.cancelled.is_set(),
    )
    assert observation == CallObservation(1, 0, 0, 0, 1, 1, 0, True)
    assert budget.exhaustion_reason is None


def test_default_budget_is_derived_from_current_profile():
    budget = DebateExecutionBudget()

    assert budget.max_provider_calls == DEFAULT_MAX_PROVIDER_CALLS == 64
    assert budget.max_retries == DEFAULT_MAX_RETRIES == 12
    assert budget.max_healing_calls == DEFAULT_MAX_HEALING_CALLS == 8
    assert budget.max_nested_depth == DEFAULT_MAX_NESTED_DEPTH == 1
    assert budget.max_concurrent_provider_calls == DEFAULT_MAX_CONCURRENT_PROVIDER_CALLS == 3
    assert 5 * 2 + 1 <= budget.max_provider_calls
    assert 4 * (5 * 2 + 1) <= budget.max_provider_calls


def test_failure_classifier_prefers_status_and_permanent_quota():
    class RateLimitError(Exception):
        status_code = 429

    assert classify_provider_failure(RateLimitError()).retryable
    assert classify_provider_failure("quota exhausted").reason == "permanent_provider_failure"
    assert classify_provider_failure(asyncio.CancelledError()).reason == "cancelled"


@pytest.mark.asyncio
async def test_budget_tracks_retry_healing_and_known_usage_once(tmp_path):
    provider = InstrumentedProvider(transient_failures=1)
    room = _make_room(tmp_path, provider)
    budget = DebateExecutionBudget()

    await room.run(topic="usage", agents=_agents(), max_rounds=1, _execution_budget=budget)

    assert budget.provider_calls == 4
    assert budget.retries == 1
    assert budget.healing_calls == 1
    assert budget.known_prompt_tokens == 26
    assert budget.known_completion_tokens == 10
    assert budget.known_total_tokens == 36
    assert budget.known_cost_usd > 0


@pytest.mark.asyncio
async def test_failed_usage_metadata_is_accounted_without_invention(tmp_path):
    provider = InstrumentedProvider(
        permanent_error=AuthenticationFailure,
        failure_usage={"prompt_tokens": 7, "completion_tokens": 3, "total_tokens": 10},
    )
    room = _make_room(tmp_path, provider)
    budget = DebateExecutionBudget()

    await room.run(topic="failed usage", agents=_agents(), max_rounds=1, _execution_budget=budget)

    assert budget.provider_calls == 2
    assert budget.healing_calls == 0
    assert budget.known_prompt_tokens == 14
    assert budget.known_completion_tokens == 6
    assert budget.known_total_tokens == 20


@pytest.mark.asyncio
async def test_default_success_profile_fits_global_budget(tmp_path):
    provider = InstrumentedProvider()
    room = _make_room(tmp_path, provider)
    budget = DebateExecutionBudget()

    await room.run(topic="profile", agents=_agents(5), max_rounds=2, _execution_budget=budget)

    assert budget.provider_calls == 11
    assert budget.provider_calls < budget.max_provider_calls
    assert budget.retries == 0
    assert budget.healing_calls == 0


@pytest.mark.asyncio
async def test_default_nested_profile_has_finite_global_bound(tmp_path):
    provider = InstrumentedProvider()
    room = _make_room(tmp_path, provider)
    budget = DebateExecutionBudget()
    sub_problems = [
        {"topic": f"child-{index}", "agents": _agents(5), "max_rounds": 2}
        for index in range(3)
    ]

    await room.run(
        topic="nested profile",
        agents=_agents(5),
        max_rounds=2,
        sub_problems=sub_problems,
        _execution_budget=budget,
    )

    assert budget.provider_calls == 44
    assert budget.provider_calls <= budget.max_provider_calls
    assert budget.current_nested_depth == 0
    assert budget.peak_nested_depth == 1


@pytest.mark.asyncio
async def test_nested_work_shares_provider_cap_and_depth(tmp_path):
    provider = InstrumentedProvider()
    room = _make_room(tmp_path, provider)
    budget = DebateExecutionBudget(max_provider_calls=4)

    await room.run(
        topic="nested budget",
        agents=_agents(),
        max_rounds=1,
        sub_problems=[{"topic": "child", "agents": _agents(), "max_rounds": 1}],
        _execution_budget=budget,
    )

    assert budget.provider_calls == 4
    assert budget.current_nested_depth == 0
    assert budget.peak_nested_depth == 1


@pytest.mark.asyncio
async def test_nested_depth_exhaustion_precedes_provider_work(tmp_path):
    provider = InstrumentedProvider()
    room = _make_room(tmp_path, provider)
    budget = DebateExecutionBudget(max_nested_depth=0)

    with pytest.raises(BudgetExhausted, match="budget_exhausted: nested_depth"):
        await room.run(
            topic="too deep",
            agents=_agents(),
            max_rounds=1,
            sub_problems=[{"topic": "child", "agents": _agents(), "max_rounds": 1}],
            _execution_budget=budget,
        )
    assert provider.calls == 0


@pytest.mark.asyncio
async def test_healing_exhaustion_does_not_restart_retry_chain(tmp_path):
    provider = InstrumentedProvider(transient_failures=1)
    room = _make_room(tmp_path, provider)
    budget = DebateExecutionBudget(max_healing_calls=0)

    await room.run(topic="no healing", agents=_agents(), max_rounds=1, _execution_budget=budget)

    assert budget.provider_calls == 3
    assert budget.retries == 1
    assert budget.healing_calls == 0
    assert provider.healing_calls == 0


@pytest.mark.asyncio
async def test_retry_exhaustion_is_finite_and_deterministic(tmp_path):
    provider = InstrumentedProvider(transient_failures=10)
    room = _make_room(tmp_path, provider)
    budget = DebateExecutionBudget(max_retries=1, max_healing_calls=0)

    result = await room.run(topic="retry cap", agents=_agents(), max_rounds=1, _execution_budget=budget)

    assert budget.provider_calls == 3
    assert budget.retries == 1
    assert budget.exhaustion_reason == "retries"
    assert "budget_exhausted: retries" in result["transcript"][0]["content"]


@pytest.mark.asyncio
async def test_concurrent_provider_calls_respect_shared_cap(tmp_path):
    provider = InstrumentedProvider(barrier_target=2)
    room = _make_room(tmp_path, provider)
    budget = DebateExecutionBudget(max_concurrent_provider_calls=2)
    sub_problems = [
        {"topic": f"child-{index}", "agents": _agents(), "max_rounds": 1}
        for index in range(2)
    ]

    task = asyncio.create_task(
        room.run(
            topic="concurrency cap",
            agents=_agents(),
            max_rounds=1,
            sub_problems=sub_problems,
            _execution_budget=budget,
        )
    )
    await provider.barrier_ready.wait()
    assert provider.max_concurrent_calls == 2
    provider.release.set()
    await task
    assert budget.peak_concurrent_provider_calls == 2
    assert budget.current_concurrent_provider_calls == 0


@pytest.mark.asyncio
async def test_nested_parent_cancellation_cleans_children_and_restores_depth(tmp_path):
    provider = InstrumentedProvider(barrier_target=3)
    room = _make_room(tmp_path, provider)
    budget = DebateExecutionBudget()
    sub_problems = [
        {"topic": f"cancel-child-{index}", "agents": _agents(), "max_rounds": 1}
        for index in range(3)
    ]

    task = asyncio.create_task(
        room.run(
            topic="cancel-parent",
            agents=_agents(),
            max_rounds=1,
            sub_problems=sub_problems,
            _execution_budget=budget,
        )
    )
    await provider.barrier_ready.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert provider.cancelled.is_set()
    assert provider.pending_task_count == 0
    assert provider.active_calls == 0
    assert budget.current_concurrent_provider_calls == 0
    assert budget.current_nested_depth == 0


@pytest.mark.asyncio
async def test_cancellation_during_retry_backoff_does_not_consume_retry(tmp_path, monkeypatch):
    provider = InstrumentedProvider(transient_failures=1)
    room = _make_room(tmp_path, provider)
    budget = DebateExecutionBudget()
    backoff_started = asyncio.Event()
    backoff_release = asyncio.Event()

    async def controlled_backoff(_delay):
        backoff_started.set()
        await backoff_release.wait()

    from agent_workspace.core import discussion_room as discussion_room_module

    monkeypatch.setattr(discussion_room_module.asyncio, "sleep", controlled_backoff)
    task = asyncio.create_task(
        room.run(topic="cancel-backoff", agents=_agents(), max_rounds=1, _execution_budget=budget)
    )
    await backoff_started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert provider.calls == 2
    assert budget.retries == 0
    assert budget.exhaustion_reason is None
    assert budget.current_concurrent_provider_calls == 0
    assert provider.pending_task_count == 0


@pytest.mark.asyncio
async def test_canceled_semaphore_wait_does_not_consume_provider_attempt(tmp_path):
    provider = InstrumentedProvider(barrier_target=1)
    room = _make_room(tmp_path, provider)

    class ObservableBudget(DebateExecutionBudget):
        def __post_init__(self):
            super().__post_init__()
            self.waiting = asyncio.Event()

        async def _acquire_provider(self):
            if self.current_concurrent_provider_calls >= self.max_concurrent_provider_calls:
                self.waiting.set()
            await super()._acquire_provider()

    budget = ObservableBudget(max_concurrent_provider_calls=1)
    first = asyncio.create_task(
        room.run(topic="first", agents=_agents(), max_rounds=1, _execution_budget=budget)
    )
    await provider.barrier_ready.wait()
    second = asyncio.create_task(
        room.run(topic="second", agents=_agents(), max_rounds=1, _execution_budget=budget)
    )
    await budget.waiting.wait()
    second.cancel()
    with pytest.raises(asyncio.CancelledError):
        await second

    assert budget.provider_calls == 1
    assert budget.current_concurrent_provider_calls == 1
    provider.release.set()
    await first
    assert budget.current_concurrent_provider_calls == 0


@pytest.mark.asyncio
async def test_broker_timeout_falls_back_without_duplicate_local_provider_attempt(tmp_path, monkeypatch):
    from agent_workspace.core import broker as broker_module
    from agent_workspace.core import discussion_room as discussion_room_module
    from agent_workspace.core.broker import RedisSwarmBroker

    class FakeRedisBroker(RedisSwarmBroker):
        def __init__(self):
            self.unsubscribed = []

        async def subscribe(self, channel, callback):
            return None

        async def publish(self, channel, message):
            return None

        async def unsubscribe(self, channel):
            self.unsubscribed.append(channel)

    provider = InstrumentedProvider()
    room = _make_room(tmp_path, provider)
    broker = FakeRedisBroker()
    fallback_calls = 0
    response = ProviderResponse(
        "text",
        "local fallback",
        {"prompt_tokens": 2, "completion_tokens": 1, "total_tokens": 3},
    )

    async def fail_fast(_awaitable, _timeout):
        raise asyncio.TimeoutError()

    async def fallback(*_args, **_kwargs):
        nonlocal fallback_calls
        fallback_calls += 1
        return {
            "status": "success",
            "response": response,
            "config": {"model": "fake-model"},
            "account_id": "test-account",
        }

    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setattr(broker_module, "get_broker", lambda **_kwargs: broker)
    monkeypatch.setattr(discussion_room_module.asyncio, "wait_for", fail_fast)
    monkeypatch.setattr(room, "_complete_with_budget", fallback)
    budget = DebateExecutionBudget()

    result = await room.run(
        topic="broker timeout",
        agents=_agents(),
        max_rounds=1,
        _execution_budget=budget,
    )

    assert result["transcript"][0]["content"] == "local fallback"
    assert fallback_calls == 2
    assert len(broker.unsubscribed) == 1
    assert budget.provider_calls == 1
    assert budget.current_concurrent_provider_calls == 0


@pytest.mark.asyncio
async def test_broker_parent_cancellation_skips_fallback_and_unsubscribes(tmp_path, monkeypatch):
    from agent_workspace.core import broker as broker_module
    from agent_workspace.core import discussion_room as discussion_room_module
    from agent_workspace.core.broker import RedisSwarmBroker

    class FakeRedisBroker(RedisSwarmBroker):
        def __init__(self):
            self.published = asyncio.Event()
            self.unsubscribed = asyncio.Event()

        async def subscribe(self, channel, callback):
            return None

        async def publish(self, channel, message):
            self.published.set()

        async def unsubscribe(self, channel):
            self.unsubscribed.set()

    provider = InstrumentedProvider()
    room = _make_room(tmp_path, provider)
    broker = FakeRedisBroker()
    fallback_calls = 0

    async def blocked_wait(_awaitable, **_kwargs):
        await asyncio.Future()

    async def fallback(*_args, **_kwargs):
        nonlocal fallback_calls
        fallback_calls += 1
        raise AssertionError("fallback must not run after parent cancellation")

    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setattr(broker_module, "get_broker", lambda **_kwargs: broker)
    monkeypatch.setattr(discussion_room_module.asyncio, "wait_for", blocked_wait)
    monkeypatch.setattr(room, "_complete_with_budget", fallback)
    task = asyncio.create_task(
        room.run(topic="broker cancel", agents=_agents(), max_rounds=1)
    )
    await broker.published.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert fallback_calls == 0
    assert broker.unsubscribed.is_set()
