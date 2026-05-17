"""
FastAPI service adapter for FindAi Studio LAS.

The API layer is intentionally external to the closed-loop engine. It creates
AgentEngine and AgentRouter instances through their public interfaces and keeps
HTTP/SSE concerns out of core runtime modules.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

workspace = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, workspace)

from core.engine import AgentEngine
from core.router import AgentRouter


API_VERSION = "0.1.0"


class ChatRequest(BaseModel):
    msg: str = Field(..., min_length=1)
    session: str = "default-session"
    allowed_tools: list[str] | None = None


class ChatResponse(BaseModel):
    session: str
    response: str


class TaskRequest(ChatRequest):
    task_id: str | None = None


class TaskSubmitResponse(BaseModel):
    task_id: str
    session: str
    status: str


@dataclass
class TaskRecord:
    task_id: str
    session: str
    msg: str
    status: str
    submitted_at: str
    started_at: str | None = None
    completed_at: str | None = None
    response: str | None = None
    error: str | None = None


app = FastAPI(
    title="FindAi Studio LAS API",
    version=API_VERSION,
    description="Non-invasive REST/SSE adapter for the LLM-Agent-System runtime.",
)

_engine: AgentEngine | None = None
_task_records: dict[str, TaskRecord] = {}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_engine() -> AgentEngine:
    global _engine
    if _engine is None:
        _engine = AgentEngine(workspace_path=workspace)
    return _engine


def build_router(session_id: str) -> AgentRouter:
    return AgentRouter(get_engine(), session_id=session_id)


def ensure_llm_configured() -> None:
    # The current default provider is Google GenAI. Keep this check in the API
    # adapter so core provider logic remains unchanged.
    if not os.environ.get("GOOGLE_API_KEY"):
        raise HTTPException(
            status_code=503,
            detail="GOOGLE_API_KEY is not set. Configure the provider before calling chat, stream, or task endpoints.",
        )


def sse_event(event: dict[str, Any]) -> str:
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


@app.get("/v1/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "api_version": API_VERSION,
        "workspace": workspace,
        "google_api_key_configured": bool(os.environ.get("GOOGLE_API_KEY")),
    }


@app.post("/v1/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    ensure_llm_configured()
    router = build_router(request.session)
    response = await router.run_agent_loop(request.msg, allowed_tools=request.allowed_tools)
    return ChatResponse(session=request.session, response=response)


@app.post("/v1/stream")
async def stream(request: ChatRequest) -> StreamingResponse:
    ensure_llm_configured()

    async def event_generator():
        router = build_router(request.session)
        async for event in router.stream_agent_loop(request.msg, allowed_tools=request.allowed_tools):
            yield sse_event({"session": request.session, **event})

    return StreamingResponse(event_generator(), media_type="text/event-stream")


async def run_background_task(record: TaskRecord, allowed_tools: list[str] | None) -> None:
    record.status = "running"
    record.started_at = utc_now()
    try:
        router = build_router(record.session)
        record.response = await router.run_agent_loop(record.msg, allowed_tools=allowed_tools)
        record.status = "completed"
    except Exception as error:  # API adapter boundary: capture task failure state.
        record.status = "error"
        record.error = str(error)
    finally:
        record.completed_at = utc_now()


@app.post("/v1/task", response_model=TaskSubmitResponse)
async def submit_task(request: TaskRequest) -> TaskSubmitResponse:
    ensure_llm_configured()
    task_id = request.task_id or f"task-{uuid.uuid4()}"
    if task_id in _task_records:
        raise HTTPException(status_code=409, detail=f"Task already exists: {task_id}")

    record = TaskRecord(
        task_id=task_id,
        session=request.session,
        msg=request.msg,
        status="queued",
        submitted_at=utc_now(),
    )
    _task_records[task_id] = record
    asyncio.create_task(run_background_task(record, request.allowed_tools))
    return TaskSubmitResponse(task_id=task_id, session=request.session, status=record.status)


@app.get("/v1/session/{session_id}")
async def get_session(session_id: str) -> dict[str, Any]:
    memory_path = Path(workspace) / "memory" / f"{session_id}.json"
    memory: dict[str, Any] = {}
    if memory_path.is_file():
        try:
            memory = json.loads(memory_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            memory = {"error": "memory file is not valid JSON"}

    tasks = [
        asdict(record)
        for record in _task_records.values()
        if record.session == session_id
    ]
    return {
        "session": session_id,
        "memory_path": str(memory_path),
        "memory": memory,
        "tasks": tasks,
    }
