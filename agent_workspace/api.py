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

import collections
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response, StreamingResponse, JSONResponse
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

try:
    from core.account_manager import AccountManager
except ImportError:
    from agent_workspace.core.account_manager import AccountManager


API_VERSION = "0.1.0"


class ChatRequest(BaseModel):
    msg: str = Field(..., min_length=1)
    session: str = "default-session"
    allowed_tools: list[str] | None = None
    account_id: str | None = Field(None, description="Optional LLM account ID to route the call")


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


class AccountCreateRequest(BaseModel):
    id: str = Field(..., description="Unique identifier for the account")
    provider: str = Field(..., description="e.g. google-genai, openai, anthropic, ollama")
    model: str = Field(..., description="e.g. gemini-2.5-flash")
    api_key: str = Field(..., description="API key literal, or env:VAR_NAME")
    base_url: str | None = Field("", description="Optional custom base URL")
    token_budget: int | None = Field(-1, description="Token limit, -1 for unlimited")
    tokens_used: int | None = Field(0, description="Tokens used")
    is_active: bool | None = Field(False, description="Set as active account")


class ActiveAccountSelectRequest(BaseModel):
    account_id: str = Field(..., description="The ID of the account to activate")


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


class SlidingWindowRateLimiter:
    """Sliding-window rate limiter using in-memory collections."""
    def __init__(self, limit: int = 10, window_seconds: float = 10.0):
        self.limit = limit
        self.window_seconds = window_seconds
        self.history = collections.defaultdict(list)
        self._lock = asyncio.Lock()

    async def is_rate_limited(self, client_id: str) -> bool:
        async with self._lock:
            now = time.time()
            self.history[client_id] = [t for t in self.history[client_id] if now - t < self.window_seconds]
            if len(self.history[client_id]) >= self.limit:
                return True
            self.history[client_id].append(now)
            return False

rate_limiter = SlidingWindowRateLimiter(limit=10, window_seconds=10.0)

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

@app.middleware("http")
async def rate_limiting_middleware(request: Request, call_next):
    endpoint = request.url.path
    if endpoint in {"/v1/chat", "/v1/stream", "/v1/task"}:
        client_id = request.client.host if request.client else "unknown"
        if await rate_limiter.is_rate_limited(client_id):
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Too many requests."}
            )
            
        try:
            am = get_account_manager()
            active_acc = am.get_active_account()
            if active_acc:
                budget = active_acc.get("token_budget", -1)
                used = active_acc.get("tokens_used", 0)
                if budget != -1 and used >= budget:
                    # Attempt instant dynamic failover swapping
                    if am.swap_to_fallback() is True:
                        active_acc = am.get_active_account()
                    else:
                        return JSONResponse(
                            status_code=429,
                            content={"detail": f"Token budget exceeded for account '{active_acc['id']}' and no fallback accounts are under budget."}
                        )
        except Exception:
            pass
            
    return await call_next(request)

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


def get_account_manager() -> AccountManager:
    return AccountManager(workspace)


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
    try:
        am = get_account_manager()
        active_acc = am.get_active_account()
        if active_acc:
            budget = active_acc.get("token_budget", -1)
            used = active_acc.get("tokens_used", 0)
            if budget != -1 and used >= budget:
                # Attempt instant dynamic failover swapping
                if am.swap_to_fallback() is True:
                    active_acc = am.get_active_account()
                else:
                    raise HTTPException(
                        status_code=429,
                        detail=f"Token budget exceeded for account '{active_acc['id']}' and no fallback accounts are under budget."
                    )
            api_key = am.resolve_api_key(active_acc)
            if api_key:
                return
    except HTTPException:
        raise
    except Exception:
        pass

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
    response = await router.run_agent_loop(request.msg, allowed_tools=request.allowed_tools, account_id=request.account_id)
    return ChatResponse(session=request.session, response=response)


@app.post("/v1/stream")
async def stream(request: ChatRequest) -> StreamingResponse:
    ensure_llm_configured()

    async def event_generator():
        router = build_router(request.session)
        async for event in router.stream_agent_loop(request.msg, allowed_tools=request.allowed_tools, account_id=request.account_id):
            yield sse_event({"session": request.session, **event})

    return StreamingResponse(event_generator(), media_type="text/event-stream")


class DashboardConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[tuple[WebSocket, str]]] = {}

    async def connect(self, websocket: WebSocket, session_id: str, role: str):
        await websocket.accept()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = []
        self.active_connections[session_id].append((websocket, role))

    def disconnect(self, websocket: WebSocket, session_id: str):
        if session_id in self.active_connections:
            self.active_connections[session_id] = [
                conn for conn in self.active_connections[session_id] if conn[0] != websocket
            ]
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]

    async def broadcast(self, session_id: str, event: dict[str, Any]):
        if session_id not in self.active_connections:
            return
            
        event_type = event.get("type")
        
        for websocket, role in self.active_connections[session_id]:
            filtered_event = dict(event)
            
            # Apply CEO Strategy filters
            if role == "ceo":
                if event_type == "tool_result" and len(str(event.get("result", ""))) > 200:
                    filtered_event["result"] = str(event.get("result", ""))[:200] + "... (truncated for CEO strategy)"
            
            # Apply Auditor Billing filters and token metrics
            elif role == "auditor":
                # Preserve pre-injected event telemetry alerts
                existing_telemetry = event.get("telemetry") or {}
                if not isinstance(existing_telemetry, dict):
                    existing_telemetry = {}
                
                # Check for active warning telemetry flags in either root or nested dict
                duration = event.get("duration_ms") or existing_telemetry.get("duration_ms", 250)
                
                latency_alert = (
                    event.get("active_latency_alert")
                    or existing_telemetry.get("active_latency_alert")
                    or (duration > 2000)
                )
                cost_alert = (
                    event.get("cost_alert")
                    or existing_telemetry.get("cost_alert")
                    or False
                )
                
                # Coalesce into final structure
                filtered_event["telemetry"] = {
                    "token_used": event.get("token_used") or existing_telemetry.get("token_used", 150),
                    "duration_ms": duration,
                    "active_latency_alert": latency_alert,
                    **existing_telemetry
                }
                if cost_alert:
                    filtered_event["telemetry"]["cost_alert"] = cost_alert
            
            try:
                await websocket.send_json(filtered_event)
            except Exception:
                pass


dashboard_manager = DashboardConnectionManager()


async def run_dashboard_chat(session_id: str, msg: str):
    router = build_router(session_id)
    try:
        async for event in router.stream_agent_loop(msg):
            event["token_used"] = len(msg) * 4 + 120
            event["duration_ms"] = 450
            await dashboard_manager.broadcast(session_id, {"session": session_id, **event})
    except Exception as e:
        await dashboard_manager.broadcast(session_id, {"session": session_id, "type": "error", "content": str(e)})


@app.websocket("/v1/dashboard/{session_id}/{role}")
async def dashboard_stream(websocket: WebSocket, session_id: str, role: str):
    role = role.lower()
    if role not in {"ceo", "developer", "auditor"}:
        await websocket.accept()
        await websocket.send_json({"error": f"Invalid role: {role}. Supported: ceo, developer, auditor"})
        await websocket.close()
        return

    await dashboard_manager.connect(websocket, session_id, role)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                payload = json.loads(data)
                msg = payload.get("msg")
                if msg:
                    asyncio.create_task(run_dashboard_chat(session_id, msg))
            except Exception as e:
                await websocket.send_json({"error": "Failed to process message payload", "details": str(e)})
    except WebSocketDisconnect:
        dashboard_manager.disconnect(websocket, session_id)
        logger.info(f"Dashboard client disconnected from session {session_id} with role {role}")


@app.websocket("/v1/stream_ws")
async def stream_ws(websocket: WebSocket):
    await websocket.accept()
    try:
        # Expect the first message to be the ChatRequest payload
        data = await websocket.receive_json()
        session = data.get("session", "default-session")
        msg = data.get("msg", "")
        allowed_tools = data.get("allowed_tools")
        account_id = data.get("account_id")
        
        if not msg:
            await websocket.send_json({"error": "msg is required"})
            await websocket.close()
            return
            
        try:
            ensure_llm_configured()
        except HTTPException as e:
            await websocket.send_json({"error": e.detail})
            await websocket.close()
            return

        router = build_router(session)
        async for event in router.stream_agent_loop(msg, allowed_tools=allowed_tools, account_id=account_id):
            await websocket.send_json({"session": session, **event})
            
        await websocket.close()
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.send_json({"error": str(e)})
            await websocket.close()
        except Exception:
            pass


