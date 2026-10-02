from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from agent_workspace.core.providers import (
    ProviderResponse,
    ProviderStreamTimeoutError,
    ProviderTransientError,
)


DEFAULT_MAX_PROVIDER_CALLS = 64
DEFAULT_MAX_RETRIES = 12
DEFAULT_MAX_HEALING_CALLS = 8
DEFAULT_MAX_NESTED_DEPTH = 1
DEFAULT_MAX_CONCURRENT_PROVIDER_CALLS = 3


class RetryableProviderError(RuntimeError):
    retryable = True


class PermanentProviderError(RuntimeError):
    retryable = False


class BudgetExhausted(RuntimeError):
    code = "budget_exhausted"

    def __init__(self, dimension: str):
        self.dimension = dimension
        super().__init__(f"{self.code}: {dimension}")


@dataclass(frozen=True)
class FailureClassification:
    retryable: bool
    reason: str


def _status_code(error: Any) -> int | None:
    current = error
    seen: set[int] = set()
    for _ in range(8):
        if current is None or id(current) in seen:
            break
        seen.add(id(current))
        for name in ("status_code", "status"):
            value = getattr(current, name, None)
            if isinstance(value, int):
                return value
        current = getattr(current, "__cause__", None) or getattr(current, "__context__", None)
    return None


def classify_provider_failure(error: Any) -> FailureClassification:
    if isinstance(error, asyncio.CancelledError):
        return FailureClassification(False, "cancelled")

    current = error
    seen: set[int] = set()
    typed_retryable = False
    typed_permanent = False
    for _ in range(8):
        if current is None or id(current) in seen:
            break
        seen.add(id(current))
        marker = getattr(current, "retryable", None)
        if marker is True:
            typed_retryable = True
            break
        if marker is False:
            typed_permanent = True
            break
        current = getattr(current, "__cause__", None) or getattr(current, "__context__", None)

    if typed_retryable:
        return FailureClassification(True, "explicit_temporary_provider_failure")
    if typed_permanent:
        return FailureClassification(False, "explicit_permanent_provider_failure")

    status_code = _status_code(error)
    if status_code in {429, 500, 502, 503, 504}:
        return FailureClassification(True, f"http_{status_code}")
    if status_code in {400, 401, 403, 404, 409, 422}:
        return FailureClassification(False, f"http_{status_code}")

    if isinstance(error, (ProviderTransientError, ProviderStreamTimeoutError, TimeoutError, ConnectionError)):
        return FailureClassification(True, "typed_transient_provider_failure")

    text = str(error).lower()
    permanent_markers = (
        "unauthorized",
        "forbidden",
        "authentication",
        "invalid api key",
        "api key was not provided",
        "subscription",
        "billing",
        "quota",
        "unsupported model",
        "malformed request",
        "validation",
        "context window",
        "offline",
        "disabled provider",
    )
    if any(marker in text for marker in permanent_markers):
        return FailureClassification(False, "permanent_provider_failure")

    retryable_markers = (
        "timeout",
        "timed out",
        "connection",
        "connection reset",
        "temporarily unavailable",
        "rate limit",
        "http 429",
        "http 500",
        "http 502",
        "http 503",
        "http 504",
    )
    if any(marker in text for marker in retryable_markers):
        return FailureClassification(True, "flattened_transient_provider_failure")

    return FailureClassification(False, "ambiguous_provider_failure")


def estimate_provider_cost(model_name: str, prompt_tokens: int, completion_tokens: int) -> float:
    model = model_name.lower()
    if "pro" in model:
        input_rate = 1.25 / 1_000_000
        output_rate = 5.00 / 1_000_000
    else:
        input_rate = 0.075 / 1_000_000
        output_rate = 0.30 / 1_000_000
    return (prompt_tokens * input_rate) + (completion_tokens * output_rate)


class _ProviderAttempt:
    def __init__(self, budget: DebateExecutionBudget):
        self.budget = budget
        self.acquired = False

    async def __aenter__(self) -> _ProviderAttempt:
        await self.budget._acquire_provider()
        self.acquired = True
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        if self.acquired:
            self.budget._release_provider()
        return False


