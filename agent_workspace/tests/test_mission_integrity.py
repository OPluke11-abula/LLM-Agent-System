from datetime import datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from agent_workspace.core.mission_contracts import (
    ApprovalGate,
    ApprovalStatus,
    ApprovalType,
    EvidenceRecord,
    EvidenceType,
    ExecutionPlan,
    GateStatus,
    PlanApprovalSubject,
    PlanTask,
    VerificationGate,
    VerificationGateName,
)
from agent_workspace.core.mission_model import Mission, MissionState
from agent_workspace.core.product_contracts import MissionPolicy
from agent_workspace.core.mission_store import MissionStore


def make_plan(*, revision: int = 1, title: str = "Inspect") -> ExecutionPlan:
    return ExecutionPlan(
        plan_id="plan-integrity-1",
        mission_id="mission-integrity-1",
        revision=revision,
        tasks=[PlanTask(task_id="task-1", title=title, order=1)],
    )


def make_mission(*, plan: ExecutionPlan | None = None) -> Mission:
    values = {
        "mission_id": "mission-integrity-1",
        "requirement": "Protect the Mission aggregate.",
        "repository_id": "repo-1",
        "execution_policy": MissionPolicy(),
        "actor_id": "owner-1",
    }
    if plan is not None:
        values.update(
            execution_plan=plan,
            plan_reference=plan.plan_id,
            plan_revision=plan.revision,
        )
    return Mission(**values)


def make_evidence(
    evidence_id: str = "evidence-1",
    *,
    status: GateStatus = GateStatus.PASSED,
    evidence_type: EvidenceType = EvidenceType.TEST,
    task_links: tuple[str, ...] = ("task-1",),
    plan_revision: int | None = 1,
) -> EvidenceRecord:
    timestamp = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return EvidenceRecord(
        evidence_id=evidence_id,
        evidence_type=evidence_type,
        source="pytest",
        operation="python -m pytest",
        started_at=timestamp,
        finished_at=timestamp,
        exit_status=0,
        bounded_output_summary="passed",
        producing_agent="owner-1",
        task_links=task_links,
        plan_revision=plan_revision,
        verification_status=status,
    )


def test_plan_digest_is_deterministic_and_changes_with_content() -> None:
    first = make_plan()
    same = make_plan()
    changed = make_plan(title="Inspect changed")

    assert first.canonical_digest() == same.canonical_digest()
    assert first.canonical_digest() != changed.canonical_digest()


def test_approval_subject_requires_exact_plan_digest() -> None:
    plan = make_plan()
    subject = PlanApprovalSubject(
        plan_id=plan.plan_id,
        plan_revision=plan.revision,
        plan_digest=plan.canonical_digest(),
    )
    assert subject.plan_digest == plan.canonical_digest()


def test_aggregate_rejects_duplicate_evidence_before_store_write(tmp_path: Path) -> None:
    database = tmp_path / "missions.db"
    mission = make_mission(plan=make_plan())

    with MissionStore(database) as store:
        store.create(mission)
        first = mission.add_evidence_record(make_evidence())
        store.save(first, expected_revision=0)

        with pytest.raises(ValueError):
            duplicate = first.add_evidence_record(make_evidence())
            store.save(duplicate, expected_revision=1)

        persisted = store.get(mission.mission_id)

    assert persisted is not None
    assert len(persisted.evidence_records) == 1


def test_verification_rejects_fake_pending_and_incompatible_evidence() -> None:
    mission = make_mission(plan=make_plan())
    with_evidence = mission.add_evidence_record(make_evidence())

    with pytest.raises(ValueError):
        with_evidence.record_verification_gate(
            VerificationGate(
                gate=VerificationGateName.TESTS,
                status=GateStatus.PASSED,
                evidence_refs=("missing",),
            )
        )

    pending = with_evidence.add_evidence_record(
        make_evidence("evidence-pending", status=GateStatus.PENDING)
    )
    with pytest.raises(ValueError):
        pending.record_verification_gate(
            VerificationGate(
                gate=VerificationGateName.TESTS,
                status=GateStatus.PASSED,
                evidence_refs=("evidence-pending",),
            )
        )

    with pytest.raises(ValueError):
        with_evidence.record_verification_gate(
            VerificationGate(
                gate=VerificationGateName.CI,
                status=GateStatus.PASSED,
                evidence_refs=("evidence-1",),
            )
        )

    with pytest.raises(ValueError):
        VerificationGate(
            gate=VerificationGateName.TESTS,
            status=GateStatus.PASSED,
            evidence_refs=(),
        )


def test_verification_retry_replaces_refs_and_preserves_evidence_history() -> None:
    failed = make_evidence("evidence-failed", status=GateStatus.FAILED)
    passed = make_evidence("evidence-passed", status=GateStatus.PASSED)
    mission = make_mission(plan=make_plan()).model_copy(
        update={"required_verification": (VerificationGateName.TESTS,)}
    )
    mission = mission.add_evidence_record(failed).add_evidence_record(passed)

    failed_gate = mission.record_verification_gate(
        VerificationGate(
            gate=VerificationGateName.TESTS,
            status=GateStatus.FAILED,
            evidence_refs=(failed.evidence_id,),
        )
    )
    retried = failed_gate.record_verification_gate(
        VerificationGate(
            gate=VerificationGateName.TESTS,
            status=GateStatus.PASSED,
            evidence_refs=(passed.evidence_id,),
        )
    )

    current_gate = retried.verification_gates[0]
    assert current_gate.status is GateStatus.PASSED
    assert current_gate.evidence_refs == (passed.evidence_id,)
    assert {record.evidence_id for record in retried.evidence_records} == {
        failed.evidence_id,
        passed.evidence_id,
    }
    assert retried.verification_complete() is True


def test_pending_verification_retry_replaces_refs_with_passed_evidence() -> None:
    pending = make_evidence("evidence-pending", status=GateStatus.PENDING)
    passed = make_evidence("evidence-passed", status=GateStatus.PASSED)
    mission = make_mission(plan=make_plan()).model_copy(
        update={"required_verification": (VerificationGateName.TESTS,)}
    )
    mission = mission.add_evidence_record(pending).add_evidence_record(passed)

    pending_gate = mission.record_verification_gate(
        VerificationGate(
            gate=VerificationGateName.TESTS,
            status=GateStatus.PENDING,
            evidence_refs=(pending.evidence_id,),
        )
    )
    retried = pending_gate.record_verification_gate(
        VerificationGate(
            gate=VerificationGateName.TESTS,
            status=GateStatus.PASSED,
            evidence_refs=(passed.evidence_id,),
        )
    )

    assert retried.verification_gates[0].evidence_refs == (passed.evidence_id,)
    assert retried.verification_complete() is True


def test_final_approval_decision_cannot_be_replaced() -> None:
    plan = make_plan()
    subject = PlanApprovalSubject(
        plan_id=plan.plan_id,
        plan_revision=plan.revision,
        plan_digest=plan.canonical_digest(),
    )
    approved = ApprovalGate(
        gate_id="approval-1",
        gate_type=ApprovalType.PLAN,
        subject=subject,
        status=ApprovalStatus.APPROVED,
        actor_id="owner-1",
        decided_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        idempotency_key="approval-key-1",
    )
    mission = make_mission(plan=plan).add_approval_gate(approved)
    rejected = approved.model_copy(update={"gate_id": "approval-2", "status": ApprovalStatus.REJECTED})

    with pytest.raises(ValueError):
        mission.add_approval_gate(rejected)
