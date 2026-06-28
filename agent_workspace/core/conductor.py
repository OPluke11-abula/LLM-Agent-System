"""Structured conductor plans for LAS agent orchestration telemetry."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


ExecutionMode = Literal["fast", "pro", "ultra"]
RiskLevel = Literal["low", "medium", "high"]
Topology = Literal[
    "single_worker",
    "planner_worker_verifier",
    "parallel_specialists",
    "debate_consensus",
]
VerificationKind = Literal["none", "self_check", "verifier", "proof_of_consensus"]


class ConductorSubtask(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    description: str = ""
    role_id: str = "worker"
    depends_on: list[str] = Field(default_factory=list)
    status: Literal["planned", "running", "done", "blocked"] = "planned"


class ConductorRole(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    responsibility: str
    model_capabilities: list[str] = Field(default_factory=list)
    required: bool = True


class ModelCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str
    model: str
    account_id: str | None = None
    capabilities: list[str] = Field(default_factory=list)
    cost_tier: str = "unknown"
    latency_tier: str = "unknown"


class SelectedModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role_id: str
    provider: str
    model: str
    account_id: str | None = None
    selection_reason: str


class MemoryScope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str
    long_term_enabled: bool = True
    retrieval_limit: int = Field(default=5, ge=0, le=50)
    tenant_id: str | None = None


class VerificationStrategy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: VerificationKind
    required: bool = False
    approval_required: bool = False
    success_criteria: list[str] = Field(default_factory=list)


class ExecutionBudget(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_iterations: int = Field(ge=1)
    max_tool_calls: int = Field(ge=0)
    token_budget: int | None = Field(default=None, ge=0)
    cost_limit: float | None = Field(default=None, ge=0)


class FallbackRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trigger: str
    action: str
    target_provider: str | None = None
    target_model: str | None = None


class RouteOutcomeHint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record_id: str
    task_type: str
    execution_mode: str
    success: bool
    error_type: str | None = None
    token_count: int = Field(default=0, ge=0)
    latency_ms: int = Field(default=0, ge=0)
    human_intervention_count: int = Field(default=0, ge=0)


class ConductorPlan(BaseModel):
    """Audit-friendly plan describing how LAS intends to orchestrate a task."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = "1.0"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    task_id: str
    task_summary: str
    execution_mode: ExecutionMode
    risk_level: RiskLevel
    topology: Topology
    task_type: str
    intent: Literal["CHAT", "TASK"]
    subtasks: list[ConductorSubtask]
    roles: list[ConductorRole]
    candidate_models: list[ModelCandidate]
    selected_models: list[SelectedModel]
    tool_allowlist: list[str] = Field(default_factory=list)
    memory_scope: MemoryScope
    verification_strategy: VerificationStrategy
    budget: ExecutionBudget
    fallbacks: list[FallbackRule] = Field(default_factory=list)
    routing_memory_hints: list[RouteOutcomeHint] = Field(default_factory=list)
    decision_rationale: str

    @model_validator(mode="after")
    def validate_high_risk_ultra_gate(self) -> "ConductorPlan":
        if (
            self.execution_mode == "ultra"
            and (
                self.verification_strategy.kind != "proof_of_consensus"
                or not self.verification_strategy.required
                or not self.verification_strategy.approval_required
            )
        ):
            raise ValueError("Ultra plans require ProofOfConsensus approval")
        return self


def _summarize_task(user_input: str, limit: int = 160) -> str:
    normalized = " ".join(user_input.split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[: limit - 3]}..."


def _normalize_token_budget(value: Any) -> int | None:
    if value is None:
        return None
    try:
        budget = int(value)
    except (TypeError, ValueError):
        return None
    return budget if budget >= 0 else None


def _infer_execution_shape(intent: str, task_type: str) -> tuple[ExecutionMode, RiskLevel, Topology, VerificationStrategy]:
    if intent == "CHAT":
        return (
            "fast",
            "low",
            "single_worker",
            VerificationStrategy(kind="none", required=False, approval_required=False),
        )
    if task_type in {"compilation", "ui_layout"}:
        return (
            "pro",
            "medium",
            "planner_worker_verifier",
            VerificationStrategy(
                kind="verifier",
                required=True,
                approval_required=False,
                success_criteria=["planned route completed", "relevant checks reported"],
            ),
        )
    return (
        "pro",
        "low",
        "planner_worker_verifier",
        VerificationStrategy(
            kind="self_check",
            required=True,
            approval_required=False,
            success_criteria=["answer satisfies user request"],
        ),
    )


