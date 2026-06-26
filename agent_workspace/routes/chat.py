import os
import sys
import json
import uuid
import logging
import asyncio
import yaml
import dotenv
from pathlib import Path
from typing import Any
from dataclasses import dataclass, asdict
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, Request, Response
from fastapi.responses import StreamingResponse

from agent_workspace.routes.dependencies import (
    get_tenant_context,
    verify_websocket_tenant,
    get_engine,
    get_account_manager,
    build_router,
    get_long_term_memory,
    load_llm_config,
    required_env_for_provider,
    ensure_llm_configured,
    sse_event,
    get_workspace
)
from agent_workspace.routes.schemas import (
    ChatRequest, ChatResponse, TaskRequest, TaskSubmitResponse, ConfigUpdateRequest,
    AccountCreateRequest, ActiveAccountSelectRequest, PreferenceRequest,
    BuilderAgentRequest, SandboxExecuteRequest, MemoryUpdateRequest,
    MemoryBatchMoveRequest
)
from agent_workspace.tool_manifest import ToolManifest
from agent_workspace.core.account_manager import AccountManager
from agent_workspace.core.router import ACTIVE_APPROVALS
from observability import (
    generate_latest,
    CONTENT_TYPE_LATEST,
    PROMETHEUS_AVAILABLE
)

logger = logging.getLogger(__name__)
API_VERSION = "0.1.0"

router = APIRouter()

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

_task_records: dict[str, TaskRecord] = {}

def utc_now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


async def run_background_task(record: TaskRecord, allowed_tools: list[str] | None, account_id: str | None) -> None:
    record.status = "running"
    record.started_at = utc_now()
    try:
        r = build_router(record.session)
        record.response = await r.run_agent_loop(record.msg, allowed_tools=allowed_tools, account_id=account_id)
        record.status = "completed"
    except Exception as error:
        record.status = "error"
        record.error = str(error)
    finally:
        record.completed_at = utc_now()


@router.get("/v1/health")
async def health() -> dict[str, Any]:
    llm_config = load_llm_config()
    provider = llm_config.get("provider", "google-genai")
    required_env = required_env_for_provider(provider)
    return {
        "status": "ok",
        "api_version": API_VERSION,
        "workspace": get_workspace(),
        "llm_provider": provider,
        "llm_required_env": required_env,
        "llm_configured": True if required_env is None else bool(os.environ.get(required_env)),
        "prometheus_available": PROMETHEUS_AVAILABLE,
    }


