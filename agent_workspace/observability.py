"""Observability utilities for LAS.

This module provides two capabilities that are commonly needed together:

1. **Structured JSON Logging** — a drop-in ``logging.Formatter`` that emits
   every log record as a single-line JSON object.  Fields include
   ``timestamp``, ``level``, ``logger``, ``message``, and any *extra* keys
   the caller passes (``session_id``, ``tool_name``, ``latency_ms``, …).

2. **Prometheus-compatible Metrics** — lightweight counters, histograms, and
   gauges using the ``prometheus_client`` library (soft dependency).  When the
   library is not installed the metrics helpers become harmless no-ops so the
   rest of the codebase never needs conditional imports.

Architecture note:
    ``configure_logging()`` should be called **once** at process startup
    (in ``run.py``, ``api.py``, or ``topology_stream.py``).  Individual
    modules keep using ``logging.getLogger(__name__)`` — no changes needed.
"""

from __future__ import annotations

import json
import logging
import sys
import time
from datetime import datetime, timezone
from typing import Any


# =========================================================================
# 1.  Structured JSON Formatter
# =========================================================================

class JSONFormatter(logging.Formatter):
    """Emit each log record as a single-line JSON object.

    Extra fields can be injected per-record via the standard *extra* kwarg::

        logger.info("tool ok", extra={"tool_name": "calc", "latency_ms": 42})

    The formatter will surface them as top-level keys in the output.
    """

    # Keys that already live on every LogRecord — we never surface these as
    # "extra" because they are either internal or already mapped.
    _BUILTIN_KEYS = frozenset(logging.LogRecord("", 0, "", 0, "", (), None).__dict__)

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Inject OpenTelemetry trace IDs if available
        if TRACING_AVAILABLE:
            ctx = trace.get_current_span().get_span_context()
            if ctx.is_valid:
                payload["trace_id"] = trace.format_trace_id(ctx.trace_id)
                payload["span_id"] = trace.format_span_id(ctx.span_id)

        # Surface caller-supplied *extra* fields.
        for key, value in record.__dict__.items():
            if key not in self._BUILTIN_KEYS and key not in payload:
                try:
                    json.dumps(value)  # guard: only JSON-serialisable values
                    payload[key] = value
                except (TypeError, ValueError):
                    payload[key] = repr(value)

        if record.exc_info and record.exc_info[1] is not None:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False)


def configure_logging(
    *,
    level: int | str = logging.INFO,
    json_output: bool = True,
) -> None:
    """Configure the root logger for the LAS process.

    Parameters
    ----------
    level:
        Minimum log level (default ``INFO``).
    json_output:
        When *True* (default), attach :class:`JSONFormatter` to *stderr*.
        When *False*, fall back to the default human-readable format — useful
        during local development.
    """
    root = logging.getLogger()
    root.setLevel(level)

    # Remove pre-existing handlers to avoid duplicated output when
    # configure_logging is called more than once (e.g. tests).
    for handler in root.handlers[:]:
        root.removeHandler(handler)

    handler = logging.StreamHandler(sys.stderr)
    if json_output:
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )
    root.addHandler(handler)


# =========================================================================
# 2.  Prometheus Metrics (soft dependency)
# =========================================================================

try:
    from prometheus_client import (
        Counter,
        Histogram,
        Gauge,
        generate_latest,
        CONTENT_TYPE_LATEST,
    )

    PROMETHEUS_AVAILABLE = True
except ImportError:  # pragma: no cover — library not installed
    PROMETHEUS_AVAILABLE = False

    # Stub classes so the rest of the codebase can reference metrics without
    # guarding every call.  Each stub silently discards all observations.
    class _NoOpMetric:
        def __init__(self, *a: Any, **kw: Any) -> None: ...
        def inc(self, *a: Any, **kw: Any) -> None: ...
        def dec(self, *a: Any, **kw: Any) -> None: ...
        def set(self, *a: Any, **kw: Any) -> None: ...
        def observe(self, *a: Any, **kw: Any) -> None: ...
        def labels(self, *a: Any, **kw: Any) -> "_NoOpMetric":
            return self
        def time(self) -> "_NoOpTimer":
            return _NoOpTimer()

    class _NoOpTimer:
        def __enter__(self) -> "_NoOpTimer":
            return self
        def __exit__(self, *a: Any) -> None: ...

    Counter = Histogram = Gauge = _NoOpMetric  # type: ignore[misc,assignment]

    def generate_latest() -> bytes:  # type: ignore[misc]
        return b""

    CONTENT_TYPE_LATEST = "text/plain; charset=utf-8"


