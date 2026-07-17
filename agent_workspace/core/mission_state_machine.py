"""Central deterministic Mission transition validation for Developer Beta."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Final

from agent_workspace.core.mission_contracts import ApprovalStatus, ApprovalType, GateStatus
from agent_workspace.core.mission_model import (
    Mission,
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


_LEGAL_TRANSITIONS: Final[dict[tuple[MissionState, MissionEvent], MissionState]] = {
    (MissionState.DRAFT, MissionEvent.START_PLANNING): MissionState.PLANNING,
    (MissionState.PLANNING, MissionEvent.SUBMIT_PLAN): MissionState.AWAITING_APPROVAL,
    (MissionState.AWAITING_APPROVAL, MissionEvent.APPROVE_PLAN): MissionState.RUNNING,
    (MissionState.AWAITING_APPROVAL, MissionEvent.REJECT_PLAN): MissionState.PLANNING,
    (MissionState.RUNNING, MissionEvent.BEGIN_VERIFICATION): MissionState.VERIFYING,
    (MissionState.RUNNING, MissionEvent.REQUEST_SCOPE_EXPANSION): MissionState.NEEDS_DECISION,
    (MissionState.RUNNING, MissionEvent.BLOCK_SCOPE): MissionState.SCOPE_BLOCKED,
    (MissionState.NEEDS_DECISION, MissionEvent.BLOCK_SCOPE): MissionState.SCOPE_BLOCKED,
    (MissionState.NEEDS_DECISION, MissionEvent.APPROVE_SCOPE): MissionState.RUNNING,
    (MissionState.NEEDS_DECISION, MissionEvent.REJECT_SCOPE): MissionState.PLANNING,
    (MissionState.SCOPE_BLOCKED, MissionEvent.APPROVE_SCOPE): MissionState.RUNNING,
    (MissionState.SCOPE_BLOCKED, MissionEvent.REJECT_SCOPE): MissionState.PLANNING,
    (MissionState.VERIFYING, MissionEvent.COMPLETE_VERIFICATION): MissionState.REVIEW_READY,
    (MissionState.VERIFYING, MissionEvent.FAIL_CI): MissionState.CI_FAILED,
    (MissionState.CI_FAILED, MissionEvent.RETRY_VERIFICATION): MissionState.VERIFYING,
    (MissionState.REVIEW_READY, MissionEvent.CREATE_DRAFT_PR): MissionState.DRAFT_PR_CREATED,
    (MissionState.REVIEW_READY, MissionEvent.CLOSE): MissionState.CLOSED,
    (MissionState.DRAFT_PR_CREATED, MissionEvent.CLOSE): MissionState.CLOSED,
}

_TERMINAL_STATES: Final[frozenset[MissionState]] = frozenset(
    {MissionState.CLOSED, MissionState.CANCELLED, MissionState.FAILED, MissionState.BUDGET_EXHAUSTED}
)
_PAUSABLE_STATES: Final[frozenset[MissionState]] = frozenset(
    {
        MissionState.PLANNING,
        MissionState.AWAITING_APPROVAL,
        MissionState.RUNNING,
        MissionState.NEEDS_DECISION,
        MissionState.VERIFYING,
        MissionState.REVIEW_READY,
        MissionState.CI_FAILED,
        MissionState.SCOPE_BLOCKED,
    }
)


def _add_recovery_transitions() -> None:
    for state in _PAUSABLE_STATES:
        _LEGAL_TRANSITIONS[(state, MissionEvent.PAUSE)] = MissionState.PAUSED
        _LEGAL_TRANSITIONS[(state, MissionEvent.CANCEL)] = MissionState.CANCELLED
        _LEGAL_TRANSITIONS[(state, MissionEvent.FAIL)] = MissionState.FAILED
    for state in (MissionState.PLANNING, MissionState.RUNNING, MissionState.VERIFYING):
        _LEGAL_TRANSITIONS[(state, MissionEvent.EXHAUST_BUDGET)] = MissionState.BUDGET_EXHAUSTED
    _LEGAL_TRANSITIONS[(MissionState.DRAFT, MissionEvent.CANCEL)] = MissionState.CANCELLED
    _LEGAL_TRANSITIONS[(MissionState.PAUSED, MissionEvent.CANCEL)] = MissionState.CANCELLED
    _LEGAL_TRANSITIONS[(MissionState.PAUSED, MissionEvent.FAIL)] = MissionState.FAILED


_add_recovery_transitions()


def _has_approved_gate(mission: Mission, gate_type: ApprovalType) -> bool:
    return any(
        gate.gate_type is gate_type and gate.status is ApprovalStatus.APPROVED
        for gate in mission.approval_gates
    )


def _require_plan_approval(mission: Mission, request: TransitionRequest) -> None:
    if not _has_approved_gate(mission, ApprovalType.PLAN):
        raise MissionTransitionError(
            TransitionErrorCode.PLAN_APPROVAL_REQUIRED,
            mission.current_state,
            request.event,
            "plan approval is required before running",
        )


def _require_verification(mission: Mission, request: TransitionRequest) -> None:
    complete = bool(mission.verification_gates) and all(
        gate.status in (GateStatus.PASSED, GateStatus.NOT_APPLICABLE)
        for gate in mission.verification_gates
    )
    if not complete:
        raise MissionTransitionError(
            TransitionErrorCode.VERIFICATION_REQUIRED,
            mission.current_state,
            request.event,
            "all verification gates must be passed or not applicable",
        )


def _require_draft_pr(mission: Mission, request: TransitionRequest) -> None:
    if not mission.execution_policy.scope.draft_pr_permission:
        raise MissionTransitionError(
            TransitionErrorCode.DRAFT_PR_PERMISSION_REQUIRED,
            mission.current_state,
            request.event,
            "Draft PR permission is not enabled in the scope policy",
        )
    if not _has_approved_gate(mission, ApprovalType.DRAFT_PR):
        raise MissionTransitionError(
            TransitionErrorCode.DRAFT_PR_APPROVAL_REQUIRED,
            mission.current_state,
            request.event,
            "explicit Draft PR approval is required",
        )


def _require_scope_decision(mission: Mission, request: TransitionRequest) -> None:
    if not any(item.status is ApprovalStatus.APPROVED for item in mission.scope_expansion_requests):
        raise MissionTransitionError(
            TransitionErrorCode.SCOPE_DECISION_REQUIRED,
            mission.current_state,
            request.event,
            "an approved scope-expansion decision is required",
        )


_GUARDS: Final[dict[MissionEvent, Callable[[Mission, TransitionRequest], None]]] = {
    MissionEvent.APPROVE_PLAN: _require_plan_approval,
    MissionEvent.COMPLETE_VERIFICATION: _require_verification,
    MissionEvent.CREATE_DRAFT_PR: _require_draft_pr,
    MissionEvent.APPROVE_SCOPE: _require_scope_decision,
}


class MissionStateMachine:
    def transition(self, mission: Mission, request: TransitionRequest) -> TransitionResult:
        existing = next(
            (audit for audit in mission.transition_audit if audit.idempotency_key == request.idempotency_key),
            None,
        )
        if existing is not None:
            if existing.event is not request.event:
                raise MissionTransitionError(
                    TransitionErrorCode.IDEMPOTENCY_CONFLICT,
                    mission.current_state,
                    request.event,
                    "idempotency key was already used for another event",
                )
            return TransitionResult(mission=mission, audit=existing, replayed=True)

        if mission.current_state in _TERMINAL_STATES:
            raise MissionTransitionError(
                TransitionErrorCode.TERMINAL_STATE,
                mission.current_state,
                request.event,
                "terminal Mission states cannot transition",
            )

        target = _LEGAL_TRANSITIONS.get((mission.current_state, request.event))
        if request.event is MissionEvent.RESUME and mission.current_state is MissionState.PAUSED:
            target = mission.resume_state
            if target is None:
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

        audit = MissionTransitionAudit(
            audit_id=f"transition:{request.idempotency_key}",
            event=request.event,
            from_state=mission.current_state,
            to_state=target,
            actor_id=request.actor_id,
            idempotency_key=request.idempotency_key,
        )
        resume_state = mission.current_state if target is MissionState.PAUSED else None
        updated = mission.model_copy(
            update={
                "current_state": target,
                "updated_at": datetime.now(timezone.utc),
                "resume_state": resume_state,
                "transition_audit": mission.transition_audit + (audit,),
            }
        )
        return TransitionResult(mission=updated, audit=audit, replayed=False)


_DEFAULT_MACHINE: Final[MissionStateMachine] = MissionStateMachine()


def transition(mission: Mission, request: TransitionRequest) -> TransitionResult:
    return _DEFAULT_MACHINE.transition(mission, request)
