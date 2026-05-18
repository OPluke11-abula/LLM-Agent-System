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

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field
import yaml
import dotenv

workspace = os.path.dirname(os.path.abspath(__file__))
dotenv.load_dotenv(Path(workspace) / ".env")
sys.path.insert(0, workspace)

from observability import (
    configure_logging,
    configure_tracing,
    generate_latest,
    CONTENT_TYPE_LATEST,
    PROMETHEUS_AVAILABLE,
    TRACING_AVAILABLE,
    REQUEST_COUNT,
    REQUEST_LATENCY,
    REQUEST_ERRORS,
)

configure_logging(json_output=True)
configure_tracing("las.api")
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


class ConfigUpdateRequest(BaseModel):
    provider: str | None = Field(None, description="e.g. google-genai, openai, anthropic, ollama")
    model: str | None = Field(None, description="e.g. gemini-2.5-flash")
    api_key: str | None = Field(None, description="API Key. Will be written to .env securely.")
    base_url: str | None = Field(None, description="Optional Base URL for Ollama or custom endpoints.")


class PreferenceRequest(BaseModel):
    session: str = Field(..., description="The session ID to attach this preference to")
    preference: str = Field(..., description="The preference text")
    confidence: float = 1.0
    expires_at: str | None = None


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

if TRACING_AVAILABLE:
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        FastAPIInstrumentor.instrument_app(app)
    except ImportError:
        logger.warning("opentelemetry-instrumentation-fastapi not installed. FastAPI tracing disabled.")

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


@app.websocket("/v1/stream")
async def websocket_stream(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            try:
                request = ChatRequest(**data)
            except Exception as e:
                await websocket.send_json({"error": "Invalid request format", "details": str(e)})
                continue
            
            try:
                ensure_llm_configured()
            except HTTPException as e:
                await websocket.send_json({"error": e.detail})
                continue
                
            router = build_router(request.session)
            async for event in router.stream_agent_loop(request.msg, allowed_tools=request.allowed_tools):
                await websocket.send_json({"session": request.session, **event})
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")


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
async def query_long_term_memory(q: str, session: str | None = None, limit: int = 5, domain: str | None = None) -> dict[str, Any]:
    store = get_long_term_memory()
    return {
        "query": q,
        "session": session,
        "limit": limit,
        "domain": domain,
        "records": store.query(q, session_id=session, limit=limit, domain=domain),
    }


@app.post("/v1/memory/preference")
async def add_preference(req: PreferenceRequest) -> dict[str, Any]:
    store = get_long_term_memory()
    record = store.add_preference(
        session_id=req.session,
        preference_text=req.preference,
        confidence=req.confidence,
        expires_at=req.expires_at,
    )
    return {"status": "success", "record": asdict(record)}


@app.delete("/v1/memory/{session_id}/{key}")
async def delete_memory(session_id: str, key: str) -> dict[str, Any]:
    store = get_long_term_memory()
    success = store.delete_record(session_id, key)
    if not success:
        raise HTTPException(status_code=404, detail="Memory record not found")
    return {"status": "success", "session_id": session_id, "key": key}


@app.post("/v1/memory/prune")
async def prune_memory() -> dict[str, Any]:
    store = get_long_term_memory()
    count = store.prune_expired()
    return {"status": "success", "deleted_count": count}


@app.get("/v1/config")
async def get_config() -> dict[str, Any]:
    config_path = Path(workspace) / "config.yaml"
    try:
        config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        config = {}
    
    llm_config = config.get("llm", {})
    provider = llm_config.get("provider", "")
    
    # Check if API key is set in environment variables
    api_key_set = False
    if provider == "google-genai" and os.environ.get("GOOGLE_API_KEY"):
        api_key_set = True
    elif provider == "openai" and os.environ.get("OPENAI_API_KEY"):
        api_key_set = True
    elif provider == "anthropic" and os.environ.get("ANTHROPIC_API_KEY"):
        api_key_set = True
        
    return {
        "provider": provider,
        "model": llm_config.get("model", ""),
        "base_url": llm_config.get("base_url", ""),
        "api_key_set": api_key_set
    }


@app.put("/v1/config")
async def update_config(req: ConfigUpdateRequest) -> dict[str, Any]:
    config_path = Path(workspace) / "config.yaml"
    try:
        config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        config = {}
        
    if "llm" not in config:
        config["llm"] = {}
        
    if req.provider is not None:
        config["llm"]["provider"] = req.provider
    if req.model is not None:
        config["llm"]["model"] = req.model
    if req.base_url is not None:
        if req.base_url.strip() == "":
            config["llm"].pop("base_url", None)
        else:
            config["llm"]["base_url"] = req.base_url
            
    # Save config.yaml
    config_path.write_text(yaml.dump(config, sort_keys=False, allow_unicode=True), encoding="utf-8")
    
    # Handle API Key
    if req.api_key is not None and req.api_key.strip() != "":
        env_path = Path(workspace) / ".env"
        # Determine the key name
        key_name = ""
        provider = req.provider or config["llm"].get("provider", "")
        if provider == "google-genai":
            key_name = "GOOGLE_API_KEY"
        elif provider == "openai":
            key_name = "OPENAI_API_KEY"
        elif provider == "anthropic":
            key_name = "ANTHROPIC_API_KEY"
            
        if key_name:
            # Update .env
            env_vars = {}
            if env_path.is_file():
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            env_vars[k.strip()] = v.strip()
            
            env_vars[key_name] = req.api_key.strip()
            
            with open(env_path, "w", encoding="utf-8") as f:
                for k, v in env_vars.items():
                    f.write(f"{k}={v}\n")
            
            # Reload dotenv
            dotenv.load_dotenv(env_path, override=True)
            
    # Reset engine cache so next call reloads config
    global _engine
    _engine = None
    
    return {"status": "success", "message": "Configuration updated successfully."}