@dataclass
class DebateExecutionBudget:
    max_provider_calls: int = DEFAULT_MAX_PROVIDER_CALLS
    max_retries: int = DEFAULT_MAX_RETRIES
    max_healing_calls: int = DEFAULT_MAX_HEALING_CALLS
    max_nested_depth: int = DEFAULT_MAX_NESTED_DEPTH
    max_concurrent_provider_calls: int = DEFAULT_MAX_CONCURRENT_PROVIDER_CALLS
    provider_calls: int = 0
    retries: int = 0
    healing_calls: int = 0
    current_nested_depth: int = 0
    peak_nested_depth: int = 0
    current_concurrent_provider_calls: int = 0
    peak_concurrent_provider_calls: int = 0
    known_prompt_tokens: int = 0
    known_completion_tokens: int = 0
    known_total_tokens: int = 0
    known_cost_usd: float = 0.0
    exhaustion_reason: str | None = None
    classifications: list[str] = field(default_factory=list)
    _semaphore: asyncio.Semaphore = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for name in (
            "max_provider_calls",
            "max_concurrent_provider_calls",
        ):
            if getattr(self, name) < 1:
                raise ValueError(f"{name} must be at least 1")
        for name in ("max_retries", "max_healing_calls"):
            if getattr(self, name) < 0:
                raise ValueError(f"{name} must be non-negative")
        if self.max_nested_depth < 0:
            raise ValueError("max_nested_depth must be non-negative")
        self._semaphore = asyncio.Semaphore(self.max_concurrent_provider_calls)

    def provider_attempt(self) -> _ProviderAttempt:
        return _ProviderAttempt(self)

    async def _acquire_provider(self) -> None:
        await self._semaphore.acquire()
        if self.provider_calls >= self.max_provider_calls:
            self.exhaustion_reason = "provider_calls"
            self._semaphore.release()
            raise BudgetExhausted("provider_calls")
        self.provider_calls += 1
        self.current_concurrent_provider_calls += 1
        self.peak_concurrent_provider_calls = max(
            self.peak_concurrent_provider_calls,
            self.current_concurrent_provider_calls,
        )

    def _release_provider(self) -> None:
        self.current_concurrent_provider_calls -= 1
        self._semaphore.release()

    def consume_retry(self) -> None:
        if self.retries >= self.max_retries:
            self.exhaustion_reason = "retries"
            raise BudgetExhausted("retries")
        self.retries += 1

    def consume_healing(self) -> None:
        if self.healing_calls >= self.max_healing_calls:
            self.exhaustion_reason = "healing_calls"
            raise BudgetExhausted("healing_calls")
        self.healing_calls += 1

    def check_nested_depth(self, depth: int) -> None:
        if depth > self.max_nested_depth:
            self.exhaustion_reason = "nested_depth"
            raise BudgetExhausted("nested_depth")
        self.current_nested_depth = depth
        self.peak_nested_depth = max(self.peak_nested_depth, depth)

    def record_classification(self, classification: FailureClassification) -> None:
        self.classifications.append(classification.reason)

    def record_usage(self, usage: dict[str, Any] | None, cost_usd: float | None = None) -> None:
        if not usage:
            return
        prompt = usage.get("prompt_tokens")
        completion = usage.get("completion_tokens")
        total = usage.get("total_tokens")
        if isinstance(prompt, int) and prompt >= 0:
            self.known_prompt_tokens += prompt
        if isinstance(completion, int) and completion >= 0:
            self.known_completion_tokens += completion
        if isinstance(total, int) and total >= 0:
            self.known_total_tokens += total
        elif isinstance(prompt, int) and isinstance(completion, int) and prompt >= 0 and completion >= 0:
            self.known_total_tokens += prompt + completion
        if isinstance(cost_usd, (int, float)) and cost_usd >= 0:
            self.known_cost_usd += float(cost_usd)


__all__ = [
    "BudgetExhausted",
    "DebateExecutionBudget",
    "FailureClassification",
    "PermanentProviderError",
    "ProviderResponse",
    "RetryableProviderError",
    "classify_provider_failure",
    "estimate_provider_cost",
]
