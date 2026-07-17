from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from agent_workspace.core.mission_model import (
    Mission,
    MissionEvent,
    MissionState,
    TransitionErrorCode,
    TransitionRequest,
)
from agent_workspace.core.mission_state_machine import (
    _LEGAL_TRANSITIONS,
    MissionStateMachine,
    MissionTransitionError,
    transition,
)
from agent_workspace.core.mission_contracts import (
    ApprovalGate,
    ApprovalRequest,
    ApprovalStatus,
    ApprovalType,
    DraftPullRequestDelivery,
    EvidenceRecord,
    EvidenceType,
    ExecutionPlan,
    GateStatus,
    MissionCostSummary,
    PlanTask,
    serialize_contract,
    ScopeExpansionRequest,
    VerificationGate,
    VerificationGateName,
)
from agent_workspace.core.product_contracts import (
    CIStatus,
    ExecutionPolicyPreset,
    HumanDecisionState,
    MissionPolicy,
    RepositoryProfile,
    RiskLevel,
    ScopePolicy,
)


def make_repository() -> RepositoryProfile:
    return RepositoryProfile(
        repository_id="repo-1",
        repository_name="LAS",
        local_path="/private/local/repo",
        remote_url="https://github.com/example/LAS.git",
        base_branch="main",
    )


def make_policy(*, draft_pr_permission: bool = True) -> MissionPolicy:
    return MissionPolicy(
        preset=ExecutionPolicyPreset.BALANCED,
        scope=ScopePolicy(
            allowed_paths=["agent_workspace", "docs"],
            protected_paths=[".agent/memory"],
            draft_pr_permission=draft_pr_permission,
        ),
    )


def make_mission(
    *,
    state: MissionState = MissionState.DRAFT,
    policy: MissionPolicy | None = None,
    approvals: tuple[ApprovalGate, ...] = (),
    verification_gates: tuple[VerificationGate, ...] = (),
    scope_requests: tuple[ScopeExpansionRequest, ...] = (),
) -> Mission:
    selected_policy = policy or make_policy()
    return Mission(
        mission_id="mission-1",
        requirement="Add a PR risk summary.",
        repository_id="repo-1",
        current_state=state,
        execution_policy=selected_policy,
        plan_reference="plan-1",
        budget_policy=MissionCostSummary(provider_call_limit=64),
        approval_gates=approvals,
        verification_gates=verification_gates,
        scope_expansion_requests=scope_requests,
        actor_id="developer-1",
    )


def approved_gate(gate_type: ApprovalType, gate_id: str) -> ApprovalGate:
    return ApprovalGate(
        gate_id=gate_id,
        gate_type=gate_type,
        status=ApprovalStatus.APPROVED,
        actor_id="developer-1",
        decided_at=datetime.now(timezone.utc),
        idempotency_key=f"approval-{gate_id}",
    )


def passed_verification() -> VerificationGate:
    return VerificationGate(
        gate=VerificationGateName.TESTS,
        status=GateStatus.PASSED,
        evidence_refs=["evidence-1"],
    )


def test_contracts_round_trip_without_serializing_local_paths_or_secrets() -> None:
    profile = make_repository()
    dumped = profile.model_dump(mode="json")

    assert "local_path" not in dumped
    assert "api_key" not in dumped
    assert RepositoryProfile.model_validate(dumped).repository_id == "repo-1"

    task = PlanTask(
        task_id="task-1",
        title="Inspect architecture",
        description="Inspect the existing runtime seams.",
        order=1,
        assigned_role="architect",
        expected_paths=["agent_workspace", "docs"],
        verification_requirements=["architecture review"],
        estimated_risk=RiskLevel.LOW,
    )
    plan = ExecutionPlan(
        plan_id="plan-1",
        mission_id="mission-1",
        tasks=[task],
        approval_status=ApprovalStatus.PENDING,
    )

    assert ExecutionPlan.model_validate_json(plan.model_dump_json()) == plan
    assert serialize_contract(plan) == serialize_contract(plan)
    assert '"approval_status":"pending"' in serialize_contract(plan)


def test_scope_policy_rejects_absolute_paths_and_auto_merge() -> None:
    absolute_path = "D:" + "/workspace/LAS"
    with pytest.raises(ValidationError):
        ScopePolicy(allowed_paths=[absolute_path])

    with pytest.raises(ValidationError):
        ScopePolicy(auto_merge_allowed=True)


def test_passed_verification_gate_requires_evidence_reference() -> None:
    with pytest.raises(ValidationError):
        VerificationGate(
            gate=VerificationGateName.SECURITY,
            status=GateStatus.PASSED,
            evidence_refs=[],
        )


