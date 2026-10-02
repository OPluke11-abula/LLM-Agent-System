import asyncio
import importlib
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

from agent_workspace.routes import chat
from agent_workspace.routes.schemas import TaskRequest


@pytest.fixture(autouse=True)
def reset_task_state(monkeypatch):
    chat._task_records.clear()
    chat._task_handles.clear()
    monkeypatch.setattr(chat, "MAX_CONCURRENT_TASKS", 1, raising=False)
    monkeypatch.setattr(chat, "TASK_RECORD_TTL_SECONDS", 3600, raising=False)
    monkeypatch.setattr(chat, "TASK_EXECUTION_TIMEOUT_SECONDS", 0.05, raising=False)
    yield
    chat._task_records.clear()
    chat._task_handles.clear()


def test_task_concurrency_uses_documented_environment_name(monkeypatch):
    monkeypatch.setenv("LAS_TASK_MAX_CONCURRENCY", "3")
    importlib.reload(chat)
    assert chat.MAX_CONCURRENT_TASKS == 3


@pytest.mark.asyncio
async def test_task_admission_is_bounded(monkeypatch):
    release = asyncio.Event()

    async def blocked_task(record, allowed_tools, account_id):
        await release.wait()

    monkeypatch.setattr(chat, "run_background_task", blocked_task)
    monkeypatch.setattr(chat, "ensure_llm_configured", lambda: None)

    first = await chat.submit_task(TaskRequest(session="session-1", msg="one", task_id="task-1"))
    await asyncio.sleep(0)
    assert first.status == "queued"

    with pytest.raises(HTTPException, match="capacity"):
        await chat.submit_task(TaskRequest(session="session-1", msg="two", task_id="task-2"))
    release.set()
    await asyncio.sleep(0)


@pytest.mark.asyncio
async def test_duplicate_task_submission_is_idempotent(monkeypatch):
    monkeypatch.setattr(chat, "run_background_task", lambda *args: asyncio.sleep(0.1))
    monkeypatch.setattr(chat, "ensure_llm_configured", lambda: None)
    request = TaskRequest(session="session-1", msg="same", task_id="task-1")

    first = await chat.submit_task(request)
    second = await chat.submit_task(request)
    assert second.task_id == first.task_id
    assert len(chat._task_records) == 1


@pytest.mark.asyncio
async def test_task_timeout_sets_terminal_status(monkeypatch):
    class SlowRouter:
        async def run_agent_loop(self, *args, **kwargs):
            await asyncio.sleep(1)

    monkeypatch.setattr(chat, "build_router", lambda session: SlowRouter())
    record = chat.TaskRecord("task-timeout", "session-1", "slow", "queued", chat.utc_now())

    await chat.run_background_task(record, None, None)
    assert record.status == "timeout"
    assert record.completed_at is not None


@pytest.mark.asyncio
async def test_task_cancellation_sets_terminal_status(monkeypatch):
    class SlowRouter:
        async def run_agent_loop(self, *args, **kwargs):
            await asyncio.sleep(1)

    monkeypatch.setattr(chat, "build_router", lambda session: SlowRouter())
    record = chat.TaskRecord("task-cancel", "session-1", "slow", "queued", chat.utc_now())
    task = asyncio.create_task(chat.run_background_task(record, None, None))
    await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert record.status == "cancelled"
    assert record.completed_at is not None


def test_task_record_ttl_cleanup():
    expired = datetime.now(timezone.utc) - timedelta(hours=2)
    chat._task_records["expired"] = chat.TaskRecord(
        "expired", "session-1", "old", "completed", expired.isoformat(), completed_at=expired.isoformat()
    )
    chat._cleanup_task_records()
    assert "expired" not in chat._task_records
