"""Mission identity, state, event, and transition-audit contracts."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum, unique

from pydantic import Field

from agent_workspace.core.mission_contracts import (
    ApprovalGate,
    DraftPullRequestDelivery,
    MissionCostSummary,
    ScopeExpansionRequest,
    VerificationGate,
)
from agent_workspace.core.product_contracts import (
    ActorId,
    ContractModel,
    IdempotencyKey,
    MissionId,
    MissionPolicy,
    PlanId,
    RepositoryId,
    SCHEMA_VERSION,
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
    RESUME_STATE_MISSING = "resume_state_missing"
    IDEMPOTENCY_CONFLICT = "idempotency_conflict"


class TransitionRequest(ContractModel):
    event: MissionEvent
    actor_id: ActorId
    idempotency_key: IdempotencyKey


class MissionTransitionAudit(ContractModel):
    audit_id: str = Field(min_length=1)
    event: MissionEvent
    from_state: MissionState
    to_state: MissionState
    actor_id: ActorId
    idempotency_key: IdempotencyKey
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Mission(ContractModel):
    schema_version: str = SCHEMA_VERSION
    mission_id: MissionId
    requirement: str = Field(min_length=1)
    repository_id: RepositoryId
    current_state: MissionState = MissionState.DRAFT
    execution_policy: MissionPolicy
    plan_reference: PlanId | None = None
    budget_policy: MissionCostSummary
    approval_gates: tuple[ApprovalGate, ...] = ()
    scope_expansion_requests: tuple[ScopeExpansionRequest, ...] = ()
    verification_gates: tuple[VerificationGate, ...] = ()
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    actor_id: ActorId
    final_draft_pr: DraftPullRequestDelivery | None = None
    resume_state: MissionState | None = None
    transition_audit: tuple[MissionTransitionAudit, ...] = ()