def test_evidence_record_has_bounded_serializable_fields() -> None:
    evidence = EvidenceRecord(
        evidence_id="evidence-1",
        evidence_type=EvidenceType.TEST,
        source="pytest",
        operation="python -m pytest -q agent_workspace/tests/test_mission_contracts.py",
        started_at=datetime.now(timezone.utc),
        finished_at=datetime.now(timezone.utc),
        exit_status=0,
        bounded_output_summary="1 passed",
        commit_sha="a" * 40,
        producing_agent="codex",
        task_links=["task-1"],
        verification_status=GateStatus.PASSED,
    )

    assert len(evidence.bounded_output_summary) <= 4000
    assert evidence.model_dump(mode="json")["exit_status"] == 0


def test_state_machine_requires_plan_approval_before_running() -> None:
    machine = MissionStateMachine()
    awaiting = transition(
        transition(
            make_mission(),
            TransitionRequest(
                event=MissionEvent.START_PLANNING,
                actor_id="developer-1",
                idempotency_key="start-planning",
            ),
        ).mission,
        TransitionRequest(
            event=MissionEvent.SUBMIT_PLAN,
            actor_id="developer-1",
            idempotency_key="submit-plan",
        ),
    ).mission

    with pytest.raises(MissionTransitionError) as error:
        machine.transition(
            awaiting,
            TransitionRequest(
                event=MissionEvent.APPROVE_PLAN,
                actor_id="developer-1",
                idempotency_key="approve-plan",
            ),
        )

    assert "approval" in str(error.value).lower()


def test_state_machine_transitions_to_running_after_approved_plan() -> None:
    mission = make_mission(
        state=MissionState.AWAITING_APPROVAL,
        approvals=(approved_gate(ApprovalType.PLAN, "plan-gate"),),
    )

    result = transition(
        mission,
        TransitionRequest(
            event=MissionEvent.APPROVE_PLAN,
            actor_id="developer-1",
            idempotency_key="approve-plan",
        ),
    )

    assert result.mission.current_state is MissionState.RUNNING
    assert result.audit.from_state is MissionState.AWAITING_APPROVAL
    assert result.audit.to_state is MissionState.RUNNING


def test_review_ready_requires_completed_verification_gates() -> None:
    mission = make_mission(state=MissionState.VERIFYING)

    with pytest.raises(MissionTransitionError) as error:
        transition(
            mission,
            TransitionRequest(
                event=MissionEvent.COMPLETE_VERIFICATION,
                actor_id="developer-1",
                idempotency_key="complete-verification",
            ),
        )

    assert "verification" in str(error.value).lower()

    ready = transition(
        mission.model_copy(update={"verification_gates": (passed_verification(),)}),
        TransitionRequest(
            event=MissionEvent.COMPLETE_VERIFICATION,
            actor_id="developer-1",
            idempotency_key="complete-verification-approved",
        ),
    )

    assert ready.mission.current_state is MissionState.REVIEW_READY


def test_draft_pr_requires_permission_and_explicit_approval() -> None:
    mission = make_mission(
        state=MissionState.REVIEW_READY,
        policy=make_policy(draft_pr_permission=True),
        verification_gates=(passed_verification(),),
    )

    with pytest.raises(MissionTransitionError) as error:
        transition(
            mission,
            TransitionRequest(
                event=MissionEvent.CREATE_DRAFT_PR,
                actor_id="developer-1",
                idempotency_key="create-draft-pr",
            ),
        )
    assert "approval" in str(error.value).lower()

    delivered = transition(
        mission.model_copy(
            update={
                "approval_gates": (
                    approved_gate(ApprovalType.DRAFT_PR, "draft-pr-gate"),
                )
            }
        ),
        TransitionRequest(
            event=MissionEvent.CREATE_DRAFT_PR,
            actor_id="developer-1",
            idempotency_key="create-draft-pr-approved",
        ),
    )

    assert delivered.mission.current_state is MissionState.DRAFT_PR_CREATED


def test_scope_blocked_work_requires_an_approved_scope_decision() -> None:
    blocked = transition(
        make_mission(state=MissionState.RUNNING),
        TransitionRequest(
            event=MissionEvent.BLOCK_SCOPE,
            actor_id="developer-1",
            idempotency_key="block-scope",
        ),
    ).mission

    with pytest.raises(MissionTransitionError) as error:
        transition(
            blocked,
            TransitionRequest(
                event=MissionEvent.APPROVE_SCOPE,
                actor_id="developer-1",
                idempotency_key="approve-scope",
            ),
        )
    assert "scope" in str(error.value).lower()

    resumed = transition(
        blocked.model_copy(
            update={
                "scope_expansion_requests": (
                    ScopeExpansionRequest(
                        request_id="scope-1",
                        mission_id="mission-1",
                        requested_paths=["agent_workspace/core"],
                        reason="The contract module is required.",
                        impact="Adds the P1 canonical contract.",
                        risk=RiskLevel.LOW,
                        status=ApprovalStatus.APPROVED,
                    ),
                )
            }
        ),
        TransitionRequest(
            event=MissionEvent.APPROVE_SCOPE,
            actor_id="developer-1",
            idempotency_key="approve-scope-approved",
        ),
    )

    assert resumed.mission.current_state is MissionState.RUNNING


