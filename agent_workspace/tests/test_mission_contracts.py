from datetime import datetime, timedelta, timezone

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
    DraftPRApprovalSubject,
    DraftPullRequestDelivery,
    EvidenceRecord,
    EvidenceType,
    ExecutionPlan,
    GateStatus,
    MissionBudgetPolicy,
    MissionUsageSummary,
    PlanTask,
    PlanApprovalSubject,
    serialize_contract,
    ScopeApprovalSubject,
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


def make_plan(*, revision: int = 1) -> ExecutionPlan:
    return ExecutionPlan(
        plan_id="plan-1",
        mission_id="mission-1",
        revision=revision,
        tasks=[PlanTask(task_id="task-1", title="Inspect architecture", order=1)],
    )


def make_mission(
    *,
    state: MissionState = MissionState.DRAFT,
    policy: MissionPolicy | None = None,
    approvals: tuple[ApprovalGate, ...] = (),
    verification_gates: tuple[VerificationGate, ...] = (),
    scope_requests: tuple[ScopeExpansionRequest, ...] = (),
    execution_plan: ExecutionPlan | None = None,
    draft_pr_review_subject: DraftPRApprovalSubject | None = None,
    required_verification: tuple[VerificationGateName, ...] | None = None,
) -> Mission:
    selected_policy = policy or make_policy()
    values = {
        "mission_id": "mission-1",
        "requirement": "Add a PR risk summary.",
        "repository_id": "repo-1",
        "current_state": state,
        "execution_policy": selected_policy,
        "execution_plan": execution_plan,
        "budget_policy": MissionBudgetPolicy(provider_call_limit=64),
        "usage_summary": MissionUsageSummary(),
        "approval_gates": approvals,
        "verification_gates": verification_gates,
        "scope_expansion_requests": scope_requests,
        "actor_id": "developer-1",
        "draft_pr_review_subject": draft_pr_review_subject,
    }
    if required_verification is not None:
        values["required_verification"] = required_verification
    if execution_plan is not None:
        values["plan_reference"] = execution_plan.plan_id
        values["plan_revision"] = execution_plan.revision
    if verification_gates:
        now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        values["evidence_records"] = (
            EvidenceRecord(
                evidence_id="evidence-1",
                evidence_type=EvidenceType.TEST,
                source="pytest",
                operation="python -m pytest",
                started_at=now,
                finished_at=now,
                exit_status=0,
                bounded_output_summary="passed",
                producing_agent="developer-1",
                verification_status=GateStatus.PASSED,
            ),
        )
    return Mission(
        **values,
    )


def approved_gate(gate_type: ApprovalType, gate_id: str) -> ApprovalGate:
    if gate_type is ApprovalType.PLAN:
        subject = PlanApprovalSubject(
            plan_id="plan-1",
            plan_revision=1,
            plan_digest=make_plan().canonical_digest(),
        )
    elif gate_type is ApprovalType.SCOPE_EXPANSION:
        subject = ScopeApprovalSubject(scope_request_id="scope-1")
    else:
        subject = DraftPRApprovalSubject(
            review_id="review-1",
            plan_id="plan-1",
            plan_revision=1,
            branch="feature/p1",
            head_sha="a" * 40,
        )
    return ApprovalGate(
        gate_id=gate_id,
        gate_type=gate_type,
        subject=subject,
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
        execution_plan=make_plan(),
    )

    result = transition(
        mission,
        TransitionRequest(
            event=MissionEvent.APPROVE_PLAN,
            actor_id="developer-1",
            idempotency_key="approve-plan",
            approval_subject=PlanApprovalSubject(
                plan_id="plan-1",
                plan_revision=1,
                plan_digest=make_plan().canonical_digest(),
            ),
        ),
    )

    assert result.mission.current_state is MissionState.RUNNING
    assert result.audit.from_state is MissionState.AWAITING_APPROVAL
    assert result.audit.to_state is MissionState.RUNNING


def test_review_ready_requires_completed_verification_gates() -> None:
    mission = make_mission(
        state=MissionState.VERIFYING,
        required_verification=(VerificationGateName.TESTS,),
    )

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
        make_mission(
            state=MissionState.VERIFYING,
            required_verification=(VerificationGateName.TESTS,),
            verification_gates=(passed_verification(),),
        ),
        TransitionRequest(
            event=MissionEvent.COMPLETE_VERIFICATION,
            actor_id="developer-1",
            idempotency_key="complete-verification-approved",
        ),
    )

    assert ready.mission.current_state is MissionState.REVIEW_READY


