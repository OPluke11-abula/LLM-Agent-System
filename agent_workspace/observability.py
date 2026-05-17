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

REQUEST_COUNT = Counter(
    "las_request_total",
    "Total number of agent requests",
    ["endpoint", "session_id"],
)

REQUEST_LATENCY = Histogram(
    "las_request_latency_seconds",
    "Latency of agent requests in seconds",
    ["endpoint"],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0),
)

REQUEST_ERRORS = Counter(
    "las_request_errors_total",
    "Total number of agent request errors",
    ["endpoint", "error_type"],
)

TOOL_CALL_COUNT = Counter(
    "las_tool_call_total",
    "Total number of tool calls",
    ["tool_name", "status"],
)

TOOL_CALL_LATENCY = Histogram(
    "las_tool_call_latency_seconds",
    "Latency of individual tool calls",
    ["tool_name"],
)

LLM_CALL_COUNT = Counter(
    "las_llm_call_total",
    "Total number of LLM provider calls",
    ["provider", "status"],
)

LLM_CALL_LATENCY = Histogram(
    "las_llm_call_latency_seconds",
    "Latency of LLM provider calls",
    ["provider"],
)

ACTIVE_SESSIONS = Gauge(
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