def test_transition_requests_are_idempotent_and_auditable() -> None:
    request = TransitionRequest(
        event=MissionEvent.START_PLANNING,
        actor_id="developer-1",
        idempotency_key="same-request",
    )
    first = transition(make_mission(), request)
    replay = transition(first.mission, request)

    assert first.replayed is False
    assert replay.replayed is True
    assert replay.mission == first.mission
    assert len(replay.mission.transition_audit) == 1


def test_terminal_states_fail_closed_and_no_merge_state_exists() -> None:
    cancelled = transition(
        make_mission(state=MissionState.RUNNING),
        TransitionRequest(
            event=MissionEvent.CANCEL,
            actor_id="developer-1",
            idempotency_key="cancel",
        ),
    ).mission

    with pytest.raises(MissionTransitionError) as error:
        transition(
            cancelled,
            TransitionRequest(
                event=MissionEvent.RESUME,
                actor_id="developer-1",
                idempotency_key="resume-after-cancel",
            ),
        )

    assert TransitionErrorCode.TERMINAL_STATE.value in str(error.value)
    assert "merged" not in {state.value for state in MissionState}
    assert "merge" not in {event.value for event in MissionEvent}


def test_draft_pr_delivery_contract_preserves_human_decision_boundary() -> None:
    delivery = DraftPullRequestDelivery(
        branch="productization/p1-product-contract",
        commit_shas=["a" * 40],
        pr_number=42,
        url="https://github.com/example/LAS/pull/42",
        head_sha="a" * 40,
        base_sha="b" * 40,
        ci_status=CIStatus.PENDING,
        unresolved_review_thread_count=0,
        mergeability="mergeable",
        human_decision_state=HumanDecisionState.PENDING,
    )

    assert "merged" not in delivery.model_dump(mode="json")


def test_approval_request_captures_human_decision_boundary() -> None:
    request = ApprovalRequest(
        request_id="approval-1",
        decision_type=ApprovalType.SCOPE_EXPANSION,
        requested_change="Add the contract test directory to scope.",
        reason="The tests verify the requested product contract.",
        impact="Adds one repository-relative test path.",
        requested_actor="developer-1",
        idempotency_key="approval-request-1",
    )

    assert request.decision is None
    assert request.model_dump(mode="json")["decision_type"] == "scope_expansion"


def test_every_declared_transition_is_executable() -> None:
    for (state, event), expected_state in _LEGAL_TRANSITIONS.items():
        mission = make_mission(state=state)
        if event is MissionEvent.APPROVE_PLAN:
            mission = mission.model_copy(
                update={"approval_gates": (approved_gate(ApprovalType.PLAN, "plan-gate"),)}
            )
        elif event is MissionEvent.COMPLETE_VERIFICATION:
            mission = mission.model_copy(update={"verification_gates": (passed_verification(),)})
        elif event is MissionEvent.CREATE_DRAFT_PR:
            mission = mission.model_copy(
                update={"approval_gates": (approved_gate(ApprovalType.DRAFT_PR, "draft-pr-gate"),)}
            )
        elif event is MissionEvent.APPROVE_SCOPE:
            mission = mission.model_copy(
                update={
                    "scope_expansion_requests": (
                        ScopeExpansionRequest(
                            request_id="scope-1",
                            mission_id="mission-1",
                            requested_paths=["agent_workspace/core"],
                            reason="The contract module is required.",
                            impact="Adds the P1 canonical contract.",
                            risk=RiskLevel.LOW,
                            status=ApprovalStatus.APPROVED,
                        ),
                    )
                }
            )

        result = transition(
            mission,
            TransitionRequest(
                event=event,
                actor_id="developer-1",
                idempotency_key=f"legal-{state.value}-{event.value}",
            ),
        )

        assert result.mission.current_state is expected_state


def test_pause_resume_and_idempotency_conflict_are_explicit() -> None:
    paused = transition(
        make_mission(state=MissionState.RUNNING),
        TransitionRequest(
            event=MissionEvent.PAUSE,
            actor_id="developer-1",
            idempotency_key="pause-running",
        ),
    ).mission

    resumed = transition(
        paused,
        TransitionRequest(
            event=MissionEvent.RESUME,
            actor_id="developer-1",
            idempotency_key="resume-running",
        ),
    )
    assert resumed.mission.current_state is MissionState.RUNNING

    first = transition(
        make_mission(),
        TransitionRequest(
            event=MissionEvent.START_PLANNING,
            actor_id="developer-1",
            idempotency_key="conflicting-key",
        ),
    )
    with pytest.raises(MissionTransitionError) as error:
        transition(
            first.mission,
            TransitionRequest(
                event=MissionEvent.SUBMIT_PLAN,
                actor_id="developer-1",
                idempotency_key="conflicting-key",
            ),
        )

    assert error.value.code is TransitionErrorCode.IDEMPOTENCY_CONFLICT