# ---------------------------------------------------------------------------
#  Pre-defined metrics — import and use from anywhere in the codebase.
# ---------------------------------------------------------------------------

def _get_or_create_metric(metric_cls: Any, name: str, documentation: str, labelnames: list[str] | None = None, **kwargs: Any) -> Any:
    """Safe helper to define or retrieve a Prometheus metric without duplication errors."""
    if not PROMETHEUS_AVAILABLE:
        return metric_cls(name, documentation, labelnames or [], **kwargs)
    
    from prometheus_client import REGISTRY
    if name in REGISTRY._names_to_collectors:
        return REGISTRY._names_to_collectors[name]
    
    try:
        return metric_cls(name, documentation, labelnames or [], **kwargs)
    except ValueError:
        return REGISTRY._names_to_collectors.get(name, metric_cls(name, documentation, labelnames or [], **kwargs))


# ---------------------------------------------------------------------------
#  Pre-defined metrics — import and use from anywhere in the codebase.
# ---------------------------------------------------------------------------

REQUEST_COUNT = _get_or_create_metric(
    Counter,
    "las_request_total",
    "Total number of agent requests",
    ["endpoint", "session_id"],
)

REQUEST_LATENCY = _get_or_create_metric(
    Histogram,
    "las_request_latency_seconds",
    "Latency of agent requests in seconds",
    ["endpoint"],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0),
)

REQUEST_ERRORS = _get_or_create_metric(
    Counter,
    "las_request_errors_total",
    "Total number of agent request errors",
    ["endpoint", "error_type"],
)

TOOL_CALL_COUNT = _get_or_create_metric(
    Counter,
    "las_tool_call_total",
    "Total number of tool calls",
    ["tool_name", "status"],
)

TOOL_CALL_LATENCY = _get_or_create_metric(
    Histogram,
    "las_tool_call_latency_seconds",
    "Latency of individual tool calls",
    ["tool_name"],
)

LLM_CALL_COUNT = _get_or_create_metric(
    Counter,
    "las_llm_call_total",
    "Total number of LLM provider calls",
    ["provider", "status"],
)

LLM_CALL_LATENCY = _get_or_create_metric(
    Histogram,
    "las_llm_call_latency_seconds",
    "Latency of LLM provider calls",
    ["provider"],
)

ACTIVE_SESSIONS = _get_or_create_metric(
    Gauge,
    "las_active_sessions",
    "Number of currently active agent sessions",
)


# ---------------------------------------------------------------------------
#  Timer context manager (convenient for manual instrumentation)
# ---------------------------------------------------------------------------

class Timer:
    """Measure elapsed wall-clock time and optionally record to a histogram.

    Usage::

        with Timer(LLM_CALL_LATENCY, labels={"provider": "openai"}) as t:
            result = await provider.generate_content(...)
        logger.info("done", extra={"latency_ms": t.elapsed_ms})
    """

    def __init__(
        self,
        histogram: Any = None,
        labels: dict[str, str] | None = None,
    ) -> None:
        self._histogram = histogram
        self._labels = labels or {}
        self.elapsed: float = 0.0

    @property
    def elapsed_ms(self) -> float:
        return round(self.elapsed * 1000, 2)

    def __enter__(self) -> "Timer":
        self._start = time.perf_counter()
        return self

    def __exit__(self, *exc: Any) -> None:
        self.elapsed = time.perf_counter() - self._start
        if self._histogram is not None:
            self._histogram.labels(**self._labels).observe(self.elapsed)


