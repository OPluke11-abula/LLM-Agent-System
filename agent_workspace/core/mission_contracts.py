"""Mission-specific typed contracts built on the shared product contract types."""

from __future__ import annotations

import json
from datetime import datetime

from pydantic import Field, field_validator, model_validator

from agent_workspace.core.product_contracts import (
    ActorId,
    ApprovalStatus,
    ApprovalType,
    CIStatus,
    ContractModel,
    EvidenceType,
    GateStatus,
    HumanDecisionState,
    IdempotencyKey,
    MissionId,
    Mergeability,
    PlanId,
    RiskLevel,
    SCHEMA_VERSION,
    VerificationGateName,
    _validate_relative_paths,
)


class AgentAssignment(ContractModel):
    assignment_id: str = Field(min_length=1)
    role: str = Field(min_length=1)
    agent_id: str | None = None
    provider: str | None = None
    model: str | None = None


class PlanTask(ContractModel):
    task_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    description: str = ""
    order: int = Field(ge=1)
    dependencies: tuple[str, ...] = ()
    assignment: AgentAssignment | None = None
    assigned_role: str | None = None
    expected_paths: tuple[str, ...] = ()
    verification_requirements: tuple[str, ...] = ()
    estimated_risk: RiskLevel = RiskLevel.MEDIUM
    estimated_provider_calls_min: int = Field(default=0, ge=0)
    estimated_provider_calls_max: int = Field(default=0, ge=0)
    approval_status: ApprovalStatus = ApprovalStatus.PENDING

    @field_validator("expected_paths")
    @classmethod
    def validate_expected_paths(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return _validate_relative_paths(value)


class ExecutionPlan(ContractModel):
    schema_version: str = SCHEMA_VERSION
    plan_id: PlanId
    mission_id: MissionId
    revision: int = Field(default=1, ge=1)
    tasks: tuple[PlanTask, ...]
    approval_status: ApprovalStatus = ApprovalStatus.PENDING
    required_verification: tuple[VerificationGateName, ...] = ()
    estimated_risk: RiskLevel = RiskLevel.MEDIUM


class ApprovalDecision(ContractModel):
    status: ApprovalStatus
    actor_id: ActorId
    decided_at: datetime
    evidence_refs: tuple[str, ...] = ()


class ApprovalRequest(ContractModel):
    request_id: str = Field(min_length=1)
    decision_type: ApprovalType
    requested_change: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    impact: str = Field(min_length=1)
    requested_actor: ActorId
    decision: ApprovalDecision | None = None
    evidence_refs: tuple[str, ...] = ()
    idempotency_key: IdempotencyKey


class ApprovalGate(ContractModel):
    gate_id: str = Field(min_length=1)
    gate_type: ApprovalType
    status: ApprovalStatus = ApprovalStatus.PENDING
    actor_id: ActorId | None = None
    decided_at: datetime | None = None
    evidence_refs: tuple[str, ...] = ()
    idempotency_key: IdempotencyKey


class ScopeExpansionRequest(ContractModel):
    request_id: str = Field(min_length=1)
    mission_id: MissionId
    requested_paths: tuple[str, ...]
    reason: str = Field(min_length=1)
    impact: str = Field(min_length=1)
    risk: RiskLevel
    status: ApprovalStatus = ApprovalStatus.PENDING
    requested_by: ActorId | None = None

    @field_validator("requested_paths")
    @classmethod
    def validate_requested_paths(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return _validate_relative_paths(value)


class EvidenceRecord(ContractModel):
    evidence_id: str = Field(min_length=1)
    evidence_type: EvidenceType
    source: str = Field(min_length=1)
    operation: str = Field(min_length=1)
    started_at: datetime
    finished_at: datetime
    exit_status: int | None = None
    bounded_output_summary: str = Field(default="", max_length=4000)
    artifact_ref: str | None = None
    commit_sha: str | None = None
    producing_agent: str = Field(min_length=1)
    requirement_links: tuple[str, ...] = ()
    task_links: tuple[str, ...] = ()
    verification_status: GateStatus = GateStatus.PENDING


class VerificationGate(ContractModel):
    gate: VerificationGateName
    status: GateStatus = GateStatus.PENDING
    evidence_refs: tuple[str, ...] = ()

    @model_validator(mode="after")
    def passed_gate_requires_evidence(self) -> VerificationGate:
        if self.status is GateStatus.PASSED and not self.evidence_refs:
            raise ValueError("passed verification gates require evidence references")
        return self


class MissionCostSummary(ContractModel):
    provider_call_limit: int = Field(ge=1)
    estimated_provider_calls: int = Field(default=0, ge=0)
    actual_provider_calls: int = Field(default=0, ge=0)
    estimated_cost: float | None = Field(default=None, ge=0)
    actual_cost: float | None = Field(default=None, ge=0)
    currency: str = "USD"
    retry_count: int = Field(default=0, ge=0)


class DraftPullRequestDelivery(ContractModel):
    branch: str = Field(min_length=1)
    commit_shas: tuple[str, ...]
    pr_number: int = Field(ge=1)
    url: str
    head_sha: str = Field(min_length=1)
    base_sha: str = Field(min_length=1)
    ci_status: CIStatus
    unresolved_review_thread_count: int = Field(ge=0)
    mergeability: Mergeability
    human_decision_state: HumanDecisionState = HumanDecisionState.PENDING


def serialize_contract(model: ContractModel) -> str:
    """Return deterministic JSON for a canonical product contract."""
    return json.dumps(model.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