def test_running_mission_rejects_begin_verification_until_required_gates_resolve() -> None:
    mission = make_mission(
        state=MissionState.RUNNING,
        required_verification=(VerificationGateName.TESTS,),
    )
    machine = MissionStateMachine()

    capabilities = machine.capabilities(mission)
    with pytest.raises(MissionTransitionError) as error:
        machine.transition(
            mission,
            TransitionRequest(
                event=MissionEvent.BEGIN_VERIFICATION,
                actor_id="developer-1",
                idempotency_key="begin-incomplete-verification",
            ),
        )

    assert error.value.code is TransitionErrorCode.VERIFICATION_REQUIRED
    assert capabilities.current_state is MissionState.RUNNING
    assert capabilities.revision == mission.revision
    assert MissionEvent.BEGIN_VERIFICATION not in capabilities.allowed_events
    assert capabilities.blocked_reason == TransitionErrorCode.VERIFICATION_REQUIRED.value


def test_running_mission_begins_verification_after_passed_gate_resolves() -> None:
    mission = make_mission(
        state=MissionState.RUNNING,
        required_verification=(VerificationGateName.TESTS,),
        verification_gates=(passed_verification(),),
    )
    machine = MissionStateMachine()

    capabilities = machine.capabilities(mission)
    result = machine.transition(
        mission,
        TransitionRequest(
            event=MissionEvent.BEGIN_VERIFICATION,
            actor_id="developer-1",
            idempotency_key="begin-complete-verification",
        ),
    )

    assert MissionEvent.BEGIN_VERIFICATION in capabilities.allowed_events
    assert result.mission.current_state is MissionState.VERIFYING


def test_not_applicable_gate_resolves_verification_without_pass_claim() -> None:
    mission = make_mission(
        state=MissionState.RUNNING,
        required_verification=(VerificationGateName.TESTS,),
        verification_gates=(
            VerificationGate(gate=VerificationGateName.TESTS, status=GateStatus.NOT_APPLICABLE),
        ),
    ).model_copy(update={"evidence_records": ()})

    capabilities = MissionStateMachine().capabilities(mission)

    assert MissionEvent.BEGIN_VERIFICATION in capabilities.allowed_events
    assert capabilities.verification_incomplete is False


def test_draft_pr_requires_permission_and_explicit_approval() -> None:
    mission = make_mission(
        state=MissionState.REVIEW_READY,
        policy=make_policy(draft_pr_permission=True),
        verification_gates=(passed_verification(),),
        draft_pr_review_subject=approved_gate(ApprovalType.DRAFT_PR, "draft-pr-gate").subject,
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
            approval_subject=approved_gate(ApprovalType.DRAFT_PR, "draft-pr-gate").subject,
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
                approval_subject=ScopeApprovalSubject(scope_request_id="scope-1"),
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
                ),
                "approval_gates": (approved_gate(ApprovalType.SCOPE_EXPANSION, "scope-gate"),),
            }
        ),
        TransitionRequest(
            event=MissionEvent.APPROVE_SCOPE,
            actor_id="developer-1",
            idempotency_key="approve-scope-approved",
            approval_subject=ScopeApprovalSubject(scope_request_id="scope-1"),
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
        subject=ScopeApprovalSubject(scope_request_id="scope-1"),
        idempotency_key="approval-request-1",
    )

    assert request.decision is None
    assert request.model_dump(mode="json")["decision_type"] == "scope_expansion"


