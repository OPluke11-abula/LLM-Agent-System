import asyncio
from dataclasses import dataclass

import pytest

from agent_workspace.core.discussion_room import DiscussionRoom


class AuthenticationFailure(Exception):
    pass


class MalformedRequestFailure(Exception):
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
    ):
        self.remaining_transient_failures = transient_failures
        self.permanent_error = permanent_error
        self.barrier_target = barrier_target
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
                return "success", "{}"
            if self.permanent_error is not None:
                self.failed_non_healing_calls += 1
                raise self.permanent_error("permanent provider failure")
            if self.remaining_transient_failures:
                self.remaining_transient_failures -= 1
                self.failed_non_healing_calls += 1
                raise RuntimeError("transient provider failure")
            return "success", "provider response"
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
async def test_characterization_permanent_authentication_failure_is_retried_currently(tmp_path):
    provider = InstrumentedProvider(permanent_error=AuthenticationFailure)
    room = _make_room(tmp_path, provider)

    result = await room.run(topic="auth failure", agents=_agents(), max_rounds=1)
    observation = _observe(provider, initial_participants=1)

    assert "Connection Error" in result["transcript"][0]["content"]
    assert "Error synthesizing consensus" in result["consensus_summary"]
    assert observation == CallObservation(1, 8, 6, 0, 14, 1, 0, False)


@pytest.mark.asyncio
async def test_characterization_malformed_request_failure_is_retried_currently(tmp_path):
    provider = InstrumentedProvider(permanent_error=MalformedRequestFailure)
    room = _make_room(tmp_path, provider)

    result = await room.run(topic="malformed request", agents=_agents(), max_rounds=1)
    observation = _observe(provider, initial_participants=1)

    assert "Connection Error" in result["transcript"][0]["content"]
    assert "Error synthesizing consensus" in result["consensus_summary"]
    assert observation == CallObservation(1, 8, 6, 0, 14, 1, 0, False)


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
    task = asyncio.create_task(room.run(topic="cancel", agents=_agents(), max_rounds=1))

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