# =========================================================================
# 3.  OpenTelemetry Tracing (soft dependency)
# =========================================================================

try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

    TRACING_AVAILABLE = True

    def configure_tracing(service_name: str = "las") -> None:
        """Initialize OpenTelemetry tracer provider.
        
        Currently configures a ConsoleSpanExporter for local debugging.
        If OTEL_EXPORTER_OTLP_ENDPOINT is set, you could easily swap in an OTLP exporter here.
        """
        # Note: In a production setup, we'd use Resource(attributes={"service.name": service_name})
        provider = TracerProvider()
        
        # We output to console by default so developers can see the trace tree
        processor = BatchSpanProcessor(ConsoleSpanExporter())
        provider.add_span_processor(processor)
        
        trace.set_tracer_provider(provider)

    # Get a tracer for manual span creation
    tracer = trace.get_tracer("las.core")

except ImportError:  # pragma: no cover
    TRACING_AVAILABLE = False

    def configure_tracing(service_name: str = "las") -> None: ...

    class _NoOpSpanContext:
        is_valid = False

    class _NoOpSpan:
        def get_span_context(self) -> _NoOpSpanContext:
            return _NoOpSpanContext()
        def set_attribute(self, *a: Any, **kw: Any) -> None: ...
        def record_exception(self, *a: Any, **kw: Any) -> None: ...
        def set_status(self, *a: Any, **kw: Any) -> None: ...
        def __enter__(self) -> "_NoOpSpan": return self
        def __exit__(self, *a: Any) -> None: ...

    class _NoOpTracer:
        def start_as_current_span(self, *a: Any, **kw: Any) -> _NoOpSpan:
            return _NoOpSpan()

    class _NoOpTraceAPI:
        def get_current_span(self) -> _NoOpSpan:
            return _NoOpSpan()
        def get_tracer(self, *a: Any, **kw: Any) -> _NoOpTracer:
            return _NoOpTracer()

    trace = _NoOpTraceAPI()  # type: ignore[assignment]
    tracer = trace.get_tracer("las.core")


# =========================================================================
# 4.  Dynamic Event-Loop Bottleneck Profiler & Self-Tuning Executor
# =========================================================================

import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor

_ACTIVE_PROFILER: EventLoopBottleneckProfiler | None = None


def get_active_profiler() -> EventLoopBottleneckProfiler | None:
    """Retrieve the currently active bottleneck profiler singleton."""
    return _ACTIVE_PROFILER


