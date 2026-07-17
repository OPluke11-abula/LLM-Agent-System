"""Mission identity, state, transition, and aggregate contracts."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum, unique

from pydantic import Field, model_validator

from agent_workspace.core.mission_contracts import (
    ApprovalGate,
    ApprovalSubject,
    DraftPRApprovalSubject,
    DraftPullRequestDelivery,
    ExecutionPlan,
    EvidenceRecord,
    MissionBudgetPolicy,
    MissionUsageSummary,
    ScopeExpansionRequest,
    VerificationGate,
)
from agent_workspace.core.product_contracts import (
    ActorId,
    ApprovalId,
    ContractModel,
    DEFAULT_REQUIRED_VERIFICATION,
    IdempotencyKey,
    MissionId,
    MissionPolicy,
    PlanId,
    RepositoryId,
    SCHEMA_VERSION,
    ScopeRequestId,
    VerificationGateName,
)


@unique
class MissionState(StrEnum):
    DRAFT = "draft"
    PLANNING = "planning"
    AWAITING_APPROVAL = "awaiting_approval"
    RUNNING = "running"
    NEEDS_DECISION = "needs_decision"
    VERIFYING = "verifying"
    REVIEW_READY = "review_ready"
    DRAFT_PR_CREATED = "draft_pr_created"
    CLOSED = "closed"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    FAILED = "failed"
    BUDGET_EXHAUSTED = "budget_exhausted"
    SCOPE_BLOCKED = "scope_blocked"
    CI_FAILED = "ci_failed"


@unique
class MissionEvent(StrEnum):
    START_PLANNING = "start_planning"
    SUBMIT_PLAN = "submit_plan"
    APPROVE_PLAN = "approve_plan"
    REJECT_PLAN = "reject_plan"
    BEGIN_VERIFICATION = "begin_verification"
    COMPLETE_VERIFICATION = "complete_verification"
    FAIL_CI = "fail_ci"
    RETRY_VERIFICATION = "retry_verification"
    CREATE_DRAFT_PR = "create_draft_pr"
    REQUEST_SCOPE_EXPANSION = "request_scope_expansion"
    BLOCK_SCOPE = "block_scope"
    APPROVE_SCOPE = "approve_scope"
    REJECT_SCOPE = "reject_scope"
    PAUSE = "pause"
    RESUME = "resume"
    CANCEL = "cancel"
    FAIL = "fail"
    EXHAUST_BUDGET = "exhaust_budget"
    CLOSE = "close"


@unique
class TransitionErrorCode(StrEnum):
    INVALID_TRANSITION = "invalid_transition"
    TERMINAL_STATE = "terminal_state"
    PLAN_APPROVAL_REQUIRED = "plan_approval_required"
    VERIFICATION_REQUIRED = "verification_required"
    DRAFT_PR_PERMISSION_REQUIRED = "draft_pr_permission_required"
    DRAFT_PR_APPROVAL_REQUIRED = "draft_pr_approval_required"
    SCOPE_DECISION_REQUIRED = "scope_decision_required"
    APPROVAL_SUBJECT_REQUIRED = "approval_subject_required"
    APPROVAL_SUBJECT_MISMATCH = "approval_subject_mismatch"
    RESUME_STATE_MISSING = "resume_state_missing"
    IDEMPOTENCY_CONFLICT = "idempotency_conflict"


class TransitionRequest(ContractModel):
    event: MissionEvent
    actor_id: ActorId
    idempotency_key: IdempotencyKey
    approval_subject: ApprovalSubject | None = None


class MissionTransitionAudit(ContractModel):
    audit_id: ApprovalId
    event: MissionEvent
    from_state: MissionState
    to_state: MissionState
    from_revision: int = Field(ge=0)
    to_revision: int = Field(ge=1)
    actor_id: ActorId
    idempotency_key: IdempotencyKey
    approval_subject: ApprovalSubject | None = None
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Mission(ContractModel):
    schema_version: str = SCHEMA_VERSION
    mission_id: MissionId
    requirement: str = Field(min_length=1, max_length=4000)
    repository_id: RepositoryId
    current_state: MissionState = MissionState.DRAFT
    revision: int = Field(default=0, ge=0)
    execution_policy: MissionPolicy
    execution_plan: ExecutionPlan | None = None
    plan_reference: PlanId | None = None
    plan_revision: int | None = Field(default=None, ge=1)
    budget_policy: MissionBudgetPolicy = Field(default_factory=MissionBudgetPolicy)
    usage_summary: MissionUsageSummary = Field(default_factory=MissionUsageSummary)
    approval_gates: tuple[ApprovalGate, ...] = ()
    scope_expansion_requests: tuple[ScopeExpansionRequest, ...] = ()
    evidence_records: tuple[EvidenceRecord, ...] = ()
    required_verification: tuple[VerificationGateName, ...] = DEFAULT_REQUIRED_VERIFICATION
    verification_gates: tuple[VerificationGate, ...] = ()
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    actor_id: ActorId
    draft_pr_review_subject: DraftPRApprovalSubject | None = None
    final_draft_pr: DraftPullRequestDelivery | None = None
    resume_state: MissionState | None = None
    transition_audit: tuple[MissionTransitionAudit, ...] = ()

    @model_validator(mode="after")
    def validate_aggregate_references(self) -> Mission:
        if self.execution_plan is None:
            if self.plan_reference is not None or self.plan_revision is not None:
                raise ValueError("plan references require an execution plan")
        elif (
            self.plan_reference != self.execution_plan.plan_id
            or self.plan_revision != self.execution_plan.revision
        ):
            raise ValueError("mission plan references must match the execution plan")
        if len({gate.gate_id for gate in self.approval_gates}) != len(self.approval_gates):
            raise ValueError("approval gate IDs must be unique")
        if len({item.request_id for item in self.scope_expansion_requests}) != len(
            self.scope_expansion_requests
        ):
            raise ValueError("scope request IDs must be unique")
        if len({item.evidence_id for item in self.evidence_records}) != len(self.evidence_records):
            raise ValueError("evidence IDs must be unique")
        if len({gate.gate for gate in self.verification_gates}) != len(self.verification_gates):
            raise ValueError("verification gate names must be unique")
        if len(set(self.required_verification)) != len(self.required_verification):
            raise ValueError("required verification gate names must be unique")
        if len({audit.idempotency_key for audit in self.transition_audit}) != len(
            self.transition_audit
        ):
            raise ValueError("transition idempotency keys must be unique")
        return self
