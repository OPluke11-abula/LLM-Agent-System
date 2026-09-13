"""Unit and end-to-end integration tests for Phase 2-D (RuntimeEvents, Feedback & Recovery)."""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from agent_workspace.core.agent_executor import AgentExecutor
from agent_workspace.core.git_worktree import GitWorktreeManager
from agent_workspace.core.pipeline.manager import CodingPipelineManager
from agent_workspace.core.pipeline.models import (
    CodingTaskRequest,
    DraftPRPayload,
    PipelineStage,
    ScopedMutationPlan,
    VerificationReceipt,
    VerificationStatus,
)
from agent_workspace.core.repository import RepositoryInspector
from agent_workspace.core.runtime_events import (
    CheckpointCorruptError,
    CheckpointRecoveryManager,
    ExecutionCheckpoint,
    GitHubDraftPRPublisher,
    IndependentReviewVerifier,
    LiveFeedbackRunner,
    RuntimeEventType,
    RuntimeEventsLedger,
)


class TestRuntimeEventsLedgerP2D(unittest.TestCase):
    """Verifies cryptographic chaining and Merkle tree root computation."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="las_test_events_")
        self.ledger = RuntimeEventsLedger(workspace_path=self.temp_dir)

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_record_and_chain_events(self):
        ev1 = self.ledger.record_event("TASK-100", RuntimeEventType.TASK_STARTED, {"goal": "build"})
        ev2 = self.ledger.record_event("TASK-100", RuntimeEventType.TOOL_INVOKED, {"tool": "filesystem.read"})
        ev3 = self.ledger.record_event("TASK-100", RuntimeEventType.TASK_COMPLETED, {"result": "success"})

        self.assertEqual(ev1.previous_hash, "0" * 64)
        self.assertEqual(ev2.previous_hash, ev1.current_hash)
        self.assertEqual(ev3.previous_hash, ev2.current_hash)

        # Verify integrity
        self.assertTrue(self.ledger.verify_chain_integrity("TASK-100"))

        # Merkle root computation
        root = self.ledger.calculate_merkle_root("TASK-100")
        self.assertIsNotNone(root)
        self.assertEqual(len(root), 64)


class TestLiveFeedbackRunnerP2D(unittest.TestCase):
    """Verifies test ladder execution and diagnostic failure extraction."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="las_test_runner_")
        self.runner = LiveFeedbackRunner(timeout_seconds=10.0)

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_run_verification_ladder_success(self):
        receipts = self.runner.run_verification_ladder(
            self.temp_dir,
            [
                'python -c "print(\'step 1 ok\')"',
                'python -c "print(\'step 2 ok\')"',
            ],
        )
        self.assertEqual(len(receipts), 2)
        self.assertEqual(receipts[0].status, VerificationStatus.PASS)
        self.assertEqual(receipts[1].status, VerificationStatus.PASS)

    def test_run_verification_ladder_failure_and_diagnostics(self):
        receipts = self.runner.run_verification_ladder(
            self.temp_dir,
            [
                'python -c "raise AssertionError(\'Expected 42 but got 0\')"',
                'python -c "print(\'should not run due to fail-fast\')"',
            ],
        )
        self.assertEqual(len(receipts), 1)
        self.assertEqual(receipts[0].status, VerificationStatus.FAIL)
        self.assertIn("AssertionError", receipts[0].stderr_snippet)

        diagnostics = LiveFeedbackRunner.extract_failure_evidence(receipts)
        self.assertEqual(len(diagnostics), 1)
        self.assertIn("AssertionError: Expected 42 but got 0", diagnostics[0])


class TestIndependentReviewVerifierP2D(unittest.TestCase):
    """Verifies review freshness invariant."""

    def test_fresh_review_passes(self):
        fresh, msg = IndependentReviewVerifier.verify_review_freshness("abc12345", "abc12345")
        self.assertTrue(fresh)
        self.assertIn("Review is fresh", msg)

    def test_stale_review_rejected(self):
        fresh, msg = IndependentReviewVerifier.verify_review_freshness("old_commit_111", "new_commit_222")
        self.assertFalse(fresh)
        self.assertIn("STALE_REVIEW", msg)


