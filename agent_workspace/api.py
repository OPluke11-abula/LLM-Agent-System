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
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request, Depends
from fastapi.responses import JSONResponse
import dotenv

# Load workspace env
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

from agent_workspace.routes.dependencies import (
    get_workspace,
    get_account_manager,
    API_KEYS,
    verify_jwt,
    _api_key_principal,
)
from agent_workspace.core.rate_limit import TenantRequestRateLimiter, RateLimitStateUnavailable
from agent_workspace.core.runtime_config import get_runtime_feature_flags

API_VERSION = "0.1.0"


class SlidingWindowRateLimiter:
    def __init__(self, limit: int = 10, window_seconds: float = 10.0):
        self.limit = limit
        self.window_seconds = window_seconds

    async def is_rate_limited(self, tenant_id: str) -> bool:
        db_path = Path(get_workspace()) / "memory" / "financial_ledger.db"
        limiter = TenantRequestRateLimiter(db_path, limit=self.limit, window_seconds=self.window_seconds)
        return await limiter.is_rate_limited(tenant_id)

rate_limiter = SlidingWindowRateLimiter(limit=10, window_seconds=10.0)


_audit_daemon = None
_lifecycle_tasks: set[asyncio.Task[Any]] = set()


def _track_lifecycle_task(coroutine: Any) -> asyncio.Task[Any]:
    task = asyncio.create_task(coroutine)
    _lifecycle_tasks.add(task)
    task.add_done_callback(_lifecycle_tasks.discard)
    return task


async def _cancel_lifecycle_tasks() -> None:
    tasks = list(_lifecycle_tasks)
    for task in tasks:
        if not task.done():
            task.cancel()
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
    _lifecycle_tasks.clear()

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _audit_daemon
    broker = None
    flags = get_runtime_feature_flags()
    try:
        if flags.enable_stripe:
            from agent_workspace.routes.admin import start_stripe_billing_scheduler
            _track_lifecycle_task(start_stripe_billing_scheduler())

        if flags.enable_redis_swarm or flags.enable_audit_consensus:
            from agent_workspace.core.broker import get_broker
            broker = get_broker(workspace_path=get_workspace(), start=False)
            try:
                await broker.start()
            except Exception:
                from agent_workspace.core.broker import InMemorySwarmBroker
                broker = InMemorySwarmBroker()

        if flags.enable_redis_swarm:
            from agent_workspace.routes.collaboration import collab_manager
            _track_lifecycle_task(collab_manager.start_redis_listener())

        if flags.enable_audit_consensus:
            from agent_workspace.core.audit_ledger import AuditConsensusDaemon, AuditLedger
            ledger = AuditLedger(get_workspace())
            _audit_daemon = AuditConsensusDaemon(ledger, node_id=f"node-backend-{os.getpid()}")
            _track_lifecycle_task(_audit_daemon.start())

        if flags.distributed_enabled:
            from agent_workspace.core.swarm_coordinator import SwarmCoordinator

            async def swarm_heartbeat_loop():
                while True:
                    try:
                        SwarmCoordinator.check_heartbeats()
                    except Exception as e:
                        logger.error(f"Error in swarm heartbeat loop: {e}")
                    await asyncio.sleep(5.0)

            async def listen_swarm_discovery():
                async def on_discovery(msg: dict):
                    try:
                        msg_type = msg.get("type")
                        if msg_type in ("join", "heartbeat"):
                            SwarmCoordinator.register_or_update_node(
                                role=msg["role"],
                                node_id=msg["node_id"],
                                status=msg.get("status", "idle")
                            )
                        elif msg_type == "leave":
                            SwarmCoordinator.mark_node_offline(
                                node_id=msg["node_id"],
                                reason="graceful_leave"
                            )
                    except Exception as e:
                        logger.error(f"Error processing discovery message: {e}")

                await broker.subscribe("swarm:discovery", on_discovery)

            _track_lifecycle_task(swarm_heartbeat_loop())
            _track_lifecycle_task(listen_swarm_discovery())

        yield
    finally:
        if _audit_daemon:
            await _audit_daemon.stop()
            _audit_daemon = None
        if broker:
            await broker.stop()
        await _cancel_lifecycle_tasks()


app = FastAPI(
    title="FindAi Studio LAS API",
    version=API_VERSION,
    description="Non-invasive REST/SSE adapter for the LLM-Agent-System runtime.",
    lifespan=lifespan
)

# Exception handlers
from agent_workspace.core.billing import QuotaExceededError, TenantSubscriptionInactiveError, TenantRateLimitError

@app.exception_handler(QuotaExceededError)
async def quota_exceeded_handler(request: Request, exc: QuotaExceededError):
    return JSONResponse(
        status_code=402,
        content={"detail": str(exc)}
    )

@app.exception_handler(TenantSubscriptionInactiveError)
async def subscription_inactive_handler(request: Request, exc: TenantSubscriptionInactiveError):
    return JSONResponse(
        status_code=403,
        content={"detail": str(exc)}
    )

