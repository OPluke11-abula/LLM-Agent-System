"""Unit tests for LAS Autonomous Coding Pipeline Phase 1 (P1).

Uses Python standard library unittest (compatible with both `python -m unittest` and `pytest`).
Validates:
- Pydantic models contract & validation
- Anti-Summary Invariant preflight check
- Stop-and-Wait Architecture Gate (Human sign-off requirement)
- Role Scope boundary enforcement (ROLE_SCOPE_RESTRICTIONS)
- Full mocked pipeline execution & Draft PR receipt generation
- Verification failure handling (no false Draft PR generation)
- State machine transition history tracking
"""

import os
import tempfile
import unittest
from pathlib import Path

from agent_workspace.core.pipeline.models import (
    PipelineStage,
    VerificationStatus,
    CodingTaskRequest,
    WorktreeSessionConfig,
    ScopedMutationPlan,
    VerificationReceipt,
    DraftPRPayload,
    CodingPipelineResult,
)
from agent_workspace.core.pipeline.contracts import (
    IWorktreeManager,
    IScopedExecutor,
    IVerificationRunner,
    IDraftPRPublisher,
)
from agent_workspace.core.pipeline.manager import (
    CodingPipelineManager,
    PipelineError,
)
from agent_workspace.core.audit_ledger import AuditLedger


class MockWorktreeManager(IWorktreeManager):
    """Mock implementation of IWorktreeManager for testing."""
    def __init__(self):
        self.created_worktrees = []
        self.committed_messages = []

    def create_worktree(self, repo_path: str, branch_name: str, base_ref: str = "main") -> WorktreeSessionConfig:
        config = WorktreeSessionConfig(
            session_id=f"wt-{branch_name}",
            worktree_path=os.path.join(repo_path, ".worktrees", branch_name),
            branch_name=branch_name,
            base_commit="abc1234",
            is_isolated=True,
        )
        self.created_worktrees.append(config)
        return config

    def cleanup_worktree(self, session: WorktreeSessionConfig, remove_branch_on_abort: bool = False) -> bool:
        return True

    def get_diff(self, session: WorktreeSessionConfig) -> str:
        return "diff --git a/test.py b/test.py\n+ # Added feature"

    def commit_changes(self, session: WorktreeSessionConfig, commit_message: str) -> str:
        self.committed_messages.append(commit_message)
        return "commit-sha-98765"


class MockScopedExecutor(IScopedExecutor):
    """Mock implementation of IScopedExecutor."""
    def __init__(self):
        self.executed_plans = []

    def execute_plan(self, session: WorktreeSessionConfig, plan: ScopedMutationPlan):
        self.executed_plans.append(plan)
        return {"status": "success", "modified_files": plan.target_files}

    def validate_scope_compliance(self, role: str, target_files: list[str]):
        return True, None


class MockVerificationRunner(IVerificationRunner):
    """Mock implementation of IVerificationRunner."""
    def __init__(self, should_pass: bool = True):
        self.should_pass = should_pass

    def run_verification_ladder(self, worktree_path: str, test_strategy: list[str]) -> list[VerificationReceipt]:
        status = VerificationStatus.PASS if self.should_pass else VerificationStatus.FAIL
        exit_code = 0 if self.should_pass else 1
        return [
            VerificationReceipt(
                step_name="Step 1: Python compileall",
                command="python -m compileall .",
                exit_code=exit_code,
                status=status,
                stdout_snippet="Compiled successfully" if self.should_pass else "Syntax error in file",
                duration_ms=120,
            ),
            VerificationReceipt(
                step_name="Step 2: Unit Tests",
                command="pytest tests/",
                exit_code=exit_code,
                status=status,
                stdout_snippet="10 passed" if self.should_pass else "1 failed, 9 passed",
                duration_ms=450,
            ),
        ]


class MockDraftPRPublisher(IDraftPRPublisher):
    """Mock implementation of IDraftPRPublisher."""
    def __init__(self):
        self.published_prs = []

    def publish_draft_pr(self, payload: DraftPRPayload, repo_path: str) -> str:
        self.published_prs.append(payload)
        return f"https://github.com/mock-repo/pull/{len(self.published_prs)}"