class ProfilingThreadPoolExecutor(ThreadPoolExecutor):
    """ThreadPoolExecutor subclass that intercepts tasks to profile blocking call durations."""

    def __init__(self, profiler: EventLoopBottleneckProfiler, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.profiler = profiler

    def submit(self, fn: Any, *args: Any, **kwargs: Any) -> Any:
        def wrapped(*a: Any, **kw: Any) -> Any:
            start = time.perf_counter()
            try:
                return fn(*a, **kw)
            finally:
                duration = time.perf_counter() - start
                if duration > self.profiler.stutter_threshold:
                    self.profiler.record_sync_call(fn, duration, args, kwargs)
        return super().submit(wrapped, *args, **kwargs)


class EventLoopBottleneckProfiler:
    """Non-intrusive event-loop stutter profiling and self-tuning execution throttle."""

    def __init__(self, check_interval_ms: float = 10, stutter_threshold_ms: float = 50) -> None:
        self.check_interval = check_interval_ms / 1000.0
        self.stutter_threshold = stutter_threshold_ms / 1000.0
        self.stutters: list[dict[str, Any]] = []
        self.sync_calls: list[dict[str, Any]] = []
        self.executor: ProfilingThreadPoolExecutor | None = None
        self.is_running = False
        self._monitor_task: asyncio.Task[None] | None = None
        self._engines: list[Any] = []

    def start(self, loop: asyncio.AbstractEventLoop | None = None) -> None:
        """Start the background event-loop monitor task and initialize profiling executor."""
        if self.is_running:
            return
        if loop is None:
            loop = asyncio.get_running_loop()
        self.is_running = True
        self.executor = ProfilingThreadPoolExecutor(self, max_workers=4)
        self._monitor_task = loop.create_task(self._monitor_loop())
        global _ACTIVE_PROFILER
        _ACTIVE_PROFILER = self
        logging.getLogger(__name__).info("EventLoopBottleneckProfiler started successfully.")

    def stop(self) -> None:
        """Stop background profiling and cleanup executor."""
        self.is_running = False
        if self._monitor_task:
            self._monitor_task.cancel()
        if self.executor:
            self.executor.shutdown(wait=False)
        global _ACTIVE_PROFILER
        if _ACTIVE_PROFILER is self:
            _ACTIVE_PROFILER = None
        logging.getLogger(__name__).info("EventLoopBottleneckProfiler stopped successfully.")

    def register_engine(self, engine: Any) -> None:
        """Register a WorkflowEngine to dynamically tune its task throttles."""
        if engine not in self._engines:
            self._engines.append(engine)

    def unregister_engine(self, engine: Any) -> None:
        """Unregister a WorkflowEngine from concurrency tuning."""
        if engine in self._engines:
            self._engines.remove(engine)

    async def _monitor_loop(self) -> None:
        while self.is_running:
            start = time.perf_counter()
            try:
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            elapsed = time.perf_counter() - start
            stutter = elapsed - self.check_interval
            if stutter > self.stutter_threshold:
                context = {
                    "type": "event_loop_stutter",
                    "stutter_ms": stutter * 1000.0,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                self.stutters.append(context)
                logging.getLogger(__name__).warning("Event loop stutter detected: %.2fms", context["stutter_ms"])
                self.tune_concurrency()

    def record_sync_call(self, func: Any, duration: float, args: Any = None, kwargs: Any = None) -> None:
        """Record sync blocking calls exceeding the threshold."""
        func_name = getattr(func, "__name__", str(func))
        func_module = getattr(func, "__module__", "")
        context = {
            "type": "sync_blocking_call",
            "function": f"{func_module}.{func_name}" if func_module else func_name,
            "duration_ms": duration * 1000.0,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        self.sync_calls.append(context)
        logging.getLogger(__name__).warning("Sync blocking call detected: %s took %.2fms", context["function"], context["duration_ms"])
        self.tune_concurrency()

    def tune_concurrency(self) -> None:
        """Scale ThreadPool capacity and WorkflowEngine max_concurrent_tasks dynamically based on recent metrics."""
        now = time.perf_counter()
        has_recent_stutter = any(
            (now - datetime.fromisoformat(s["timestamp"]).timestamp() < 5)
            for s in self.stutters
        )
        has_recent_blocking = any(
            (now - datetime.fromisoformat(c["timestamp"]).timestamp() < 5)
            for c in self.sync_calls
        )

        if has_recent_stutter or has_recent_blocking:
            # Scale down capacity to alleviate resource contention
            if self.executor:
                new_workers = max(2, self.executor._max_workers - 1)
                self.executor._max_workers = new_workers
            for engine in self._engines:
                engine.max_concurrent_tasks = max(1, engine.max_concurrent_tasks - 1)
        else:
            # Scale up capacity to maximize throughput when execution is smooth
            if self.executor:
                new_workers = min(16, self.executor._max_workers + 1)
                self.executor._max_workers = new_workers
            for engine in self._engines:
                engine.max_concurrent_tasks = min(12, engine.max_concurrent_tasks + 1)


# =========================================================================
# 5.  Multi-Agent Dynamic Thread Load Balancer
# =========================================================================

class ConcurrencyBalancer:
    """Robust concurrency balancer to schedule and balance thread pool tasks across swarms.
    
    Offloads heavy operations to a dedicated worker pool to ensure telemetry and 
    dashboard websocket updates are never blocked by slow sync operations.
    """

    def __init__(self, max_heavy_workers: int = 8, max_telemetry_workers: int = 4) -> None:
        self.heavy_pool = ThreadPoolExecutor(max_workers=max_heavy_workers, thread_name_prefix="balancer-heavy")
        self.telemetry_pool = ThreadPoolExecutor(max_workers=max_telemetry_workers, thread_name_prefix="balancer-telemetry")
        self.max_heavy = max_heavy_workers
        self.max_telemetry = max_telemetry_workers
        self.active_tasks: dict[str, int] = {"heavy": 0, "telemetry": 0}
        self._lock = threading.Lock()

    def offload(self, fn: Any, category: str = "heavy", *args: Any, **kwargs: Any) -> Any:
        """Offload a task to a dedicated thread pool category."""
        pool = self.heavy_pool if category == "heavy" else self.telemetry_pool
        
        with self._lock:
            self.active_tasks[category] += 1
        self.balance_loads()
        
        def wrapped(*a: Any, **kw: Any) -> Any:
            try:
                return fn(*a, **kw)
            finally:
                with self._lock:
                    self.active_tasks[category] = max(0, self.active_tasks[category] - 1)
                self.balance_loads()

        return pool.submit(wrapped, *args, **kwargs)

    def balance_loads(self) -> None:
        """Dynamically balance worker allocations based on active task load."""
        with self._lock:
            heavy_load = self.active_tasks["heavy"]
            telemetry_load = self.active_tasks["telemetry"]
            
            # If heavy tasks are piling up but telemetry is idle, expand heavy capacity
            if heavy_load > self.max_heavy and telemetry_load == 0:
                adjusted_heavy = min(16, self.max_heavy + 4)
                adjusted_telemetry = max(2, self.max_telemetry - 2)
                self.heavy_pool._max_workers = adjusted_heavy
                self.telemetry_pool._max_workers = adjusted_telemetry
            # If telemetry is loaded but heavy tasks are idle, expand telemetry capacity
            elif telemetry_load > self.max_telemetry and heavy_load == 0:
                adjusted_telemetry = min(8, self.max_telemetry + 2)
                adjusted_heavy = max(4, self.max_heavy - 2)
                self.heavy_pool._max_workers = adjusted_heavy
                self.telemetry_pool._max_workers = adjusted_telemetry
            # Restore defaults
            else:
                self.heavy_pool._max_workers = self.max_heavy
                self.telemetry_pool._max_workers = self.max_telemetry

    def shutdown(self, wait: bool = True) -> None:
        self.heavy_pool.shutdown(wait=wait)
        self.telemetry_pool.shutdown(wait=wait)


_GLOBAL_BALANCER: ConcurrencyBalancer | None = None

def get_global_balancer() -> ConcurrencyBalancer:
    """Retrieve the global concurrency balancer instance."""
    global _GLOBAL_BALANCER
    if _GLOBAL_BALANCER is None:
        _GLOBAL_BALANCER = ConcurrencyBalancer()
    return _GLOBAL_BALANCER


import os

try:
    import psutil
except ImportError:
    psutil = None

class TelemetryRouter:
    """Asynchronous, thread-safe cost and latency telemetry router that buffers and routes metrics in a non-blocking fashion."""
    
    def __init__(self, workspace_path: str = ".") -> None:
        self.workspace_path = os.path.abspath(workspace_path)
        self._lock = threading.Lock()
        self.buffer: list[dict[str, Any]] = []
        self.max_buffer_size = 500
        
    def record_metric(self, session_id: str, latency_ms: float = 0.0, ws_latency_ms: float = 0.0) -> None:
        """Records telemetry metrics in a thread-safe, non-blocking fashion."""
        cpu_percent = 0.0
        memory_mb = 0.0
        if psutil:
            try:
                cpu_percent = psutil.cpu_percent()
                memory_mb = psutil.Process().memory_info().rss / (1024 * 1024)
            except Exception:
                pass
        else:
            cpu_percent = 15.4  # Mock default
            memory_mb = 124.5  # Mock default

        usd_cost = 0.0
        try:
            from core.ledger import FinancialLedger
        except ImportError:
            from agent_workspace.core.ledger import FinancialLedger
            
        try:
            ledger = FinancialLedger(self.workspace_path)
            usd_cost = ledger.get_total_cost(session_id)
        except Exception:
            pass

        metric = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": session_id,
            "cpu_percent": round(cpu_percent, 2),
            "memory_mb": round(memory_mb, 2),
            "latency_ms": round(latency_ms, 2),
            "ws_latency_ms": round(ws_latency_ms, 2),
            "usd_cost": round(usd_cost, 6)
        }

        with self._lock:
            self.buffer.append(metric)
            if len(self.buffer) > self.max_buffer_size:
                self.buffer.pop(0)

    def get_metrics(self, session_id: str | None = None) -> list[dict[str, Any]]:
        """Retrieves buffered metrics, optionally filtered by session_id."""
        with self._lock:
            if session_id:
                return [m for m in self.buffer if m["session_id"] == session_id]
            return list(self.buffer)


_GLOBAL_TELEMETRY_ROUTER: TelemetryRouter | None = None

def get_telemetry_router(workspace_path: str = ".") -> TelemetryRouter:
    """Retrieve the global telemetry router singleton."""
    global _GLOBAL_TELEMETRY_ROUTER
    if _GLOBAL_TELEMETRY_ROUTER is None:
        _GLOBAL_TELEMETRY_ROUTER = TelemetryRouter(workspace_path)
    return _GLOBAL_TELEMETRY_ROUTER


class CloudCostRouter:
    def __init__(self):
        self.metrics = {
            "google-genai": {"price_per_1k": 0.000075, "base_speed": 80.0, "latency_history": []},
            "aws-bedrock": {"price_per_1k": 0.003, "base_speed": 50.0, "latency_history": []},
            "local-ollama": {"price_per_1k": 0.0, "base_speed": 30.0, "latency_history": []}
        }
        self.lock = threading.Lock()

    def record_latency(self, provider: str, latency_sec: float):
        with self.lock:
            p = provider.lower()
            if p in self.metrics:
                self.metrics[p]["latency_history"].append(latency_sec)
                if len(self.metrics[p]["latency_history"]) > 10:
                    self.metrics[p]["latency_history"].pop(0)

    def get_effective_speed(self, provider: str) -> float:
        with self.lock:
            p = provider.lower()
            if p not in self.metrics:
                return 50.0
            history = self.metrics[p]["latency_history"]
            if history:
                avg_latency = sum(history) / len(history)
                if avg_latency > 0:
                    return min(150.0, max(5.0, 1.0 / avg_latency * 100.0))
            return self.metrics[p]["base_speed"]

    def select_optimal_provider(self, task_type: str, available_providers: list[str]) -> str:
        """
        Choose the optimal provider from available_providers depending on task_type,
        price, and dynamic latency/speed metrics.
        """
        if not available_providers:
            return "google-genai"
            
        weights = {
            "compilation": {"w_cost": 0.1, "w_speed": 0.9},
            "ui_layout": {"w_cost": 0.4, "w_speed": 0.6},
            "text_inference": {"w_cost": 0.8, "w_speed": 0.2}
        }
        
        task_weights = weights.get(task_type, weights["text_inference"])
        w_cost = task_weights["w_cost"]
        w_speed = task_weights["w_speed"]
        
        best_provider = available_providers[0]
        best_score = -1.0
        
        for provider in available_providers:
            p = provider.lower()
            cost = self.metrics.get(p, {"price_per_1k": 0.001})["price_per_1k"]
            speed = self.get_effective_speed(p)
            
            # Utility for cost (lower cost is better utility)
            cost_utility = 1.0 / (cost + 0.0001)
            
            # Weighted utility score
            score = (w_cost * cost_utility) + (w_speed * speed)
            if score > best_score:
                best_score = score
                best_provider = provider
                
        return best_provider


_GLOBAL_COST_ROUTER = CloudCostRouter()

def get_cost_router() -> CloudCostRouter:
    global _GLOBAL_COST_ROUTER
    return _GLOBAL_COST_ROUTER