@app.exception_handler(TenantRateLimitError)
async def rate_limit_handler(request: Request, exc: TenantRateLimitError):
    return JSONResponse(
        status_code=429,
        content={"detail": str(exc)}
    )


# Middlewares
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Record request count, latency, and errors for every endpoint."""
    endpoint = request.url.path
    start = time.perf_counter()
    
    tenant_id = "default_tenant"
    try:
        x_api_key = request.headers.get("x-api-key")
        authorization = request.headers.get("authorization")
        if x_api_key and x_api_key in API_KEYS:
            tenant_id = API_KEYS[x_api_key]
        elif authorization and authorization.startswith("Bearer "):
            token = authorization[7:]
            payload = verify_jwt(token)
            if payload and "tenant_id" in payload:
                tenant_id = payload["tenant_id"]
    except Exception:
        pass

    try:
        response = await call_next(request)
        elapsed = time.perf_counter() - start
        REQUEST_LATENCY.labels(endpoint=endpoint).observe(elapsed)
        REQUEST_COUNT.labels(endpoint=endpoint, session_id="").inc()
        if PROMETHEUS_AVAILABLE:
            try:
                from observability import _get_or_create_metric
                from prometheus_client import Histogram
                api_latency = _get_or_create_metric(Histogram, "las_api_response_latency_seconds", "API response latency in seconds", ["endpoint", "tenant_id"])
                api_latency.labels(endpoint=endpoint, tenant_id=tenant_id).observe(elapsed)
            except Exception:
                pass
        return response
    except Exception as exc:
        elapsed = time.perf_counter() - start
        REQUEST_LATENCY.labels(endpoint=endpoint).observe(elapsed)
        REQUEST_ERRORS.labels(endpoint=endpoint, error_type=type(exc).__name__).inc()
        if PROMETHEUS_AVAILABLE:
            try:
                from observability import _get_or_create_metric
                from prometheus_client import Histogram
                api_latency = _get_or_create_metric(Histogram, "las_api_response_latency_seconds", "API response latency in seconds", ["endpoint", "tenant_id"])
                api_latency.labels(endpoint=endpoint, tenant_id=tenant_id).observe(elapsed)
            except Exception:
                pass
        raise

@app.middleware("http")
async def rate_limiting_middleware(request: Request, call_next):
    endpoint = request.url.path
    if endpoint in {"/v1/chat", "/v1/stream", "/v1/task"}:
        principal = None
        api_key = request.headers.get("x-api-key")
        authorization = request.headers.get("authorization")
        if api_key:
            principal = _api_key_principal(api_key)
        elif authorization and authorization.startswith("Bearer "):
            principal = verify_jwt(authorization[7:])
        tenant_id = principal.get("tenant_id", principal.get("tenant")) if principal else None
        if not isinstance(tenant_id, str) or not tenant_id:
            tenant_id = f"anonymous:{request.client.host if request.client else 'unknown'}"
        try:
            limited = await rate_limiter.is_rate_limited(tenant_id)
        except RateLimitStateUnavailable:
            return JSONResponse(status_code=503, content={"detail": "Rate-limit state unavailable."})
        if limited:
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
            return JSONResponse(status_code=503, content={"detail": "Quota state unavailable."})
            
    return await call_next(request)


if TRACING_AVAILABLE:
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        FastAPIInstrumentor.instrument_app(app)
    except ImportError:
        logger.warning("opentelemetry-instrumentation-fastapi not installed. FastAPI tracing disabled.")


# Mount modular routes
from agent_workspace.routes.swarm import router as swarm_router
from agent_workspace.routes.cross_cloud import router as cross_cloud_router
from agent_workspace.routes.audit import router as audit_router
from agent_workspace.routes.chat import router as chat_router, protected_router as chat_protected_router
from agent_workspace.routes.collaboration import router as collab_router
from agent_workspace.routes.admin import router as admin_router

app.include_router(swarm_router)
app.include_router(cross_cloud_router)
app.include_router(audit_router)
app.include_router(chat_router)
app.include_router(chat_protected_router)
app.include_router(collab_router)
app.include_router(admin_router)

# Backwards compatibility exports for testing and legacy imports
from agent_workspace.routes.dependencies import (
    API_KEYS,
    get_engine,
    generate_jwt,
    verify_jwt,
)
from agent_workspace.core.account_manager import AccountManager
from agent_workspace.core.p2p_router import SwarmP2PCrypto
from agent_workspace.core.ws_manager import crew_sync_manager
from agent_workspace.routes.collaboration import (
    collab_manager,
    dashboard_manager,
    TRUSTED_TENANTS_KEYS,
    SLACK_SIGNING_SECRET,
    LINE_CHANNEL_SECRET,
)
from agent_workspace.routes.admin import (
    STRIPE_API_KEY,
    STRIPE_WEBHOOK_SECRET,
    sync_billing_to_stripe,
)