class TestCodingPipelineP1(unittest.TestCase):
    """Test suite for Autonomous Coding Pipeline Phase 1."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name)
        (self.workspace / "agent_workspace").mkdir(parents=True)
        (self.workspace / "agent_workspace" / "core.py").write_text("# core logic")
        (self.workspace / "viewer").mkdir(parents=True)
        (self.workspace / "viewer" / "app.tsx").write_text("// frontend app")
        self.workspace_path = str(self.workspace)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_models_contract(self):
        """Verify serialization and validation constraints of Pydantic models."""
        req = CodingTaskRequest(
            task_id="TASK-001",
            repository_path=self.workspace_path,
            requirement_prompt="Add user auth endpoint",
            target_branch="feat/auth",
            inspected_files=[str(self.workspace / "agent_workspace" / "core.py")],
            target_files=["agent_workspace/api.py"],
        )
        self.assertEqual(req.task_id, "TASK-001")
        self.assertEqual(req.max_turns, 3)

        receipt = VerificationReceipt(
            step_name="compile",
            command="compileall",
            exit_code=0,
            status=VerificationStatus.PASS,
        )
        self.assertEqual(receipt.status, VerificationStatus.PASS)

    def test_anti_summary_preflight_blocks_empty(self):
        """Anti-Summary Invariant: Missing inspected_files must be BLOCKED."""
        mgr = CodingPipelineManager(workspace_path=self.workspace_path)
        req = CodingTaskRequest(
            task_id="TASK-EMPTY",
            repository_path=self.workspace_path,
            requirement_prompt="Fix bug without inspecting code",
            target_branch="feat/quick-fix",
            inspected_files=[],  # Empty! Violates Anti-Summary
            target_files=["agent_workspace/core.py"],
        )
        res = mgr.start_pipeline(req)
        self.assertEqual(res.status, VerificationStatus.BLOCKED)
        self.assertEqual(res.current_stage, PipelineStage.FAILED)
        self.assertIn("Anti-Summary violation", res.error_message or "")

    def test_role_scope_boundary_enforcement(self):
        """UnifiedPolicyGate integration: UI role cannot edit backend files and vice versa."""
        mgr = CodingPipelineManager(workspace_path=self.workspace_path)

        # 1. UI_UX_AGENT attempting to modify backend
        req_ui = CodingTaskRequest(
            task_id="TASK-UI-VIOLATE",
            repository_path=self.workspace_path,
            requirement_prompt="Update backend schema",
            target_branch="feat/ui",
            inspected_files=[str(self.workspace / "viewer" / "app.tsx")],
            target_files=["agent_workspace/core.py"],
            allowed_roles=["UI_UX_AGENT"],
        )
        res_ui = mgr.start_pipeline(req_ui)
        self.assertEqual(res_ui.status, VerificationStatus.BLOCKED)
        self.assertIn("strictly prohibited from modifying backend", res_ui.error_message or "")

        # 2. BACKEND_INFRA_AGENT attempting to modify frontend
        req_backend = CodingTaskRequest(
            task_id="TASK-BE-VIOLATE",
            repository_path=self.workspace_path,
            requirement_prompt="Change frontend button color",
            target_branch="feat/btn",
            inspected_files=[str(self.workspace / "agent_workspace" / "core.py")],
            target_files=["viewer/app.tsx"],
            allowed_roles=["BACKEND_INFRA_AGENT"],
        )
        res_backend = mgr.start_pipeline(req_backend)
        self.assertEqual(res_backend.status, VerificationStatus.BLOCKED)
        self.assertIn("strictly prohibited from modifying presentation UI", res_backend.error_message or "")

        # 3. Read-only role attempting mutation
        is_valid, err = mgr.validate_role_scope("SECURITY_AUDIT_AGENT", ["any_file.py"])
        self.assertFalse(is_valid)
        self.assertIn("strictly read-only", err or "")

    def test_stop_and_wait_gate_requires_human_approval(self):
        """Stop-and-Wait Architecture Gate: Unapproved plan must be BLOCKED."""
        mgr = CodingPipelineManager(workspace_path=self.workspace_path)
        inspected_src = str(self.workspace / "agent_workspace" / "core.py")

        req = CodingTaskRequest(
            task_id="TASK-GATE",
            repository_path=self.workspace_path,
            requirement_prompt="Add payment flow",
            target_branch="feat/payment",
            inspected_files=[inspected_src],
            target_files=["agent_workspace/core.py"],
            allowed_roles=["DOMAIN_LOGIC_AGENT"],
        )
        start_res = mgr.start_pipeline(req)
        self.assertEqual(start_res.current_stage, PipelineStage.PRECHECK)

        # Submit unapproved plan
        unapproved_plan = ScopedMutationPlan(
            task_id="TASK-GATE",
            plan_summary="Directly edit core.py",
            target_files=["agent_workspace/core.py"],
            assigned_role="DOMAIN_LOGIC_AGENT",
            human_approved=False,  # NOT approved
        )
        gate_res = mgr.submit_plan("TASK-GATE", unapproved_plan)
        self.assertEqual(gate_res.status, VerificationStatus.BLOCKED)
        self.assertIn("Stop-and-Wait Gate", gate_res.error_message or "")

        # Now approve and re-submit
        unapproved_plan.human_approved = True
        unapproved_plan.approval_token = "USER-TOKEN-12345"
        gate_res_approved = mgr.submit_plan("TASK-GATE", unapproved_plan)
        self.assertEqual(gate_res_approved.current_stage, PipelineStage.PLAN_AND_GATE)

    def test_full_pipeline_success_and_draft_pr_generation(self):
        """End-to-end P1 mock pipeline: Intake -> Gate -> Mutation -> Verification -> Draft PR."""
        wt_mgr = MockWorktreeManager()
        executor = MockScopedExecutor()
        verifier = MockVerificationRunner(should_pass=True)
        publisher = MockDraftPRPublisher()
        ledger = AuditLedger(workspace_path=self.workspace_path)

        mgr = CodingPipelineManager(
            workspace_path=self.workspace_path,
            worktree_manager=wt_mgr,
            scoped_executor=executor,
            verification_runner=verifier,
            draft_pr_publisher=publisher,
            audit_ledger=ledger,
        )

        inspected_file = str(self.workspace / "agent_workspace" / "core.py")
        req = CodingTaskRequest(
            task_id="TASK-SUCCESS",
            repository_path=self.workspace_path,
            requirement_prompt="Implement token defragmentation strategy",
            target_branch="feat/token-defrag",
            inspected_files=[inspected_file],
            target_files=["agent_workspace/core.py"],
            allowed_roles=["DOMAIN_LOGIC_AGENT"],
        )

        plan = ScopedMutationPlan(
            task_id="TASK-SUCCESS",
            plan_summary="Add SlidingWindowDefragmenter to core.py",
            target_files=["agent_workspace/core.py"],
            assigned_role="DOMAIN_LOGIC_AGENT",
            human_approved=True,
            approval_token="HUMAN-APPROVAL-TOKEN-OK",
            test_strategy=["Step 1: Python compileall", "Step 2: Unit Tests"],
        )

        result = mgr.execute_pipeline("TASK-SUCCESS", req, plan)

        self.assertEqual(result.status, VerificationStatus.PASS)
        self.assertEqual(result.current_stage, PipelineStage.COMPLETED)
        self.assertIsNotNone(result.pr_payload)
        self.assertTrue(result.pr_payload.is_draft)
        self.assertIn("token defragmentation", result.pr_payload.title)
        self.assertIn("Evidence Before Completion", result.pr_payload.body)
        self.assertEqual("commit-sha-98765", result.pr_payload.commit_hash)
        self.assertEqual(len(result.receipts), 2)
        self.assertTrue(all(r.status == VerificationStatus.PASS for r in result.receipts))
        self.assertEqual(len(publisher.published_prs), 1)

        # Verify stage transition history monotonicity
        stages = [entry["stage"] for entry in result.stage_history]
        self.assertEqual(stages, [
            "INTAKE",
            "PRECHECK",
            "PLAN_AND_GATE",
            "ISOLATED_MUTATION",
            "ISOLATED_MUTATION",
            "VERIFY_AND_EVIDENCE",
            "VERIFY_AND_EVIDENCE",
            "DRAFT_PR_EXPORT",
            "COMPLETED",
        ])

    def test_pipeline_aborts_on_failed_verification(self):
        """When verification fails, no Draft PR is published and status is FAIL."""
        wt_mgr = MockWorktreeManager()
        executor = MockScopedExecutor()
        verifier = MockVerificationRunner(should_pass=False)  # Tests will FAIL
        publisher = MockDraftPRPublisher()

        mgr = CodingPipelineManager(
            workspace_path=self.workspace_path,
            worktree_manager=wt_mgr,
            scoped_executor=executor,
            verification_runner=verifier,
            draft_pr_publisher=publisher,
        )

        inspected_file = str(self.workspace / "agent_workspace" / "core.py")
        req = CodingTaskRequest(
            task_id="TASK-FAIL-TEST",
            repository_path=self.workspace_path,
            requirement_prompt="Add faulty algorithm",
            target_branch="feat/faulty",
            inspected_files=[inspected_file],
            target_files=["agent_workspace/core.py"],
            allowed_roles=["DOMAIN_LOGIC_AGENT"],
        )

        plan = ScopedMutationPlan(
            task_id="TASK-FAIL-TEST",
            plan_summary="Faulty mutation",
            target_files=["agent_workspace/core.py"],
            assigned_role="DOMAIN_LOGIC_AGENT",
            human_approved=True,
            approval_token="TOKEN-OK",
        )

        result = mgr.execute_pipeline("TASK-FAIL-TEST", req, plan)

        self.assertEqual(result.status, VerificationStatus.FAIL)
        self.assertEqual(result.current_stage, PipelineStage.FAILED)
        self.assertIn("Verification ladder failed", result.error_message or "")
        self.assertIsNone(result.pr_payload)
        self.assertEqual(len(publisher.published_prs), 0)  # Zero Draft PR published


if __name__ == "__main__":
    unittest.main()
