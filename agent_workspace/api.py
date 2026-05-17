"""
FastAPI service adapter for FindAi Studio LAS.

The API layer is intentionally external to the closed-loop engine. It creates
AgentEngine and AgentRouter instances through their public interfaces and keeps
HTTP/SSE concerns out of core runtime modules.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field
import yaml

workspace = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, workspace)

from observability import (
    configure_logging,
    generate_latest,
    CONTENT_TYPE_LATEST,
    PROMETHEUS_AVAILABLE,
    REQUEST_COUNT,
    REQUEST_LATENCY,
    REQUEST_ERRORS,
)

configure_logging(json_output=True)
logger = logging.getLogger(__name__)

from core.engine import AgentEngine
from core.router import AgentRouter

try:
    from long_term_memory import LongTermMemoryStore
except ImportError:
    from agent_workspace.long_term_memory import LongTermMemoryStore

try:
    from tool_manifest import ToolManifest
except ImportError:
    from agent_workspace.tool_manifest import ToolManifest


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


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Record request count, latency, and errors for every endpoint."""
    endpoint = request.url.path
    start = time.perf_counter()
    try:
        response = await call_next(request)
        elapsed = time.perf_counter() - start
        REQUEST_LATENCY.labels(endpoint=endpoint).observe(elapsed)
        REQUEST_COUNT.labels(endpoint=endpoint, session_id="").inc()
        return response
    except Exception as exc:
        elapsed = time.perf_counter() - start
        REQUEST_LATENCY.labels(endpoint=endpoint).observe(elapsed)
        REQUEST_ERRORS.labels(endpoint=endpoint, error_type=type(exc).__name__).inc()
        raise

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


def get_long_term_memory() -> LongTermMemoryStore:
    config_path = Path(workspace) / "config.yaml"
    try:
        config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        config = {}
    memory_config = config.get("memory", {})
    return LongTermMemoryStore(
        Path(workspace) / "memory",
        backend_name=memory_config.get("backend", "sqlite"),
    )


def load_llm_config() -> dict[str, Any]:
    config_path = Path(workspace) / "config.yaml"
    try:
        config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        config = {}
    return config.get("llm", {})


def required_env_for_provider(provider_name: str) -> str | None:
    provider = provider_name.strip().lower()
    if provider in {"google-genai", "gemini"}:
        return "GOOGLE_API_KEY"
    if provider == "openai":
        return "OPENAI_API_KEY"
    if provider == "anthropic":
        return "ANTHROPIC_API_KEY"
    return None


def ensure_llm_configured() -> None:
    llm_config = load_llm_config()
    provider = llm_config.get("provider", "google-genai")
    required_env = required_env_for_provider(provider)
    if required_env and not os.environ.get(required_env):
        raise HTTPException(
            status_code=503,
            detail=(
                f"{required_env} is not set for provider '{provider}'. "
                "Configure the provider before calling chat, stream, or task endpoints."
            ),
        )


def sse_event(event: dict[str, Any]) -> str:
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


@app.get("/v1/health")
async def health() -> dict[str, Any]:
    llm_config = load_llm_config()
    provider = llm_config.get("provider", "google-genai")
    required_env = required_env_for_provider(provider)
    return {
        "status": "ok",
        "api_version": API_VERSION,
        "workspace": workspace,
        "llm_provider": provider,
        "llm_required_env": required_env,
        "llm_configured": True if required_env is None else bool(os.environ.get(required_env)),
        "prometheus_available": PROMETHEUS_AVAILABLE,
    }


@app.get("/v1/metrics")
async def metrics():
    """Prometheus-compatible metrics endpoint."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )

@app.get("/v1/tools")
async def list_tools() -> dict[str, Any]:
    """Return the live tool manifest (PAP-aligned)."""
    manifest = ToolManifest.from_engine(get_engine())
    return json.loads(manifest.to_json())


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


@app.get("/v1/memory")
async def list_long_term_memory() -> dict[str, Any]:
    store = get_long_term_memory()
    return {
        "memory_path": str(store.path),
        "records": store.all_records(),
    }


@app.get("/v1/memory/query")
async def query_long_term_memory(q: str, session: str | None = None, limit: int = 5) -> dict[str, Any]:
    store = get_long_term_memory()
    return {
        "query": q,
        "session": session,
        "limit": limit,
        "records": store.query(q, session_id=session, limit=limit),
    }
