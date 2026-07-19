"""Central deterministic Mission transition validation for Developer Beta."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Callable, Final, Mapping

from agent_workspace.core.mission_contracts import (
    ApprovalStatus,
    ApprovalType,
    ApprovalSubject,
    DraftPRApprovalSubject,
    GateStatus,
    PlanApprovalSubject,
    ScopeApprovalSubject,
)
from agent_workspace.core.mission_model import (
    Mission,
    MissionCapabilities,
    MissionEvent,
    MissionState,
    MissionTransitionAudit,
    TransitionErrorCode,
    TransitionRequest,
)


class MissionTransitionError(ValueError):
    def __init__(
        self,
        code: TransitionErrorCode,
        current_state: MissionState,
        event: MissionEvent,
        detail: str,
    ) -> None:
        self.code = code
        self.current_state = current_state
        self.event = event
        self.detail = detail
        super().__init__(detail)

    def __str__(self) -> str:
        return f"{self.code.value}: {self.detail}"


@dataclass(frozen=True, slots=True)
class TransitionResult:
    mission: Mission
    audit: MissionTransitionAudit
    replayed: bool


Clock = Callable[[], datetime]


_LEGAL_TRANSITIONS: Final[Mapping[tuple[MissionState, MissionEvent], MissionState]] = MappingProxyType(
    {
        (MissionState.DRAFT, MissionEvent.START_PLANNING): MissionState.PLANNING,
        (MissionState.DRAFT, MissionEvent.CANCEL): MissionState.CANCELLED,
        (MissionState.PLANNING, MissionEvent.SUBMIT_PLAN): MissionState.AWAITING_APPROVAL,
        (MissionState.PLANNING, MissionEvent.PAUSE): MissionState.PAUSED,
        (MissionState.PLANNING, MissionEvent.CANCEL): MissionState.CANCELLED,
        (MissionState.PLANNING, MissionEvent.FAIL): MissionState.FAILED,
        (MissionState.PLANNING, MissionEvent.EXHAUST_BUDGET): MissionState.BUDGET_EXHAUSTED,
        (MissionState.AWAITING_APPROVAL, MissionEvent.APPROVE_PLAN): MissionState.RUNNING,
        (MissionState.AWAITING_APPROVAL, MissionEvent.REJECT_PLAN): MissionState.PLANNING,
        (MissionState.AWAITING_APPROVAL, MissionEvent.PAUSE): MissionState.PAUSED,
        (MissionState.AWAITING_APPROVAL, MissionEvent.CANCEL): MissionState.CANCELLED,
        (MissionState.AWAITING_APPROVAL, MissionEvent.FAIL): MissionState.FAILED,
        (MissionState.RUNNING, MissionEvent.BEGIN_VERIFICATION): MissionState.VERIFYING,
        (MissionState.RUNNING, MissionEvent.REQUEST_SCOPE_EXPANSION): MissionState.NEEDS_DECISION,
        (MissionState.RUNNING, MissionEvent.BLOCK_SCOPE): MissionState.SCOPE_BLOCKED,
        (MissionState.RUNNING, MissionEvent.PAUSE): MissionState.PAUSED,
        (MissionState.RUNNING, MissionEvent.CANCEL): MissionState.CANCELLED,
        (MissionState.RUNNING, MissionEvent.FAIL): MissionState.FAILED,
        (MissionState.RUNNING, MissionEvent.EXHAUST_BUDGET): MissionState.BUDGET_EXHAUSTED,
        (MissionState.NEEDS_DECISION, MissionEvent.BLOCK_SCOPE): MissionState.SCOPE_BLOCKED,
        (MissionState.NEEDS_DECISION, MissionEvent.APPROVE_SCOPE): MissionState.RUNNING,
        (MissionState.NEEDS_DECISION, MissionEvent.REJECT_SCOPE): MissionState.PLANNING,
        (MissionState.NEEDS_DECISION, MissionEvent.PAUSE): MissionState.PAUSED,
        (MissionState.NEEDS_DECISION, MissionEvent.CANCEL): MissionState.CANCELLED,
        (MissionState.NEEDS_DECISION, MissionEvent.FAIL): MissionState.FAILED,
        (MissionState.SCOPE_BLOCKED, MissionEvent.APPROVE_SCOPE): MissionState.RUNNING,
        (MissionState.SCOPE_BLOCKED, MissionEvent.REJECT_SCOPE): MissionState.PLANNING,
        (MissionState.SCOPE_BLOCKED, MissionEvent.PAUSE): MissionState.PAUSED,
        (MissionState.SCOPE_BLOCKED, MissionEvent.CANCEL): MissionState.CANCELLED,
        (MissionState.SCOPE_BLOCKED, MissionEvent.FAIL): MissionState.FAILED,
        (MissionState.VERIFYING, MissionEvent.COMPLETE_VERIFICATION): MissionState.REVIEW_READY,
        (MissionState.VERIFYING, MissionEvent.FAIL_CI): MissionState.CI_FAILED,
        (MissionState.VERIFYING, MissionEvent.PAUSE): MissionState.PAUSED,
        (MissionState.VERIFYING, MissionEvent.CANCEL): MissionState.CANCELLED,
        (MissionState.VERIFYING, MissionEvent.FAIL): MissionState.FAILED,
        (MissionState.VERIFYING, MissionEvent.EXHAUST_BUDGET): MissionState.BUDGET_EXHAUSTED,
        (MissionState.CI_FAILED, MissionEvent.RETRY_VERIFICATION): MissionState.VERIFYING,
        (MissionState.CI_FAILED, MissionEvent.PAUSE): MissionState.PAUSED,
        (MissionState.CI_FAILED, MissionEvent.CANCEL): MissionState.CANCELLED,
        (MissionState.CI_FAILED, MissionEvent.FAIL): MissionState.FAILED,
        (MissionState.REVIEW_READY, MissionEvent.CREATE_DRAFT_PR): MissionState.DRAFT_PR_CREATED,
        (MissionState.REVIEW_READY, MissionEvent.CLOSE): MissionState.CLOSED,
        (MissionState.REVIEW_READY, MissionEvent.PAUSE): MissionState.PAUSED,
        (MissionState.REVIEW_READY, MissionEvent.CANCEL): MissionState.CANCELLED,
        (MissionState.REVIEW_READY, MissionEvent.FAIL): MissionState.FAILED,
        (MissionState.DRAFT_PR_CREATED, MissionEvent.CLOSE): MissionState.CLOSED,
        (MissionState.PAUSED, MissionEvent.CANCEL): MissionState.CANCELLED,
        (MissionState.PAUSED, MissionEvent.FAIL): MissionState.FAILED,
    }
)

_TERMINAL_STATES: Final[frozenset[MissionState]] = frozenset(
    {MissionState.CLOSED, MissionState.CANCELLED, MissionState.FAILED, MissionState.BUDGET_EXHAUSTED}
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _subject_or_error(
    mission: Mission,
    request: TransitionRequest,
    expected: ApprovalType,
) -> ApprovalSubject:
    subject = request.approval_subject
    if subject is None:
        raise MissionTransitionError(
            TransitionErrorCode.APPROVAL_SUBJECT_REQUIRED,
            mission.current_state,
            request.event,
            "the exact approval subject is required",
        )
    if subject.kind != expected.value:
        raise MissionTransitionError(
            TransitionErrorCode.APPROVAL_SUBJECT_MISMATCH,
            mission.current_state,
            request.event,
            "approval subject does not match the event",
        )
    return subject


def _require_plan_approval(mission: Mission, request: TransitionRequest) -> None:
    subject_value = _subject_or_error(mission, request, ApprovalType.PLAN)
    if not isinstance(subject_value, PlanApprovalSubject):
        raise MissionTransitionError(
            TransitionErrorCode.APPROVAL_SUBJECT_MISMATCH,
            mission.current_state,
            request.event,
            "plan approval requires a plan subject",
        )
    subject = subject_value
    if (
        mission.execution_plan is None
        or subject.plan_id != mission.execution_plan.plan_id
        or subject.plan_revision != mission.execution_plan.revision
        or subject.plan_digest != mission.execution_plan.canonical_digest()
    ):
        raise MissionTransitionError(
            TransitionErrorCode.APPROVAL_SUBJECT_MISMATCH,
            mission.current_state,
            request.event,
            "plan approval subject is stale or unrelated",
        )
    if not any(
        gate.gate_type is ApprovalType.PLAN
        and gate.status is ApprovalStatus.APPROVED
        and gate.subject == subject
        for gate in mission.approval_gates
    ):
        raise MissionTransitionError(
            TransitionErrorCode.PLAN_APPROVAL_REQUIRED,
            mission.current_state,
            request.event,
            "matching plan approval is required before running",
        )


def _require_verification(mission: Mission, request: TransitionRequest) -> None:
    by_name = {gate.gate: gate for gate in mission.verification_gates}
    complete = all(
        gate_name in by_name
        and by_name[gate_name].status in (GateStatus.PASSED, GateStatus.NOT_APPLICABLE)
        for gate_name in mission.required_verification
    )
    if not complete:
        raise MissionTransitionError(
            TransitionErrorCode.VERIFICATION_REQUIRED,
            mission.current_state,
            request.event,
            "every required verification gate must be passed or not applicable",
        )


def _require_scope_decision(mission: Mission, request: TransitionRequest) -> None:
    subject_value = _subject_or_error(mission, request, ApprovalType.SCOPE_EXPANSION)
    if not isinstance(subject_value, ScopeApprovalSubject):
        raise MissionTransitionError(
            TransitionErrorCode.APPROVAL_SUBJECT_MISMATCH,
            mission.current_state,
            request.event,
            "scope approval requires a scope subject",
        )
    if not any(
        item.request_id == subject_value.scope_request_id for item in mission.scope_expansion_requests
    ) or not any(
        gate.gate_type is ApprovalType.SCOPE_EXPANSION
        and gate.status is ApprovalStatus.APPROVED
        and gate.subject == subject_value
        for gate in mission.approval_gates
    ):
        raise MissionTransitionError(
            TransitionErrorCode.SCOPE_DECISION_REQUIRED,
            mission.current_state,
            request.event,
            "matching scope approval is required before continuing",
        )


def _require_draft_pr(mission: Mission, request: TransitionRequest) -> None:
    if not mission.execution_policy.scope.draft_pr_permission:
        raise MissionTransitionError(
            TransitionErrorCode.DRAFT_PR_PERMISSION_REQUIRED,
            mission.current_state,
            request.event,
            "Draft PR permission is not enabled in the scope policy",
        )
    subject_value = _subject_or_error(mission, request, ApprovalType.DRAFT_PR)
    if not isinstance(subject_value, DraftPRApprovalSubject):
        raise MissionTransitionError(
            TransitionErrorCode.APPROVAL_SUBJECT_MISMATCH,
            mission.current_state,
            request.event,
            "Draft PR authorization requires a delivery review subject",
        )
    if mission.draft_pr_review_subject != subject_value or not any(
        gate.gate_type is ApprovalType.DRAFT_PR
        and gate.status is ApprovalStatus.APPROVED
        and gate.subject == subject_value
        for gate in mission.approval_gates
    ):
        raise MissionTransitionError(
            TransitionErrorCode.DRAFT_PR_APPROVAL_REQUIRED,
            mission.current_state,
            request.event,
            "matching Draft PR approval is required for the reviewed head",
        )


_GUARDS: Final[Mapping[MissionEvent, Callable[[Mission, TransitionRequest], None]]] = MappingProxyType(
    {
        MissionEvent.APPROVE_PLAN: _require_plan_approval,
        MissionEvent.COMPLETE_VERIFICATION: _require_verification,
        MissionEvent.CREATE_DRAFT_PR: _require_draft_pr,
        MissionEvent.APPROVE_SCOPE: _require_scope_decision,
    }
)


class MissionStateMachine:
    def __init__(self, clock: Clock | None = None) -> None:
        self._clock = clock or _utc_now

    def capabilities(self, mission: Mission) -> MissionCapabilities:
        allowed = tuple(
            event
            for (state, event), _target in _LEGAL_TRANSITIONS.items()
            if state is mission.current_state
        )
        if mission.current_state is MissionState.PAUSED and mission.resume_state is not None:
            allowed = allowed + (MissionEvent.RESUME,)
        plan_approval_required = mission.current_state is MissionState.AWAITING_APPROVAL
        verification_incomplete = mission.current_state is MissionState.VERIFYING and not self._verification_complete(mission)
        draft_pr_permission_disabled = (
            mission.current_state is MissionState.REVIEW_READY
            and not mission.execution_policy.scope.draft_pr_permission
        )
        required_approval_type = {
            MissionState.AWAITING_APPROVAL: ApprovalType.PLAN,
            MissionState.NEEDS_DECISION: ApprovalType.SCOPE_EXPANSION,
            MissionState.SCOPE_BLOCKED: ApprovalType.SCOPE_EXPANSION,
            MissionState.REVIEW_READY: ApprovalType.DRAFT_PR,
        }.get(mission.current_state)
        blocked_reason = None
        if plan_approval_required and mission.execution_plan is None:
            blocked_reason = TransitionErrorCode.PLAN_APPROVAL_REQUIRED.value
        elif verification_incomplete:
            blocked_reason = TransitionErrorCode.VERIFICATION_REQUIRED.value
        elif draft_pr_permission_disabled:
            blocked_reason = TransitionErrorCode.DRAFT_PR_PERMISSION_REQUIRED.value
        return MissionCapabilities(
            mission_id=mission.mission_id,
            revision=mission.revision,
            current_state=mission.current_state,
            allowed_events=allowed,
            required_approval_type=required_approval_type,
            plan_approval_required=plan_approval_required,
            verification_incomplete=verification_incomplete,
            draft_pr_permission_disabled=draft_pr_permission_disabled,
            blocked_reason=blocked_reason,
        )

    @staticmethod
    def _verification_complete(mission: Mission) -> bool:
        by_name = {gate.gate: gate for gate in mission.verification_gates}
        return all(
            gate_name in by_name
            and by_name[gate_name].status in (GateStatus.PASSED, GateStatus.NOT_APPLICABLE)
            for gate_name in mission.required_verification
        )

    def transition(self, mission: Mission, request: TransitionRequest) -> TransitionResult:
        existing = next(
            (audit for audit in mission.transition_audit if audit.idempotency_key == request.idempotency_key),
            None,
        )
        if existing is not None:
            if existing.event is not request.event or existing.approval_subject != request.approval_subject:
                raise MissionTransitionError(
                    TransitionErrorCode.IDEMPOTENCY_CONFLICT,
                    mission.current_state,
                    request.event,
                    "idempotency key was already used for another event or subject",
                )
            return TransitionResult(mission=mission, audit=existing, replayed=True)
        if mission.current_state in _TERMINAL_STATES:
            raise MissionTransitionError(
                TransitionErrorCode.TERMINAL_STATE,
                mission.current_state,
                request.event,
                "terminal Mission states cannot transition",
            )
        target = mission.resume_state if request.event is MissionEvent.RESUME else _LEGAL_TRANSITIONS.get(
            (mission.current_state, request.event)
        )
        if request.event is MissionEvent.RESUME and target is None:
            raise MissionTransitionError(
                TransitionErrorCode.RESUME_STATE_MISSING,
                mission.current_state,
                request.event,
                "paused Mission has no recoverable resume state",
            )
        if target is None:
            raise MissionTransitionError(
                TransitionErrorCode.INVALID_TRANSITION,
                mission.current_state,
                request.event,
                "event is not legal from the current state",
            )
        guard = _GUARDS.get(request.event)
        if guard is not None:
            guard(mission, request)
        occurred_at = self._clock()
        next_revision = mission.revision + 1
        audit = MissionTransitionAudit(
            audit_id=f"transition:{request.idempotency_key}",
            event=request.event,
            from_state=mission.current_state,
            to_state=target,
            from_revision=mission.revision,
            to_revision=next_revision,
            actor_id=request.actor_id,
            idempotency_key=request.idempotency_key,
            approval_subject=request.approval_subject,
            occurred_at=occurred_at,
        )
        resume_state = mission.current_state if target is MissionState.PAUSED else None
        updated = mission.model_copy(
            update={
                "current_state": target,
                "revision": next_revision,
                "updated_at": occurred_at,
                "resume_state": resume_state,
                "transition_audit": mission.transition_audit + (audit,),
            }
        )
        return TransitionResult(mission=updated, audit=audit, replayed=False)


_DEFAULT_MACHINE: Final[MissionStateMachine] = MissionStateMachine()


def transition(mission: Mission, request: TransitionRequest) -> TransitionResult:
    return _DEFAULT_MACHINE.transition(mission, request)