@app.websocket("/v1/stream")
async def websocket_stream(websocket: WebSocket):
    await websocket.accept()
    running_tasks = set()

    async def run_single_session(request_data: dict):
        try:
            try:
                request = ChatRequest(**request_data)
            except Exception as e:
                await websocket.send_json({"error": "Invalid request format", "details": str(e)})
                return
            
            try:
                ensure_llm_configured()
            except HTTPException as e:
                await websocket.send_json({"error": e.detail})
                return
                
            router = build_router(request.session)
            async for event in router.stream_agent_loop(
                request.msg,
                allowed_tools=request.allowed_tools,
                account_id=request.account_id,
            ):
                await websocket.send_json({"session": request.session, **event})
        except Exception as e:
            logger.error(f"Error in async session stream: {e}")
            try:
                await websocket.send_json({"error": str(e)})
            except Exception:
                pass

    try:
        while True:
            data = await websocket.receive_json()
            task = asyncio.create_task(run_single_session(data))
            running_tasks.add(task)
            task.add_done_callback(running_tasks.discard)
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
        for task in list(running_tasks):
            task.cancel()


async def run_background_task(record: TaskRecord, allowed_tools: list[str] | None, account_id: str | None) -> None:
    record.status = "running"
    record.started_at = utc_now()
    try:
        router = build_router(record.session)
        record.response = await router.run_agent_loop(record.msg, allowed_tools=allowed_tools, account_id=account_id)
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
    asyncio.create_task(run_background_task(record, request.allowed_tools, request.account_id))
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


@app.post("/v1/sessions/{session_id}/approve")
@app.post("/v1/session/{session_id}/approve")
async def approve_session(session_id: str) -> dict[str, Any]:
    from core.router import ACTIVE_APPROVALS
    req = ACTIVE_APPROVALS.get(session_id)
    if not req:
        raise HTTPException(status_code=404, detail=f"No pending approval for session '{session_id}'")
    future = req["future"]
    if not future.done():
        future.set_result(True)
        return {"status": "approved", "session_id": session_id}
    return {"status": "already_resolved", "session_id": session_id}


@app.post("/v1/sessions/{session_id}/reject")
@app.post("/v1/session/{session_id}/reject")
async def reject_session(session_id: str) -> dict[str, Any]:
    from core.router import ACTIVE_APPROVALS
    req = ACTIVE_APPROVALS.get(session_id)
    if not req:
        raise HTTPException(status_code=404, detail=f"No pending approval for session '{session_id}'")
    future = req["future"]
    if not future.done():
        future.set_result(False)
        return {"status": "rejected", "session_id": session_id}
    return {"status": "already_resolved", "session_id": session_id}


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


@app.get("/v1/accounts")
async def list_accounts() -> list[dict[str, Any]]:
    return get_account_manager().list_accounts()


@app.post("/v1/accounts")
async def add_update_account(req: AccountCreateRequest) -> dict[str, Any]:
    acc = req.dict()
    get_account_manager().add_account(acc)
    return {"status": "success", "account": acc}


@app.delete("/v1/accounts/{account_id}")
async def delete_account(account_id: str) -> dict[str, Any]:
    success = get_account_manager().delete_account(account_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Account not found: {account_id}")
    return {"status": "success"}


@app.post("/v1/accounts/active")
async def set_active_account(req: ActiveAccountSelectRequest) -> dict[str, Any]:
    success = get_account_manager().set_active_account(req.account_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Account not found: {req.account_id}")
    return {"status": "success"}


@app.get("/v1/accounts/active")
async def get_active_account() -> dict[str, Any]:
    acc = get_account_manager().get_active_account()
    if not acc:
        raise HTTPException(status_code=404, detail="No active account configured")
    return acc


# Decoupled Global Observer/Broadcaster Pattern
def handle_telemetry_broadcast(session_id: str, event: dict[str, Any]):
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(dashboard_manager.broadcast(session_id, event))
    except RuntimeError:
        pass

try:
    from core.discussion_room import DiscussionRoom
    from core.workflow_engine import WorkflowEngine
    DiscussionRoom.register_callback(handle_telemetry_broadcast)
    WorkflowEngine.register_callback(handle_telemetry_broadcast)
except ImportError:
    pass
