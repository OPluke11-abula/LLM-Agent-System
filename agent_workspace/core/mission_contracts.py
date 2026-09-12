"""Typed Mission aggregate contracts and deterministic serialization."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from types import MappingProxyType
from typing import Annotated, Final, Literal

from pydantic import Field, field_validator, model_validator

from agent_workspace.core.product_contracts import (
    ActorId,
    ApprovalId,
    ApprovalStatus,
    ApprovalType,
    CIStatus,
    ContractModel,
    DEFAULT_REQUIRED_VERIFICATION,
    EvidenceId,
    EvidenceType,
    GateId,
    GateStatus,
    HumanDecisionState,
    IdempotencyKey,
    MissionId,
    Mergeability,
    PlanId,
    RiskLevel,
    SCHEMA_VERSION,
    ScopeRequestId,
    TaskId,
    VerificationGateName,
    _validate_relative_paths,
)


class AgentAssignment(ContractModel):
    assignment_id: TaskId
    role: str = Field(min_length=1, max_length=128)
    agent_id: ActorId | None = None
    provider: str | None = Field(default=None, max_length=128)
    model: str | None = Field(default=None, max_length=256)


class PlanTask(ContractModel):
    task_id: TaskId
    title: str = Field(min_length=1, max_length=256)
    description: str = Field(default="", max_length=4000)
    order: int = Field(ge=1)
    dependencies: tuple[TaskId, ...] = ()
    assignment: AgentAssignment | None = None
    assigned_role: str | None = Field(default=None, max_length=128)
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

    @model_validator(mode="after")
    def validate_provider_call_range(self) -> PlanTask:
        if self.estimated_provider_calls_min > self.estimated_provider_calls_max:
            raise ValueError("minimum provider calls cannot exceed maximum")
        return self


class ExecutionPlan(ContractModel):
    schema_version: str = SCHEMA_VERSION
    plan_id: PlanId
    mission_id: MissionId
    revision: int = Field(default=1, ge=1)
    tasks: tuple[PlanTask, ...] = Field(min_length=1)
    approval_status: ApprovalStatus = ApprovalStatus.PENDING
    approved_revision: int | None = Field(default=None, ge=1)
    required_verification: tuple[VerificationGateName, ...] = DEFAULT_REQUIRED_VERIFICATION
    estimated_risk: RiskLevel = RiskLevel.MEDIUM

    @model_validator(mode="after")
    def validate_plan_graph(self) -> ExecutionPlan:
        task_ids = tuple(task.task_id for task in self.tasks)
        if len(set(task_ids)) != len(task_ids):
            raise ValueError("execution plan task IDs must be unique")
        orders = tuple(task.order for task in self.tasks)
        if len(set(orders)) != len(orders):
            raise ValueError("execution plan task order values must be unique")
        known_ids = set(task_ids)
        graph = {task.task_id: task.dependencies for task in self.tasks}
        for task in self.tasks:
            if task.task_id in task.dependencies:
                raise ValueError("execution plan tasks cannot depend on themselves")
            if any(dependency not in known_ids for dependency in task.dependencies):
                raise ValueError("execution plan dependencies must reference existing tasks")
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(task_id: str) -> None:
            if task_id in visiting:
                raise ValueError("execution plan dependencies must be acyclic")
            if task_id in visited:
                return
            visiting.add(task_id)
            for dependency in graph[task_id]:
                visit(dependency)
            visiting.remove(task_id)
            visited.add(task_id)

        for task_id in task_ids:
            visit(task_id)
        if len(set(self.required_verification)) != len(self.required_verification):
            raise ValueError("required verification gates must be unique")
        if self.approval_status is ApprovalStatus.APPROVED:
            if self.approved_revision != self.revision:
                raise ValueError("approved plans must bind their approved revision")
        elif self.approved_revision is not None:
            raise ValueError("only approved plans may record an approved revision")
        return self

    def canonical_digest(self) -> str:
        return hashlib.sha256(serialize_contract(self).encode("utf-8")).hexdigest()


class PlanApprovalSubject(ContractModel):
    kind: Literal["plan"] = "plan"
    plan_id: PlanId
    plan_revision: int = Field(ge=1)
    plan_digest: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")


class ScopeApprovalSubject(ContractModel):
    kind: Literal["scope_expansion"] = "scope_expansion"
    scope_request_id: ScopeRequestId


class DraftPRApprovalSubject(ContractModel):
    kind: Literal["draft_pr"] = "draft_pr"
    review_id: ApprovalId
    plan_id: PlanId
    plan_revision: int = Field(ge=1)
    branch: str = Field(min_length=1, max_length=256)
    head_sha: str = Field(min_length=1, max_length=128)


ApprovalSubject = Annotated[
    PlanApprovalSubject | ScopeApprovalSubject | DraftPRApprovalSubject,
    Field(discriminator="kind"),
]


class ApprovalDecision(ContractModel):
    status: ApprovalStatus
    actor_id: ActorId
    decided_at: datetime
    evidence_refs: tuple[EvidenceId, ...] = ()

    @model_validator(mode="after")
    def decision_is_complete(self) -> ApprovalDecision:
        if self.status is ApprovalStatus.PENDING:
            raise ValueError("a decision must be approved or rejected")
        return self


class ApprovalRequest(ContractModel):
    request_id: ApprovalId
    decision_type: ApprovalType
    subject: ApprovalSubject
    requested_change: str = Field(min_length=1, max_length=4000)
    reason: str = Field(min_length=1, max_length=4000)
    impact: str = Field(min_length=1, max_length=4000)
    requested_actor: ActorId
    decision: ApprovalDecision | None = None
    evidence_refs: tuple[EvidenceId, ...] = ()
    idempotency_key: IdempotencyKey

    @model_validator(mode="after")
    def subject_matches_decision_type(self) -> ApprovalRequest:
        if self.subject.kind != self.decision_type.value:
            raise ValueError("approval subject must match decision type")
        return self


class ApprovalGate(ContractModel):
    gate_id: GateId
    gate_type: ApprovalType
    subject: ApprovalSubject
    status: ApprovalStatus = ApprovalStatus.PENDING
    actor_id: ActorId | None = None
    decided_at: datetime | None = None
    evidence_refs: tuple[EvidenceId, ...] = ()
    idempotency_key: IdempotencyKey

    @model_validator(mode="after")
    def validate_decision_metadata(self) -> ApprovalGate:
        if self.subject.kind != self.gate_type.value:
            raise ValueError("approval gate subject must match gate type")
        has_actor = self.actor_id is not None
        has_timestamp = self.decided_at is not None
        if self.status is ApprovalStatus.PENDING and (has_actor or has_timestamp):
            raise ValueError("pending approvals cannot claim decision metadata")
        if self.status is not ApprovalStatus.PENDING and not (has_actor and has_timestamp):
            raise ValueError("decided approvals require actor and timestamp")
        return self


class ScopeExpansionRequest(ContractModel):
    request_id: ScopeRequestId
    mission_id: MissionId
    requested_paths: tuple[str, ...]
    reason: str = Field(min_length=1, max_length=4000)
    impact: str = Field(min_length=1, max_length=4000)
    risk: RiskLevel
    status: ApprovalStatus = ApprovalStatus.PENDING
    requested_by: ActorId | None = None

    @field_validator("requested_paths")
    @classmethod
    def validate_requested_paths(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return _validate_relative_paths(value)


class EvidenceRecord(ContractModel):
    evidence_id: EvidenceId
    evidence_type: EvidenceType
    source: str = Field(min_length=1, max_length=256)
    operation: str = Field(min_length=1, max_length=512)
    started_at: datetime
    finished_at: datetime
    exit_status: int | None = None
    bounded_output_summary: str = Field(default="", max_length=4000)
    artifact_ref: str | None = Field(default=None, max_length=512)
    commit_sha: str | None = Field(default=None, max_length=128)
    producing_agent: ActorId
    requirement_links: tuple[str, ...] = ()
    task_links: tuple[TaskId, ...] = ()
    plan_revision: int | None = Field(default=None, ge=1)
    verification_status: GateStatus = GateStatus.PENDING

    @model_validator(mode="after")
    def finish_after_start(self) -> EvidenceRecord:
        if self.finished_at < self.started_at:
            raise ValueError("evidence must finish at or after it starts")
        return self

    def with_producing_agent(self, actor_id: ActorId) -> EvidenceRecord:
        return EvidenceRecord.model_validate(
            {**self.model_dump(mode="python"), "producing_agent": actor_id}
        )


class VerificationGate(ContractModel):
    gate: VerificationGateName
    status: GateStatus = GateStatus.PENDING
    evidence_refs: tuple[EvidenceId, ...] = ()

    @model_validator(mode="after")
    def passed_gate_requires_evidence(self) -> VerificationGate:
        if self.status is GateStatus.PASSED and not self.evidence_refs:
            raise ValueError("passed verification gates require evidence references")
        return self


EVIDENCE_TYPE_COMPATIBILITY: Final[MappingProxyType] = MappingProxyType(
    {
        VerificationGateName.REQUIREMENT: frozenset(
            {EvidenceType.COMMAND, EvidenceType.REVIEW, EvidenceType.TEST}
        ),
        VerificationGateName.SCOPE: frozenset(
            {EvidenceType.SCOPE, EvidenceType.COMMAND, EvidenceType.REVIEW}
        ),
        VerificationGateName.ARCHITECTURE: frozenset(
            {EvidenceType.ARCHITECTURE, EvidenceType.COMMAND, EvidenceType.REVIEW}
        ),
        VerificationGateName.TESTS: frozenset({EvidenceType.TEST, EvidenceType.COMMAND}),
        VerificationGateName.SECURITY: frozenset({EvidenceType.SECURITY, EvidenceType.COMMAND}),
        VerificationGateName.QUALITY: frozenset(
            {EvidenceType.QUALITY, EvidenceType.TEST, EvidenceType.COMMAND}
        ),
        VerificationGateName.CI: frozenset({EvidenceType.CI}),
        VerificationGateName.COST: frozenset({EvidenceType.COST, EvidenceType.PROVIDER_CALL}),
    }
)


class MissionBudgetPolicy(ContractModel):
    provider_call_limit: int = Field(default=64, ge=1)
    max_cost: float | None = Field(default=None, ge=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)


class MissionUsageSummary(ContractModel):
    provider_calls: int = Field(default=0, ge=0)
    retries: int = Field(default=0, ge=0)
    healing_calls: int = Field(default=0, ge=0)
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    actual_cost: float | None = Field(default=None, ge=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    accounting_revision: int = Field(default=0, ge=0)
    accounted_at: datetime | None = None


class DraftPullRequestDelivery(ContractModel):
    branch: str = Field(min_length=1, max_length=256)
    commit_shas: tuple[str, ...] = Field(min_length=1)
    pr_number: int = Field(ge=1)
    url: str = Field(min_length=1, max_length=512)
    head_sha: str = Field(min_length=1, max_length=128)
    base_sha: str = Field(min_length=1, max_length=128)
    ci_status: CIStatus
    unresolved_review_thread_count: int = Field(ge=0)
    mergeability: Mergeability
    human_decision_state: HumanDecisionState = HumanDecisionState.PENDING


def serialize_contract(model: ContractModel) -> str:
    """Return deterministic JSON for a canonical product contract."""
    return json.dumps(model.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