def _default_roles(execution_mode: ExecutionMode, topology: Topology) -> list[ConductorRole]:
    if topology == "single_worker":
        return [
            ConductorRole(
                id="worker",
                name="Worker",
                responsibility="Answer the user request directly.",
                model_capabilities=["general"],
            )
        ]
    roles = [
        ConductorRole(
            id="planner",
            name="Thinker",
            responsibility="Decompose the request and choose the execution path.",
            model_capabilities=["planning", "reasoning"],
        ),
        ConductorRole(
            id="worker",
            name="Worker",
            responsibility="Execute the planned task with approved tools.",
            model_capabilities=["coding", "tool_use"],
        ),
        ConductorRole(
            id="verifier",
            name="Verifier",
            responsibility="Check the result against task requirements and safety gates.",
            model_capabilities=["review", "verification"],
        ),
    ]
    if execution_mode == "ultra":
        roles.append(
            ConductorRole(
                id="consensus",
                name="Consensus",
                responsibility="Gate high-impact decisions through proof-of-consensus.",
                model_capabilities=["governance", "security"],
            )
        )
    return roles


def _normalize_route_outcome_hints(raw_hints: list[dict[str, Any]] | None) -> list[RouteOutcomeHint]:
    hints: list[RouteOutcomeHint] = []
    for raw in raw_hints or []:
        payload = raw.get("payload", raw)
        if not isinstance(payload, dict):
            continue
        try:
            hints.append(
                RouteOutcomeHint(
                    record_id=str(raw.get("id") or payload.get("record_id") or ""),
                    task_type=str(payload.get("task_type", "unknown")),
                    execution_mode=str(payload.get("execution_mode", "unknown")),
                    success=bool(payload.get("success", False)),
                    error_type=payload.get("error_type"),
                    token_count=int(payload.get("token_count") or 0),
                    latency_ms=int(payload.get("latency_ms") or 0),
                    human_intervention_count=int(payload.get("human_intervention_count") or 0),
                )
            )
        except (TypeError, ValueError):
            continue
    return hints


def build_default_conductor_plan(
    *,
    task_id: str,
    task_summary: str,
    session_id: str,
    task_type: str,
    intent: str,
    resolved_tools: list[str],
    selected_account: dict[str, Any],
    max_iterations: int,
    max_tool_calls: int,
    long_term_enabled: bool = True,
    tenant_id: str | None = None,
    route_outcome_hints: list[dict[str, Any]] | None = None,
) -> ConductorPlan:
    """Build a deterministic telemetry plan without changing runtime behavior."""

    normalized_intent = "CHAT" if intent == "CHAT" else "TASK"
    execution_mode, risk_level, topology, verification = _infer_execution_shape(normalized_intent, task_type)
    provider = str(selected_account.get("provider", "unknown"))
    model = str(selected_account.get("model", "unknown"))
    account_id = selected_account.get("id")
    candidate = ModelCandidate(
        provider=provider,
        model=model,
        account_id=str(account_id) if account_id is not None else None,
        capabilities=["general"],
    )
    selected = SelectedModel(
        role_id="worker" if execution_mode == "fast" else "planner",
        provider=provider,
        model=model,
        account_id=str(account_id) if account_id is not None else None,
        selection_reason="Matches the already-resolved account; telemetry-only plan preserves current routing.",
    )
    tool_allowlist = [] if normalized_intent == "CHAT" else list(resolved_tools)
    normalized_hints = _normalize_route_outcome_hints(route_outcome_hints)
    decision_rationale = "Telemetry-only conductor plan mirrors the current router decision without changing execution."
    if normalized_hints:
        decision_rationale += " Prior routing outcomes are attached as bounded audit hints only."

    return ConductorPlan(
        task_id=task_id,
        task_summary=_summarize_task(task_summary),
        execution_mode=execution_mode,
        risk_level=risk_level,
        topology=topology,
        task_type=task_type,
        intent=normalized_intent,
        subtasks=[
            ConductorSubtask(
                id="subtask-1",
                title="Handle user request",
                description=_summarize_task(task_summary),
                role_id=selected.role_id,
            )
        ],
        roles=_default_roles(execution_mode, topology),
        candidate_models=[candidate],
        selected_models=[selected],
        tool_allowlist=tool_allowlist,
        memory_scope=MemoryScope(
            session_id=session_id,
            long_term_enabled=long_term_enabled,
            retrieval_limit=5 if long_term_enabled else 0,
            tenant_id=tenant_id,
        ),
        verification_strategy=verification,
        budget=ExecutionBudget(
            max_iterations=max_iterations,
            max_tool_calls=max_tool_calls,
            token_budget=_normalize_token_budget(selected_account.get("token_budget")),
        ),
        fallbacks=[
            FallbackRule(
                trigger="provider_error",
                action="use_existing_provider_failover",
            )
        ],
        routing_memory_hints=normalized_hints,
        decision_rationale=decision_rationale,
    )