def test_every_declared_transition_is_executable() -> None:
    for (state, event), expected_state in _LEGAL_TRANSITIONS.items():
        mission = make_mission(state=state, verification_gates=(passed_verification(),))
        subject = None
        if event is MissionEvent.APPROVE_PLAN:
            mission = mission.model_copy(
                update={
                    "execution_plan": make_plan(),
                    "approval_gates": (approved_gate(ApprovalType.PLAN, "plan-gate"),),
                }
            )
            subject = PlanApprovalSubject(
                plan_id="plan-1",
                plan_revision=1,
                plan_digest=make_plan().canonical_digest(),
            )
        elif event is MissionEvent.BEGIN_VERIFICATION:
            mission = mission.model_copy(
                update={
                    "required_verification": (VerificationGateName.TESTS,),
                    "verification_gates": (passed_verification(),),
                }
            )
        elif event is MissionEvent.COMPLETE_VERIFICATION:
            mission = mission.model_copy(
                update={
                    "required_verification": (VerificationGateName.TESTS,),
                    "verification_gates": (passed_verification(),),
                }
            )
        elif event is MissionEvent.CREATE_DRAFT_PR:
            subject = approved_gate(ApprovalType.DRAFT_PR, "draft-pr-gate").subject
            mission = mission.model_copy(
                update={
                    "draft_pr_review_subject": subject,
                    "approval_gates": (approved_gate(ApprovalType.DRAFT_PR, "draft-pr-gate"),),
                }
            )
        elif event is MissionEvent.APPROVE_SCOPE:
            subject = ScopeApprovalSubject(scope_request_id="scope-1")
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
                    ),
                    "approval_gates": (approved_gate(ApprovalType.SCOPE_EXPANSION, "scope-gate"),),
                }
            )

        result = transition(
            mission,
            TransitionRequest(
                event=event,
                actor_id="developer-1",
                idempotency_key=f"legal-{state.value}-{event.value}",
                approval_subject=subject,
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


def test_default_mission_requires_complete_developer_beta_verification() -> None:
    mission = make_mission(
        state=MissionState.VERIFYING,
        verification_gates=(passed_verification(),),
    )

    with pytest.raises(MissionTransitionError) as error:
        transition(
            mission,
            TransitionRequest(
                event=MissionEvent.COMPLETE_VERIFICATION,
                actor_id="developer-1",
                idempotency_key="complete-tests-only",
            ),
        )

    assert error.value.code is TransitionErrorCode.VERIFICATION_REQUIRED


def test_execution_plan_rejects_duplicate_order_dependency_cycle_and_bad_estimate() -> None:
    task_one = PlanTask(task_id="task-1", title="One", order=1)
    task_two = PlanTask(
        task_id="task-2",
        title="Two",
        order=1,
        dependencies=["task-1"],
        estimated_provider_calls_min=1,
        estimated_provider_calls_max=2,
    )

    with pytest.raises(ValidationError):
        ExecutionPlan(
            plan_id="plan-1",
            mission_id="mission-1",
            tasks=[task_one, task_two],
        )

    cyclic_one = task_one.model_copy(update={"dependencies": ["task-2"]})
    cyclic_two = task_two.model_copy(
        update={
            "order": 2,
            "estimated_provider_calls_min": 1,
            "estimated_provider_calls_max": 2,
            "dependencies": ["task-1"],
        }
    )
    with pytest.raises(ValidationError):
        ExecutionPlan(
            plan_id="plan-1",
            mission_id="mission-1",
            tasks=[cyclic_one, cyclic_two],
        )

    with pytest.raises(ValidationError):
        PlanTask(
            task_id="bad-estimate",
            title="Bad estimate",
            order=1,
            estimated_provider_calls_min=3,
            estimated_provider_calls_max=2,
        )


def test_pending_approval_cannot_claim_decision_metadata() -> None:
    with pytest.raises(ValidationError):
        ApprovalGate(
            gate_id="pending-gate",
            gate_type=ApprovalType.PLAN,
            actor_id="developer-1",
            idempotency_key="pending-gate-key",
        )


def test_mission_policy_does_not_duplicate_scope_permissions() -> None:
    with pytest.raises(ValidationError):
        MissionPolicy(allow_database_changes=True)

    with pytest.raises(ValidationError):
        MissionPolicy(allow_ci_changes=True)


def test_transition_clock_and_revision_are_deterministic() -> None:
    first_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
    second_time = first_time + timedelta(seconds=1)
    times = iter((first_time, second_time))
    machine = MissionStateMachine(clock=lambda: next(times))

    result = machine.transition(
        make_mission(),
        TransitionRequest(
            event=MissionEvent.START_PLANNING,
            actor_id="developer-1",
            idempotency_key="clocked-start",
        ),
    )

    assert result.mission.revision == 1
    assert result.audit.occurred_at == first_time


def test_stale_plan_approval_cannot_approve_a_new_plan_revision() -> None:
    mission = make_mission(
        state=MissionState.AWAITING_APPROVAL,
        execution_plan=make_plan(revision=2),
        approvals=(approved_gate(ApprovalType.PLAN, "stale-plan-gate"),),
    )

    with pytest.raises(MissionTransitionError) as error:
        transition(
            mission,
            TransitionRequest(
                event=MissionEvent.APPROVE_PLAN,
                actor_id="developer-1",
                idempotency_key="stale-plan-approval",
                approval_subject=PlanApprovalSubject(
                    plan_id="plan-1",
                    plan_revision=1,
                    plan_digest=make_plan().canonical_digest(),
                ),
            ),
        )

    assert error.value.code is TransitionErrorCode.APPROVAL_SUBJECT_MISMATCH


def test_scope_approval_cannot_unblock_an_unrelated_scope_request() -> None:
    mission = make_mission(
        state=MissionState.SCOPE_BLOCKED,
        scope_requests=(
            ScopeExpansionRequest(
                request_id="scope-2",
                mission_id="mission-1",
                requested_paths=["docs"],
                reason="Documentation is required.",
                impact="Adds documentation scope.",
                risk=RiskLevel.LOW,
            ),
        ),
        approvals=(approved_gate(ApprovalType.SCOPE_EXPANSION, "scope-1-gate"),),
    )

    with pytest.raises(MissionTransitionError) as error:
        transition(
            mission,
            TransitionRequest(
                event=MissionEvent.APPROVE_SCOPE,
                actor_id="developer-1",
                idempotency_key="wrong-scope-approval",
                approval_subject=ScopeApprovalSubject(scope_request_id="scope-1"),
            ),
        )

    assert error.value.code is TransitionErrorCode.SCOPE_DECISION_REQUIRED


def test_draft_pr_approval_cannot_be_reused_after_head_changes() -> None:
    reviewed = approved_gate(ApprovalType.DRAFT_PR, "draft-review-gate").subject
    changed = DraftPRApprovalSubject(
        review_id="review-2",
        plan_id="plan-1",
        plan_revision=1,
        branch="feature/p1",
        head_sha="b" * 40,
    )
    mission = make_mission(
        state=MissionState.REVIEW_READY,
        draft_pr_review_subject=changed,
        approvals=(approved_gate(ApprovalType.DRAFT_PR, "draft-review-gate"),),
    )

    with pytest.raises(MissionTransitionError) as error:
        transition(
            mission,
            TransitionRequest(
                event=MissionEvent.CREATE_DRAFT_PR,
                actor_id="developer-1",
                idempotency_key="changed-head",
                approval_subject=reviewed,
            ),
        )

    assert error.value.code is TransitionErrorCode.DRAFT_PR_APPROVAL_REQUIRED


def test_duplicate_verification_gates_and_invalid_identifiers_are_rejected() -> None:
    with pytest.raises(ValidationError):
        make_mission(
            verification_gates=(passed_verification(), passed_verification()),
        )

    with pytest.raises(ValidationError):
        RepositoryProfile(repository_id="")

    with pytest.raises(ValidationError):
        PlanTask(task_id="task with spaces", title="Invalid", order=1)


def test_approved_plan_revision_is_bound_on_round_trip() -> None:
    plan = make_plan().model_copy(
        update={"approval_status": ApprovalStatus.APPROVED, "approved_revision": 1}
    )
    serialized = plan.model_dump(mode="json")

    with pytest.raises(ValidationError):
        ExecutionPlan.model_validate({**serialized, "revision": 2})


def test_idempotency_key_cannot_reauthorize_a_different_subject() -> None:
    mission = make_mission(
        state=MissionState.AWAITING_APPROVAL,
        execution_plan=make_plan(),
        approvals=(approved_gate(ApprovalType.PLAN, "plan-gate"),),
    )
    subject = PlanApprovalSubject(
        plan_id="plan-1",
        plan_revision=1,
        plan_digest=make_plan().canonical_digest(),
    )
    request = TransitionRequest(
        event=MissionEvent.APPROVE_PLAN,
        actor_id="developer-1",
        idempotency_key="subject-bound-key",
        approval_subject=subject,
    )
    first = transition(mission, request)

    with pytest.raises(MissionTransitionError) as error:
        transition(
            first.mission,
            request.model_copy(
                update={
                    "approval_subject": PlanApprovalSubject(
                        plan_id="plan-1",
                        plan_revision=2,
                        plan_digest=make_plan(revision=2).canonical_digest(),
                    )
                }
            ),
        )

    assert error.value.code is TransitionErrorCode.IDEMPOTENCY_CONFLICT