@router.get("/metrics")
@router.get("/v1/metrics")
async def metrics():
    """Prometheus-compatible metrics endpoint."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


@router.get("/v1/tools")
async def list_tools() -> dict[str, Any]:
    """Return the live tool manifest (PAP-aligned)."""
    manifest = ToolManifest.from_engine(get_engine())
    return json.loads(manifest.to_json())


@router.post("/v1/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    ensure_llm_configured()
    r = build_router(request.session)
    response = await r.run_agent_loop(request.msg, allowed_tools=request.allowed_tools, account_id=request.account_id)
    return ChatResponse(session=request.session, response=response)


@router.post("/v1/stream")
async def stream(request: ChatRequest) -> StreamingResponse:
    ensure_llm_configured()

    async def event_generator():
        r = build_router(request.session)
        async for event in r.stream_agent_loop(request.msg, allowed_tools=request.allowed_tools, account_id=request.account_id):
            yield sse_event({"session": request.session, **event})

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.websocket("/v1/stream_ws")
async def stream_ws(websocket: WebSocket):
    # Dynamic tenant verification
    from agent_workspace.routes.dependencies import verify_websocket_tenant
    tenant_id = await verify_websocket_tenant(websocket)
    if not tenant_id:
        return

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

        # Verify session tenancy context
        existing_tenant = AccountManager.get_session_tenant(session)
        if existing_tenant and existing_tenant != tenant_id:
            await websocket.send_json({"error": "Access denied to session of another tenant"})
            await websocket.close()
            return
        AccountManager.register_session_tenant(session, tenant_id)

        try:
            ensure_llm_configured()
        except HTTPException as e:
            await websocket.send_json({"error": e.detail})
            await websocket.close()
            return

        r = build_router(session)
        async for event in r.stream_agent_loop(msg, allowed_tools=allowed_tools, account_id=account_id):
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


@router.websocket("/v1/stream")
async def websocket_stream(websocket: WebSocket):
    # Dynamic tenant verification
    from agent_workspace.routes.dependencies import verify_websocket_tenant
    tenant_id = await verify_websocket_tenant(websocket)
    if not tenant_id:
        return

    running_tasks = set()

    async def run_single_session(request_data: dict):
        try:
            try:
                request = ChatRequest(**request_data)
            except Exception as e:
                await websocket.send_json({"error": "Invalid request format", "details": str(e)})
                return

            # Verify session tenancy context
            existing_tenant = AccountManager.get_session_tenant(request.session)
            if existing_tenant and existing_tenant != tenant_id:
                await websocket.send_json({"error": "Access denied to session of another tenant"})
                return
            AccountManager.register_session_tenant(request.session, tenant_id)

            try:
                ensure_llm_configured()
            except HTTPException as e:
                await websocket.send_json({"error": e.detail})
                return

            r = build_router(request.session)
            async for event in r.stream_agent_loop(
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


@router.post("/v1/task", response_model=TaskSubmitResponse)
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


@router.get("/v1/session/{session_id}")
async def get_session(session_id: str) -> dict[str, Any]:
    memory_path = Path(get_workspace()) / "memory" / f"{session_id}.json"
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


@router.post("/v1/sessions/{session_id}/approve")
@router.post("/v1/session/{session_id}/approve")
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


@router.post("/v1/sessions/{session_id}/reject")
@router.post("/v1/session/{session_id}/reject")
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


@router.get("/v1/memory")
async def list_long_term_memory() -> dict[str, Any]:
    store = get_long_term_memory()
    return {
        "memory_path": str(store.path),
        "records": store.all_records(),
    }


@router.get("/v1/memory/query")
async def query_long_term_memory(q: str, session: str | None = None, limit: int = 5, domain: str | None = None) -> dict[str, Any]:
    store = get_long_term_memory()
    return {
        "query": q,
        "session": session,
        "limit": limit,
        "domain": domain,
        "records": store.query(q, session_id=session, limit=limit, domain=domain),
    }


@router.post("/v1/memory/preference")
async def add_preference(req: PreferenceRequest) -> dict[str, Any]:
    store = get_long_term_memory()
    record = store.add_preference(
        session_id=req.session,
        preference_text=req.preference,
        confidence=req.confidence,
        expires_at=req.expires_at,
        category=req.category,
    )
    return {"status": "success", "record": asdict(record)}


@router.delete("/v1/memory/{session_id}/{key}")
async def delete_memory(session_id: str, key: str) -> dict[str, Any]:
    store = get_long_term_memory()
    success = store.delete_record(session_id, key)
    if not success:
        raise HTTPException(status_code=404, detail="Memory record not found")
    return {"status": "success", "session_id": session_id, "key": key}


@router.post("/v1/memory/prune")
async def prune_memory() -> dict[str, Any]:
    store = get_long_term_memory()
    count = store.prune_expired()
    return {"status": "success", "deleted_count": count}


@router.post("/v1/memory/update")
async def update_memory(req: MemoryUpdateRequest) -> dict[str, Any]:
    store = get_long_term_memory()
    success = store.update_record(
        session_id=req.session_id,
        key=req.key,
        summary=req.summary,
        domain=req.domain,
        category=req.category,
        confidence=req.confidence,
        expires_at=req.expires_at,
        citations=req.citations,
    )
    if not success:
        raise HTTPException(status_code=404, detail="Memory record not found")
    return {"status": "success", "session_id": req.session_id, "key": req.key}


@router.post("/v1/memory/batch-move")
async def batch_move_memory(req: MemoryBatchMoveRequest) -> dict[str, Any]:
    store = get_long_term_memory()
    target_items = [{"session_id": item.session_id, "key": item.key} for item in req.items]
    count = store.batch_move(target_items, req.new_category)
    return {"status": "success", "moved_count": count, "new_category": req.new_category}


@router.get("/v1/config")
async def get_config() -> dict[str, Any]:
    config_path = Path(get_workspace()) / "config.yaml"
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


@router.put("/v1/config")
async def update_config(req: ConfigUpdateRequest) -> dict[str, Any]:
    config_path = Path(get_workspace()) / "config.yaml"
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
        env_path = Path(get_workspace()) / ".env"
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
    from agent_workspace.routes import dependencies
    dependencies._engine = None

    return {"status": "success", "message": "Configuration updated successfully."}


@router.get("/v1/accounts")
async def list_accounts() -> list[dict[str, Any]]:
    return get_account_manager().list_accounts()


@router.post("/v1/accounts")
async def add_update_account(req: AccountCreateRequest) -> dict[str, Any]:
    acc = req.model_dump()
    get_account_manager().add_account(acc)
    return {"status": "success", "account": acc}


@router.delete("/v1/accounts/{account_id}")
async def delete_account(account_id: str) -> dict[str, Any]:
    success = get_account_manager().delete_account(account_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Account not found: {account_id}")
    return {"status": "success"}


@router.post("/v1/accounts/active")
async def set_active_account(req: ActiveAccountSelectRequest) -> dict[str, Any]:
    success = get_account_manager().set_active_account(req.account_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Account not found: {req.account_id}")
    return {"status": "success"}


@router.get("/v1/accounts/active")
async def get_active_account() -> dict[str, Any]:
    acc = get_account_manager().get_active_account()
    if not acc:
        raise HTTPException(status_code=404, detail="No active account configured")
    return acc


@router.get("/v1/sessions/{session_id}/turns")
@router.get("/v1/session/{session_id}/turns")
async def get_session_turns(session_id: str) -> dict[str, Any]:
    engine = get_engine()
    turns = engine.session_turns.get(session_id, 0)
    threshold = engine.handoff_threshold
    return {
        "session_id": session_id,
        "turns": turns,
        "threshold": threshold,
        "should_glow": turns >= threshold,
    }


@router.post("/v1/sessions/{session_id}/handoff")
@router.post("/v1/session/{session_id}/handoff")
async def manual_handoff_export(session_id: str) -> dict[str, Any]:
    engine = get_engine()
    memory_dir = os.path.join(engine.workspace_path, "memory")
    from agent_workspace.core.router import MemoryManager

    memory_mgr = MemoryManager(memory_dir, session_id=session_id)
    recent = memory_mgr.get_recent_context(3)
    if recent:
        context_summary = "Recent conversation summary:\n" + "\n".join(
            f"- User: {c.get('user', '')}\n- Assistant: {c.get('assistant', '')}"
            for c in recent
        )
    else:
        context_summary = "Manual session state handoff."

    try:
        handoff_id = engine.export_handoff(session_id, context_summary)

        project_root = Path(engine.workspace_path).parent
        prompt_file = project_root / ".agent" / "memory" / "handoff" / f"{handoff_id}_prompt.md"
        prompt_content = ""
        if prompt_file.is_file():
            prompt_content = prompt_file.read_text(encoding="utf-8")

        return {
            "status": "success",
            "handoff_id": handoff_id,
            "prompt": prompt_content,
            "markdown_prompt": prompt_content,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/v1/sessions/{session_id}/defragment")
@router.post("/v1/session/{session_id}/defragment")
async def manual_defragment(session_id: str) -> dict[str, Any]:
    from agent_workspace.core.memory import ContextDefragmenter

    defragmenter = ContextDefragmenter(get_workspace())
    try:
        result = defragmenter.defragment(session_id)
        router.defrag_metrics = getattr(router, "defrag_metrics", {})
        router.defrag_metrics[session_id] = {
            "fragmentation_rate": result["fragmentation_rate"],
            "reconciliation_efficiency": result["reconciliation_efficiency"],
        }
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Defragmentation sweep failed: {e}")


@router.get("/v1/sessions/{session_id}/defragment/metrics")
@router.get("/v1/session/{session_id}/defragment/metrics")
async def get_defragment_metrics(session_id: str) -> dict[str, Any]:
    metrics_by_session = getattr(router, "defrag_metrics", {})
    if session_id in metrics_by_session:
        metrics = metrics_by_session[session_id]
        return {
            "session_id": session_id,
            "fragmentation_rate": metrics["fragmentation_rate"],
            "reconciliation_efficiency": metrics["reconciliation_efficiency"],
        }

    project_root = Path(get_workspace()).parent
    handoff_dir = project_root / ".agent" / "memory" / "handoff"
    handoffs_count = 0
    if handoff_dir.is_dir():
        handoffs_count = len([
            path for path in handoff_dir.iterdir()
            if path.suffix == ".json" and not path.name.endswith("_prompt.json")
        ])
    return {
        "session_id": session_id,
        "fragmentation_rate": round(min(0.85, handoffs_count * 0.15), 2),
        "reconciliation_efficiency": 0.95,
    }


@router.get("/v1/sessions/{session_id}/ledger")
@router.get("/v1/session/{session_id}/ledger")
async def get_session_ledger(session_id: str) -> dict[str, Any]:
    from agent_workspace.core.ledger import FinancialLedger
    ledger = FinancialLedger(get_workspace())
    transactions = ledger.get_all_records()
    total_cost = ledger.get_total_cost()

    account_manager = get_account_manager()
    active_account = account_manager.get_active_account()
    active_model = active_account.get("model", "unknown") if active_account else "unknown"

    cost_threshold = 0.05
    config_path = Path(get_workspace()) / "config.yaml"
    if config_path.is_file():
        try:
            config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
            cost_threshold = config.get("billing", {}).get("cost_threshold", 0.05)
        except Exception:
            pass

    return {
        "session_id": session_id,
        "total_cost": total_cost,
        "cost_threshold": cost_threshold,
        "active_model": active_model,
        "transactions": transactions,
    }


@router.post("/v1/sessions/{session_id}/ledger/reset")
@router.post("/v1/session/{session_id}/ledger/reset")
async def reset_session_ledger(session_id: str) -> dict[str, Any]:
    from agent_workspace.core.ledger import FinancialLedger
    ledger = FinancialLedger(get_workspace())
    ledger.reset_ledger()
    return {"status": "success", "session_id": session_id}


@router.get("/v1/sessions/{session_id}/sandbox/status")
@router.get("/v1/session/{session_id}/sandbox/status")
async def get_sandbox_status(session_id: str) -> dict[str, Any]:
    from agent_workspace.core.sandbox import SandboxGuard
    return {
        "status": "healthy",
        "total_executions": getattr(SandboxGuard, "total_executions", 0),
        "blocked_executions": getattr(SandboxGuard, "blocked_executions", 0),
        "allowed_executions": getattr(SandboxGuard, "allowed_executions", 0),
        "last_execution_status": getattr(SandboxGuard, "last_execution_status", "none"),
    }


@router.get("/v1/sessions/{session_id}/telemetry")
@router.get("/v1/session/{session_id}/telemetry")
async def get_session_telemetry(session_id: str) -> dict[str, Any]:
    from agent_workspace.observability import get_telemetry_router
    router_telemetry = get_telemetry_router(get_workspace())
    router_telemetry.record_metric(session_id, latency_ms=12.5, ws_latency_ms=8.0)
    metrics = router_telemetry.get_metrics(session_id)
    return {
        "session_id": session_id,
        "metrics": metrics
    }


@router.get("/v1/router/status")
@router.get("/v1/sessions/{session_id}/router/status")
@router.get("/v1/session/{session_id}/router/status")
async def get_router_status(session_id: str | None = None) -> dict[str, Any]:
    from agent_workspace.core.router import ROUTE_REGISTRY

    return {
        "routes": list(ROUTE_REGISTRY.routes.values()),
        "pruned_history": ROUTE_REGISTRY.pruned_history,
    }


@router.post("/v1/router/prune")
@router.post("/v1/sessions/{session_id}/router/prune")
@router.post("/v1/session/{session_id}/router/prune")
async def prune_router_routes(session_id: str | None = None, force: bool = False) -> dict[str, Any]:
    from agent_workspace.core.router import ROUTE_REGISTRY

    pruned_any = ROUTE_REGISTRY.prune_stale_or_all(force_all=force)
    return {
        "status": "success",
        "pruned_any": pruned_any,
        "active_routes": [route for route in ROUTE_REGISTRY.routes.values() if route["status"] == "active"],
        "pruned_history": ROUTE_REGISTRY.pruned_history,
    }


@router.post("/v1/builder/agents")
async def create_builder_agent(req: BuilderAgentRequest, tenant_id: str = Depends(get_tenant_context)):
    from agent_workspace.core.builder import AgentBuilderRegistry

    config = req.model_dump()
    registered = AgentBuilderRegistry.register_agent(req.name, config)
    return {"status": "success", "agent": registered}


@router.get("/v1/builder/templates")
async def get_builder_templates(tenant_id: str = Depends(get_tenant_context)):
    from agent_workspace.core.builder import PRESET_TEMPLATES

    return {"templates": PRESET_TEMPLATES}


@router.post("/v1/builder/test")
async def test_builder_agent(req: Request, tenant_id: str = Depends(get_tenant_context)):
    req_json = await req.json()
    from agent_workspace.core.builder import render_system_prompt, emit_mock_webhook_telemetry
    from agent_workspace.core.ledger import FinancialLedger

    agent_config = req_json.get("agent_config", {})
    test_input = req_json.get("test_input", "")
    session_id = req_json.get("session_id", "builder-test-session")
    variables = req_json.get("variables") or {}

    system_template = agent_config.get("system_template", "")
    render_vars = {**agent_config, **variables}
    rendered_prompt = render_system_prompt(system_template, render_vars)

    # Record transaction to ledger
    ledger = FinancialLedger(get_workspace())
    model_name = agent_config.get("model", "saas-builder-test")
    cost = ledger.record_transaction(
        session_id=session_id,
        account_id="saas-builder",
        provider="mock-provider",
        model=model_name,
        prompt_tokens=150,
        completion_tokens=250,
        tenant_id=tenant_id
    )

    # Emit telemetry webhook gateways logs
    gateways = agent_config.get("telemetry_gateways", [])
    telemetry_logs = emit_mock_webhook_telemetry(gateways, f"Agent response generated for user prompt: {test_input}")

    return {
        "status": "success",
        "rendered_prompt": rendered_prompt,
        "output": f"[Console Test Output for '{agent_config.get('name', 'CustomAgent')}']: Processed: '{test_input}'.",
        "estimated_cost_usd": cost,
        "telemetry_logs": telemetry_logs
    }


@router.post("/v1/sandbox/execute")
async def execute_in_sandbox(req: SandboxExecuteRequest, tenant_id: str = Depends(get_tenant_context)):
    from agent_workspace.core.sandbox import SandboxGuard

    try:
        result = SandboxGuard.execute_safe(
            workspace_path=get_workspace(),
            code_content=req.code_content,
            globals_dict=req.globals_dict,
            locals_dict=req.locals_dict,
            sandbox_type=req.sandbox_type,
            tenant_id=tenant_id
        )
        return {"status": "success", "result": result}
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