class TestCheckpointRecoveryManagerP2D(unittest.TestCase):
    """Verifies state serialization, checksum checks, and corruption handling."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="las_test_cp_")

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_checkpoint_save_and_load(self):
        cp = ExecutionCheckpoint(
            checkpoint_id="cp-001",
            task_id="TASK-CP",
            stage=PipelineStage.ISOLATED_MUTATION,
            worktree_path=self.temp_dir,
            head_commit="commit_abc_123",
            attempt_turn=2,
            stage_history=[{"stage": "INTAKE"}],
        )
        file_path = CheckpointRecoveryManager.save_checkpoint(self.temp_dir, cp)
        self.assertTrue(file_path.exists())

        loaded = CheckpointRecoveryManager.load_checkpoint(str(file_path))
        self.assertEqual(loaded.checkpoint_id, "cp-001")
        self.assertEqual(loaded.attempt_turn, 2)

    def test_checkpoint_corrupt_raises(self):
        cp = ExecutionCheckpoint(
            checkpoint_id="cp-corrupt",
            task_id="TASK-CORRUPT",
            stage=PipelineStage.ISOLATED_MUTATION,
            worktree_path=self.temp_dir,
            head_commit="commit_abc_123",
            attempt_turn=1,
        )
        file_path = CheckpointRecoveryManager.save_checkpoint(self.temp_dir, cp)

        # Manually alter the file content without updating checksum
        content = file_path.read_text(encoding="utf-8")
        corrupted = content.replace("TASK-CORRUPT", "TAMPERED_TASK")
        file_path.write_text(corrupted, encoding="utf-8")

        with self.assertRaises(CheckpointCorruptError):
            CheckpointRecoveryManager.load_checkpoint(str(file_path))


class TestGitHubDraftPRPublisherP2D(unittest.TestCase):
    """Verifies draft PR publishing and local patch bundle fallback."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="las_test_pub_")

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_publish_local_patch_fallback(self):
        publisher = GitHubDraftPRPublisher()
        payload = DraftPRPayload(
            title="feat(core): add recovery manager",
            body="## Summary\nAdded checkpoint recovery.",
            head_branch="feat/recovery-mgr",
            base_branch="main",
            commit_hash="deadbeef12345678",
            changed_files=["agent_workspace/core/runtime_events.py"],
            merkle_root="a" * 64,
        )

        url = publisher.publish_draft_pr(payload, self.temp_dir)
        self.assertTrue(url.startswith("file:///"))
        self.assertIn(".patch.md", url)

        patch_file = Path(self.temp_dir) / ".agent" / "patches" / "feat_recovery-mgr.patch.md"
        self.assertTrue(patch_file.is_file())
        content = patch_file.read_text(encoding="utf-8")
        self.assertIn("feat(core): add recovery manager", content)
        self.assertIn("a" * 64, content)


class TestFullPipelineEndToEndIntegrationP2D(unittest.TestCase):
    """
    Full integration test verifying the complete unified pipeline:
    P2-A (Repo & Worktree) + P2-B (TaskEnvironment) + P2-C (AgentExecutor) + P2-D (Feedback & PR).
    """

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="las_e2e_repo_")
        # 1. Initialize git repo
        subprocess.run(["git", "init", "-b", "main"], cwd=self.temp_dir, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "E2E Test Agent"], cwd=self.temp_dir, check=True)
        subprocess.run(["git", "config", "user.email", "agent@e2e.test"], cwd=self.temp_dir, check=True)

        # 2. Add an initial source file & gitignore
        core_dir = os.path.join(self.temp_dir, "agent_workspace", "core")
        os.makedirs(core_dir, exist_ok=True)
        self.core_file = os.path.join(core_dir, "calc.py")
        with open(self.core_file, "w", encoding="utf-8") as f:
            f.write("def add(a, b):\n    return a + b\n")

        gitignore_file = os.path.join(self.temp_dir, ".gitignore")
        with open(gitignore_file, "w", encoding="utf-8") as f:
            f.write(".agent/patches/\n")

        subprocess.run(["git", "add", "."], cwd=self.temp_dir, check=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=self.temp_dir, check=True)

        # 3. Create worktree manager & repository inspector
        self.wt_manager = GitWorktreeManager()
        self.inspector = RepositoryInspector()

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_complete_autonomous_pipeline_run(self):
        # 1. Take snapshot for CanonicalPreservationReceipt
        preservation_receipt = self.inspector.generate_preservation_receipt(self.temp_dir)
        self.assertTrue(preservation_receipt.is_preserved)

        # 2. Assemble unified pipeline manager
        executor = AgentExecutor()
        feedback_runner = LiveFeedbackRunner()
        publisher = GitHubDraftPRPublisher()

        manager = CodingPipelineManager(
            workspace_path=self.temp_dir,
            worktree_manager=self.wt_manager,
            scoped_executor=executor,
            verification_runner=feedback_runner,
            draft_pr_publisher=publisher,
        )

        # 3. Formulate CodingTaskRequest
        req = CodingTaskRequest(
            task_id="TASK-E2E-P2-FINAL",
            repository_path=self.temp_dir,
            requirement_prompt="Add multiply function to calc.py",
            target_branch="feat/las-calc-multiply",
            base_branch="main",
            inspected_files=["agent_workspace/core/calc.py"],
            target_files=["agent_workspace/core/calc.py"],
            allowed_roles=["DOMAIN_LOGIC_AGENT"],
        )

        # 4. Formulate ScopedMutationPlan with human approval
        plan = ScopedMutationPlan(
            task_id="TASK-E2E-P2-FINAL",
            plan_summary="Implement multiply(a, b) in calc.py",
            target_files=["agent_workspace/core/calc.py"],
            assigned_role="DOMAIN_LOGIC_AGENT",
            human_approved=True,
            approval_token="PO_LUKE_TOKEN",
            test_strategy=['python -c "import sys; sys.exit(0)"'],
        )

        # 5. Execute unified pipeline
        result = manager.execute_pipeline(req.task_id, req, plan)

        # 6. Verify result
        self.assertEqual(result.status, VerificationStatus.PASS)
        self.assertEqual(result.current_stage, PipelineStage.COMPLETED)
        self.assertIsNotNone(result.pr_payload)
        self.assertTrue(result.pr_payload.pr_url.startswith("file:///"))
        self.assertEqual(len(result.receipts), 1)
        self.assertEqual(result.receipts[0].status, VerificationStatus.PASS)

        # 7. Cleanup worktree
        if result.worktree_config:
            self.wt_manager.cleanup_worktree(result.worktree_config)

        # 8. Verify canonical host checkout preservation guarantee
        verified_preservation = self.inspector.verify_preservation(preservation_receipt)
        self.assertTrue(verified_preservation.is_preserved)


if __name__ == "__main__":
    unittest.main()
