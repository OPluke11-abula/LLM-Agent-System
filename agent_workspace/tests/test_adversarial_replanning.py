"""Scenario G: Adversarial Replanning & Plan Drift Test Suite.

Validates that:
1. Silent mutation of execution plans without incrementing revision is blocked.
2. Plan revision mismatches or tampered digests reject approval transitions.
3. Adding target files or expanding scope beyond the approved plan forces re-entry into the Stop-and-Wait Architecture Gate.
"""

from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest

from agent_workspace.core.mission_contracts import (
    ApprovalGate,
    ApprovalStatus,
    ApprovalType,
    ExecutionPlan,
    PlanApprovalSubject,
    PlanTask,
)
from agent_workspace.core.mission_model import (
    Mission,
    MissionAggregateError,
    MissionEvent,
    MissionState,
    TransitionErrorCode,
    TransitionRequest,
)
from agent_workspace.core.mission_state_machine import (
    MissionStateMachine,
    MissionTransitionError,
)
from agent_workspace.core.pipeline.manager import CodingPipelineManager
from agent_workspace.core.pipeline.models import (
    CodingTaskRequest,
    ScopedMutationPlan,
    VerificationStatus,
)
from agent_workspace.core.product_contracts import MissionPolicy


class TestAdversarialReplanning(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name)
        (self.workspace / "src").mkdir(parents=True)
        (self.workspace / "src" / "core.py").write_text("def core(): pass\n", encoding="utf-8")
        (self.workspace / "src" / "extra.py").write_text("def extra(): pass\n", encoding="utf-8")
        self.machine = MissionStateMachine()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_tampered_plan_digest_rejected_on_approval(self):
        """Transitioning to RUNNING with a forged or tampered plan digest fails."""
        original_plan = ExecutionPlan(
            plan_id="plan-drift-1",
            mission_id="mission-drift-1",
            revision=1,
            tasks=[PlanTask(task_id="t1", title="initial plan", order=1)],
        )
        mission = Mission(
            mission_id="mission-drift-1",
            requirement="Verify plan integrity",
            repository_id="repo-1",
            execution_policy=MissionPolicy(),
            actor_id="agent-planner",
            current_state=MissionState.AWAITING_APPROVAL,
            execution_plan=original_plan,
            plan_reference=original_plan.plan_id,
            plan_revision=original_plan.revision,
        )

        # Forged approval subject with invalid 64-character hex digest
        forged_subject = PlanApprovalSubject(
            plan_id="plan-drift-1",
            plan_revision=1,
            plan_digest="0" * 64,
        )
        req = TransitionRequest(
            event=MissionEvent.APPROVE_PLAN,
            actor_id="human-po",
            approval_subject=forged_subject,
            idempotency_key="key-forged-digest",
        )

        with self.assertRaises(MissionTransitionError) as ctx:
            self.machine.transition(mission, req)
        self.assertEqual(ctx.exception.code, TransitionErrorCode.APPROVAL_SUBJECT_MISMATCH)
        self.assertIn("stale or unrelated", str(ctx.exception).lower())

    def test_plan_revision_mismatch_rejected(self):
        """Approving a stale plan revision is rejected."""
        plan_v2 = ExecutionPlan(
            plan_id="plan-drift-2",
            mission_id="mission-drift-2",
            revision=2,
            tasks=[PlanTask(task_id="t1", title="revised plan", order=1)],
        )
        mission = Mission(
            mission_id="mission-drift-2",
            requirement="Verify plan revision consistency",
            repository_id="repo-1",
            execution_policy=MissionPolicy(),
            actor_id="agent-planner",
            current_state=MissionState.AWAITING_APPROVAL,
            execution_plan=plan_v2,
            plan_reference=plan_v2.plan_id,
            plan_revision=2,
        )

        # Approval referencing stale revision 1
        stale_subject = PlanApprovalSubject(
            plan_id="plan-drift-2",
            plan_revision=1,
            plan_digest=plan_v2.canonical_digest(),
        )
        req = TransitionRequest(
            event=MissionEvent.APPROVE_PLAN,
            actor_id="human-po",
            approval_subject=stale_subject,
            idempotency_key="key-stale-rev",
        )

        with self.assertRaises(MissionTransitionError) as ctx:
            self.machine.transition(mission, req)
        self.assertEqual(ctx.exception.code, TransitionErrorCode.APPROVAL_SUBJECT_MISMATCH)
        self.assertIn("stale or unrelated", str(ctx.exception).lower())

    def test_scope_drift_triggers_stop_and_wait_gate(self):
        """Pipeline blocks unapproved file additions during mutation phase."""
        mgr = CodingPipelineManager(workspace_path=str(self.workspace))
        req = CodingTaskRequest(
            task_id="TASK-SCOPE-DRIFT",
            repository_path=str(self.workspace),
            requirement_prompt="Modify core only",
            target_branch="feat/drift",
            inspected_files=[str(self.workspace / "src" / "core.py")],
            target_files=["src/core.py"],
            allowed_roles=["DOMAIN_LOGIC_AGENT"],
        )
        mgr.start_pipeline(req)

        # Attempt to submit plan targeting extra.py which was NOT in inspected files
        drift_plan = ScopedMutationPlan(
            task_id="TASK-SCOPE-DRIFT",
            plan_summary="Plan attempting silent file drift",
            target_files=["src/core.py", "src/extra.py"],  # extra.py is uninspected scope drift
            assigned_role="DOMAIN_LOGIC_AGENT",
            human_approved=False,  # Unapproved!
            approval_token=None,
            test_strategy=["pytest"],
        )
        res = mgr.submit_plan("TASK-SCOPE-DRIFT", drift_plan)
        self.assertEqual(res.status, VerificationStatus.BLOCKED)
        self.assertIn("stop-and-wait", res.error_message.lower())


if __name__ == "__main__":
    unittest.main()
