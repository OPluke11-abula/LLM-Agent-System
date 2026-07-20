"""Mission identity, state, transition, and aggregate contracts."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum, unique
from typing import assert_never

from pydantic import Field, model_validator

from agent_workspace.core.mission_contracts import (
    ApprovalGate,
    ApprovalSubject,
    ApprovalStatus,
    ApprovalType,
    DraftPRApprovalSubject,
    DraftPullRequestDelivery,
    EVIDENCE_TYPE_COMPATIBILITY,
    ExecutionPlan,
    EvidenceRecord,
    GateStatus,
    MissionBudgetPolicy,
    MissionUsageSummary,
    PlanApprovalSubject,
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


class MissionCapabilities(ContractModel):
    mission_id: MissionId
    revision: int = Field(ge=0)
    current_state: MissionState
    allowed_events: tuple[MissionEvent, ...]
    required_approval_type: ApprovalType | None = None
    plan_approval_required: bool
    verification_incomplete: bool
    draft_pr_permission_disabled: bool
    blocked_reason: str | None = None


class MissionAggregateError(ValueError):
    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        self.detail = detail
        super().__init__(detail)


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
    approval_gates: tuple[ApprovalGate, ...] = Field(default=(), max_length=256)
    scope_expansion_requests: tuple[ScopeExpansionRequest, ...] = ()
    evidence_records: tuple[EvidenceRecord, ...] = Field(default=(), max_length=1000)
    required_verification: tuple[VerificationGateName, ...] = DEFAULT_REQUIRED_VERIFICATION
    verification_gates: tuple[VerificationGate, ...] = Field(default=(), max_length=32)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    actor_id: ActorId
    owner_actor_id: ActorId | None = None
    draft_pr_review_subject: DraftPRApprovalSubject | None = None
    final_draft_pr: DraftPullRequestDelivery | None = None
    resume_state: MissionState | None = None
    transition_audit: tuple[MissionTransitionAudit, ...] = Field(default=(), max_length=1000)

    @property
    def owner_id(self) -> ActorId:
        return self.owner_actor_id or self.actor_id

    def verification_complete(self) -> bool:
        evidence_by_id = {record.evidence_id: record for record in self.evidence_records}
        gates_by_name = {gate.gate: gate for gate in self.verification_gates}
        for gate_name in self.required_verification:
            gate = gates_by_name.get(gate_name)
            if gate is None:
                return False
            match gate.status:
                case GateStatus.NOT_APPLICABLE:
                    continue
                case GateStatus.PASSED:
                    if not gate.evidence_refs:
                        return False
                    linked_records: list[EvidenceRecord] = []
                    for evidence_ref in gate.evidence_refs:
                        record = evidence_by_id.get(evidence_ref)
                        if record is None:
                            return False
                        linked_records.append(record)
                    compatible = EVIDENCE_TYPE_COMPATIBILITY[gate.gate]
                    if any(
                        record.verification_status is not GateStatus.PASSED
                        or record.evidence_type not in compatible
                        for record in linked_records
                    ):
                        return False
                case GateStatus.PENDING | GateStatus.FAILED | GateStatus.BLOCKED:
                    return False
                case unreachable:
                    assert_never(unreachable)
        return True

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
        evidence_by_id = {record.evidence_id: record for record in self.evidence_records}
        if self.execution_plan is not None:
            task_ids = {task.task_id for task in self.execution_plan.tasks}
            for record in self.evidence_records:
                if record.task_links and record.plan_revision != self.execution_plan.revision:
                    raise ValueError("evidence task links must bind the current plan revision")
                if any(task_id not in task_ids for task_id in record.task_links):
                    raise ValueError("evidence task links must reference current plan tasks")
        final_decisions: set[ApprovalSubject] = set()
        for gate in self.approval_gates:
            if any(ref not in evidence_by_id for ref in gate.evidence_refs):
                raise ValueError("approval evidence references must exist in the Mission")
            if gate.status is not ApprovalStatus.PENDING:
                if gate.subject in final_decisions:
                    raise ValueError("an approval subject can have only one final decision")
                final_decisions.add(gate.subject)
        for gate in self.verification_gates:
            records = tuple(evidence_by_id.get(ref) for ref in gate.evidence_refs)
            if any(record is None for record in records):
                raise ValueError("verification evidence references must exist in the Mission")
            if gate.status is GateStatus.PASSED:
                if any(record.verification_status is not GateStatus.PASSED for record in records):
                    raise ValueError("passed verification gates require passed evidence")
                compatible = EVIDENCE_TYPE_COMPATIBILITY[gate.gate]
                if any(record.evidence_type not in compatible for record in records):
                    raise ValueError("verification evidence type is incompatible with the gate")
        return self

    def attach_plan(self, plan: ExecutionPlan) -> Mission:
        if plan.mission_id != self.mission_id:
            raise MissionAggregateError("plan_mission_mismatch", "Plan Mission ID does not match")
        if self.execution_plan is not None:
            if plan.plan_id == self.execution_plan.plan_id and plan.revision == self.execution_plan.revision:
                if plan.canonical_digest() == self.execution_plan.canonical_digest():
                    return self
                raise MissionAggregateError(
                    "immutable_plan_conflict",
                    "Plan content cannot change under the same ID and revision",
                )
            if plan.plan_id != self.execution_plan.plan_id or plan.revision <= self.execution_plan.revision:
                raise MissionAggregateError("plan_revision_conflict", "Plan revisions must increase monotonically")
            if self.current_state in {
                MissionState.RUNNING,
                MissionState.VERIFYING,
                MissionState.REVIEW_READY,
                MissionState.DRAFT_PR_CREATED,
                MissionState.CLOSED,
            }:
                raise MissionAggregateError(
                    "approved_plan_locked",
                    "The current Mission state cannot replace its plan",
                )
        return Mission.model_validate(
            {
                **self.model_dump(mode="python"),
                "execution_plan": plan,
                "plan_reference": plan.plan_id,
                "plan_revision": plan.revision,
                "required_verification": plan.required_verification,
            }
        )

    def add_approval_gate(self, gate: ApprovalGate) -> Mission:
        if gate.gate_id in {item.gate_id for item in self.approval_gates}:
            raise MissionAggregateError("duplicate_approval_gate", "Approval gate ID already exists")
        if gate.gate_type is ApprovalType.PLAN:
            if self.execution_plan is None:
                raise MissionAggregateError("plan_required", "Plan approval requires an attached plan")
            subject = gate.subject
            if not isinstance(subject, PlanApprovalSubject):
                raise MissionAggregateError("approval_subject_mismatch", "Plan approval subject is invalid")
            if (
                subject.plan_id != self.execution_plan.plan_id
                or subject.plan_revision != self.execution_plan.revision
                or subject.plan_digest != self.execution_plan.canonical_digest()
            ):
                raise MissionAggregateError("approval_subject_mismatch", "Plan approval subject is stale")
        existing = next((item for item in self.approval_gates if item.subject == gate.subject), None)
        if existing is not None:
            if (
                existing.status is gate.status
                and existing.idempotency_key == gate.idempotency_key
                and existing.evidence_refs == gate.evidence_refs
            ):
                return self
            raise MissionAggregateError(
                "immutable_decision_conflict",
                "Approval subject already has a final decision",
            )
        return Mission.model_validate(
            {
                **self.model_dump(mode="python"),
                "approval_gates": self.approval_gates + (gate,),
            }
        )

    def add_evidence_record(self, evidence: EvidenceRecord) -> Mission:
        if evidence.evidence_id in {item.evidence_id for item in self.evidence_records}:
            raise MissionAggregateError("duplicate_evidence", "Evidence ID already exists")
        return Mission.model_validate(
            {
                **self.model_dump(mode="python"),
                "evidence_records": self.evidence_records + (evidence,),
            }
        )

    def record_verification_gate(self, gate: VerificationGate) -> Mission:
        existing = next((item for item in self.verification_gates if item.gate == gate.gate), None)
        if existing is not None:
            refs = tuple(dict.fromkeys(existing.evidence_refs + gate.evidence_refs))
            gate = VerificationGate.model_validate(
                {**gate.model_dump(mode="python"), "evidence_refs": refs}
            )
        gates = tuple(item for item in self.verification_gates if item.gate != gate.gate) + (gate,)
        return Mission.model_validate(
            {**self.model_dump(mode="python"), "verification_gates": gates}
        )
