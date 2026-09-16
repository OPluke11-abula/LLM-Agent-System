"""State Machine, Event Stream, and Crash Recovery Test Suite (Phase E).

Validates:
1. Rejection of illegal state transitions (terminal state rewinds, skipping verification).
2. State durability across process crashes via SqliteMissionStore.
3. Idempotency conflicts and optimistic concurrency protections.
4. Tamper-evident cryptographic hash chains and Merkle tree verification in AuditLedger.
"""

from datetime import datetime, timezone
from pathlib import Path
import sqlite3
import tempfile
import unittest

from agent_workspace.core.audit_ledger import AuditLedger
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
    MissionEvent,
    MissionState,
    TransitionErrorCode,
    TransitionRequest,
)
from agent_workspace.core.mission_state_machine import (
    MissionStateMachine,
    MissionTransitionError,
)
from agent_workspace.core.mission_store import (
    MissionStore,
    MissionStoreConflictError,
)
from agent_workspace.core.product_contracts import MissionPolicy


class TestStateRecovery(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "missions.db"
        self.ledger_db_path = Path(self.temp_dir.name) / "audit.db"
        self.machine = MissionStateMachine()

    def tearDown(self):
        self.temp_dir.cleanup()

    def _create_base_mission(self, state: MissionState = MissionState.DRAFT) -> Mission:
        return Mission(
            mission_id="mission-recovery-1",
            requirement="Validate durable state recovery",
            repository_id="repo-1",
            execution_policy=MissionPolicy(),
            actor_id="dev-human",
            current_state=state,
        )

    def test_illegal_state_transition_from_terminal_states(self):
        """Terminal states (CLOSED, FAILED, CANCELLED) cannot transition back to active states."""
        terminal_states = [MissionState.CLOSED, MissionState.FAILED, MissionState.CANCELLED]
        for terminal_state in terminal_states:
            with self.subTest(terminal_state=terminal_state):
                mission = self._create_base_mission(state=terminal_state)
                req = TransitionRequest(
                    event=MissionEvent.START_PLANNING,
                    actor_id="dev-human",
                    idempotency_key="key-rewind",
                )
                with self.assertRaises(MissionTransitionError) as ctx:
                    self.machine.transition(mission, req)
                self.assertEqual(ctx.exception.code, TransitionErrorCode.TERMINAL_STATE)

    def test_unapproved_planning_to_running_rejected(self):
        """Transitioning to RUNNING without an approved plan must be rejected."""
        mission = self._create_base_mission(state=MissionState.AWAITING_APPROVAL)
        req = TransitionRequest(
            event=MissionEvent.APPROVE_PLAN,
            actor_id="dev-human",
            idempotency_key="key-no-approval",
        )
        with self.assertRaises(MissionTransitionError) as ctx:
            self.machine.transition(mission, req)
        self.assertIn("approval", str(ctx.exception).lower())

    def test_crash_recovery_sqlite_durability(self):
        """Committed mission state persists through crash/reconnection."""
        plan = ExecutionPlan(
            plan_id="plan-dur-1",
            mission_id="mission-recovery-1",
            revision=1,
            tasks=[PlanTask(task_id="t1", title="reconstruct", order=1)],
        )
        original = Mission(
            mission_id="mission-recovery-1",
            requirement="Ensure ACID durability",
            repository_id="repo-1",
            execution_policy=MissionPolicy(),
            actor_id="dev-human",
            current_state=MissionState.PLANNING,
            execution_plan=plan,
            plan_reference=plan.plan_id,
            plan_revision=plan.revision,
        )

        # 1. Commit to database
        with MissionStore(self.db_path) as store:
            store.create(original)

        # 2. Simulate complete process termination & fresh reload
        with MissionStore(self.db_path) as new_store:
            restored = new_store.get(original.mission_id)
            self.assertIsNotNone(restored)
            self.assertEqual(restored.mission_id, original.mission_id)
            self.assertEqual(restored.current_state, MissionState.PLANNING)
            self.assertEqual(restored.execution_plan.plan_id, "plan-dur-1")

    def test_concurrent_conflict_idempotency(self):
        """Stale revision update is rejected by optimistic concurrency control."""
        original = self._create_base_mission(state=MissionState.DRAFT)
        with MissionStore(self.db_path) as store:
            store.create(original)
            # Valid update: expected_revision=0 -> saved.revision becomes 1
            updated = original.model_copy(update={"requirement": "New requirement"})
            saved = store.save(updated, expected_revision=0, owner_id="dev-human")
            self.assertEqual(saved.revision, 1)

            # Conflicting update with stale expected_revision=0
            with self.assertRaises(MissionStoreConflictError) as ctx:
                store.save(updated, expected_revision=0, owner_id="dev-human")
            self.assertEqual(ctx.exception.code, "stale_revision")

    def test_audit_ledger_merkle_and_hash_chain_tamper_detection(self):
        """AuditLedger cryptographic hash chain detects any modification to past event logs."""
        ledger = AuditLedger(workspace_path=str(self.temp_dir.name))

        # Record sequence of events
        ledger.record_event("STAGE_PLAN", {"step": 1, "actor": "human"})
        ledger.record_event("STAGE_CODE", {"step": 2, "actor": "coder"})
        ledger.record_event("STAGE_VERIFY", {"step": 3, "status": "PASS"})

        # Verify pristine chain integrity
        initial_check = ledger.verify_chain_integrity()
        self.assertTrue(initial_check["valid"])
        self.assertIsNotNone(initial_check["merkle_root"])

        # Inject malicious tampering directly into SQLite database
        conn = sqlite3.connect(str(ledger.db_path))
        conn.execute("UPDATE audit_ledger SET payload = '{\"step\": 2, \"hacked\": true}' WHERE id = 2")
        conn.commit()
        conn.close()

        # Re-verify tampered chain
        tampered_check = ledger.verify_chain_integrity()
        self.assertFalse(tampered_check["valid"])
        self.assertEqual(tampered_check["tampered_id"], 2)
        self.assertEqual(tampered_check["error"], "current_hash mismatch")
