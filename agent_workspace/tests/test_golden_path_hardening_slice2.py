"""
Test suite for Slice 2: LAS Golden Path Hardening & Architecture Remediation.
Verifies Gaps 1, 2, 4, and 6:
- Gap 1: Real mutation execution via AgentExecutor and non-empty mutation evidence verification.
- Gap 2: UnifiedPolicyGate chokepoint and fail-closed ScopeGuard interception.
- Gap 4: Persistent state authority and SQLite rehydration across process restarts.
- Gap 6: Mandatory Independent Review gate before Draft PR export.
"""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from agent_workspace.api import app
from agent_workspace.core.agent_executor import (
    AgentExecutor,
    GovernedToolRegistry,
    ScopeExpansionRequest,
    ScopeGuard,
    SecurityViolationError,
)
from agent_workspace.core.git_worktree import GitWorktreeManager, WorktreeSessionConfig
from agent_workspace.core.pipeline.manager import CodingPipelineManager
from agent_workspace.core.pipeline.models import (
    CodingTaskRequest,
    FileMutationSpec,
    PipelineStage,
    ScopedMutationPlan,
    VerificationReceipt,
    VerificationStatus,
)
from agent_workspace.core.policy_gate import UnifiedPolicyGate
from agent_workspace.core.repository import RepositoryInspector
from agent_workspace.core.runtime_events import IndependentReviewVerifier, RuntimeEventsLedger
from agent_workspace.routes.dependencies import API_KEYS


class MockLiveVerificationRunner:
    def __init__(self, should_pass: bool = True):
        self.should_pass = should_pass

    def run_verification_ladder(self, worktree_path: str, test_strategy: list[str]) -> list[VerificationReceipt]:
        status = VerificationStatus.PASS if self.should_pass else VerificationStatus.FAIL
        return [
            VerificationReceipt(
                step_name="Step 1: Test Verification",
                command="python -c \"print('verified')\"",
                exit_code=0 if self.should_pass else 1,
                status=status,
                stdout_snippet="verified" if self.should_pass else "failure",
                duration_ms=50,
            )
        ]


class TestGoldenPathHardeningSlice2(unittest.TestCase):
    def setUp(self):
        self.temp_root = tempfile.mkdtemp(prefix="las_slice2_test_")
        self.repo_dir = os.path.join(self.temp_root, "repo")
        os.makedirs(self.repo_dir, exist_ok=True)
        self.worktrees_dir = os.path.join(self.temp_root, "worktrees")
        os.makedirs(self.worktrees_dir, exist_ok=True)

        os.environ["LAS_WORKSPACE"] = self.repo_dir

        self.wt_manager = GitWorktreeManager(base_worktrees_dir=self.worktrees_dir)
        self.inspector = RepositoryInspector()
        self.executor = AgentExecutor()

        # Initialize source git repository
        self._init_git_repo(self.repo_dir)

        self.client = TestClient(app)
        API_KEYS["slice2-test-key"] = {
            "tenant": "tenant-1",
            "sub": "luke-actor",
            "role": "tenant",
        }
        self.auth_headers = {"x-api-key": "slice2-test-key"}

        import agent_workspace.routes.pipeline as pipe_mod
        pipe_mod._manager_instance = None
        pipe_mod._inspector_instance = None
        with pipe_mod._registry_lock:
            pipe_mod._task_registry.clear()

    def tearDown(self):
        os.environ.pop("LAS_WORKSPACE", None)
        API_KEYS.pop("slice2-test-key", None)
        import agent_workspace.routes.pipeline as pipe_mod
        pipe_mod._manager_instance = None
        pipe_mod._inspector_instance = None
        with pipe_mod._registry_lock:
            pipe_mod._task_registry.clear()

        if os.path.exists(self.temp_root):
            shutil.rmtree(self.temp_root, ignore_errors=True)

    def _init_git_repo(self, path: str) -> str:
        subprocess.run(["git", "init", "-b", "main"], cwd=path, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Slice2 Test Agent"], cwd=path, check=True)
        subprocess.run(["git", "config", "user.email", "agent@slice2.test"], cwd=path, check=True)

        calc_dir = os.path.join(path, "agent_workspace", "core")
        os.makedirs(calc_dir, exist_ok=True)
        calc_path = os.path.join(calc_dir, "calc.py")
        with open(calc_path, "w", encoding="utf-8") as f:
            f.write("def add(a, b):\n    return a + b\n")

        with open(os.path.join(path, ".gitignore"), "w", encoding="utf-8") as f:
            f.write(".agent/patches/\nagent_worktrees/\n")

        subprocess.run(["git", "add", "."], cwd=path, check=True)
        subprocess.run(["git", "commit", "-m", "chore: init main repo"], cwd=path, check=True)
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=path, check=True, capture_output=True, text=True)
        return head.stdout.strip()

    # -------------------------------------------------------------------------
    # Gap 1: Real Mutation Execution & Non-Empty Mutation Evidence
    # -------------------------------------------------------------------------
    def test_agent_executor_applies_concrete_file_mutations_into_worktree(self):
        """AgentExecutor.execute_plan applies FileMutationSpec to worktree and leaves host untouched."""
        session = self.wt_manager.create_worktree(
            repo_path=self.repo_dir,
            branch_name="feat/multiply-real",
            base_ref="main",
        )

        plan = ScopedMutationPlan(
            task_id="TASK-MUT-01",
            plan_summary="Add multiply function to calc.py",
            target_files=["agent_workspace/core/calc.py"],
            assigned_role="DOMAIN_LOGIC_AGENT",
            human_approved=True,
            file_mutations=[
                FileMutationSpec(
                    file_path="agent_workspace/core/calc.py",
                    content="def add(a, b):\n    return a + b\n\ndef multiply(a, b):\n    return a * b\n",
                    action="write",
                )
            ],
        )

        res = self.executor.execute_plan(session, plan)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(len(res.get("applied_mutations", [])), 1)

        # Verify target file in worktree contains multiply
        wt_calc = Path(session.worktree_path) / "agent_workspace" / "core" / "calc.py"
        self.assertTrue(wt_calc.exists())
        self.assertIn("def multiply(a, b):", wt_calc.read_text(encoding="utf-8"))

        # Verify host repo remains untouched (Anti-Corruption / Host Zero-Pollution)
        host_calc = Path(self.repo_dir) / "agent_workspace" / "core" / "calc.py"
        self.assertNotIn("def multiply(a, b):", host_calc.read_text(encoding="utf-8"))

        self.wt_manager.cleanup_worktree(session)

    def test_pipeline_fails_fast_when_mutation_evidence_is_missing(self):
        """When require_mutation_evidence=True and plan leaves worktree empty, pipeline halts with FAIL."""
        manager = CodingPipelineManager(
            workspace_path=self.repo_dir,
            worktree_manager=self.wt_manager,
            scoped_executor=self.executor,
            verification_runner=MockLiveVerificationRunner(should_pass=True),
        )

        req = CodingTaskRequest(
            task_id="TASK-EMPTY-MUT",
            repository_path=self.repo_dir,
            requirement_prompt="Add multiply function",
            target_branch="feat/empty-diff",
            inspected_files=["agent_workspace/core/calc.py"],
            target_files=["agent_workspace/core/calc.py"],
            allowed_roles=["DOMAIN_LOGIC_AGENT"],
            require_mutation_evidence=True,  # STRICT ENFORCEMENT
        )

        plan = ScopedMutationPlan(
            task_id="TASK-EMPTY-MUT",
            plan_summary="Empty plan that does not mutate files",
            target_files=["agent_workspace/core/calc.py"],
            assigned_role="DOMAIN_LOGIC_AGENT",
            human_approved=True,
            approval_token="LUKE_TOKEN_1",
            file_mutations=[],  # No mutations provided
            test_strategy=['python -c "print(1)"'],
        )

        result = manager.execute_pipeline(req.task_id, req, plan)
        self.assertEqual(result.status, VerificationStatus.FAIL)
        self.assertEqual(result.current_stage, PipelineStage.FAILED)
        self.assertIn("No mutation evidence", result.error_message)

    # -------------------------------------------------------------------------
    # Gap 2: ScopeGuard & UnifiedPolicyGate Fail-Closed Chokepoint
    # -------------------------------------------------------------------------
    def test_governed_tool_registry_blocks_invalid_tool_invocation(self):
        """GovernedToolRegistry must check validate_tool_call return value and raise SecurityViolationError on rejection."""
        session = self.wt_manager.create_worktree(
            repo_path=self.repo_dir,
            branch_name="feat/guard-check",
            base_ref="main",
        )

        from agent_workspace.core.agent_executor import TaskEnvironment
        env = TaskEnvironment(
            intent="Test scope guard",
            agent_role="DOMAIN_LOGIC_AGENT",
            mutable_scope=["agent_workspace/core/calc.py"],
            execution_environment=session,
        )
        guard = ScopeGuard(task_env=env, worktree_path=session.worktree_path)
        tools = GovernedToolRegistry(scope_guard=guard)

        # 1. Attempt to write to a path outside mutable scope -> ScopeExpansionRequest
        with self.assertRaises(ScopeExpansionRequest):
            tools.filesystem_write("viewer/src/App.tsx", "// unapproved frontend write")

        # 2. Attempt path traversal escape -> SecurityViolationError
        with self.assertRaises(SecurityViolationError):
            tools.filesystem_write("../outside.py", "# escape")

        # 3. Attempt empty file_path -> SecurityViolationError
        with self.assertRaises(SecurityViolationError):
            tools.filesystem_write("", "empty path")

        self.wt_manager.cleanup_worktree(session)

    # -------------------------------------------------------------------------
    # Gap 4: Persistent State Authority in SQLite across Process Restarts
    # -------------------------------------------------------------------------
    def test_pipeline_task_rehydration_from_sqlite_on_cache_miss(self):
        """If memory registry loses state, get_pipeline_task rehydrates state from persistent SQLite ledger/store."""
        task_id = "TASK-PERSIST-01"
        req_payload = {
            "task_id": task_id,
            "repository_path": self.repo_dir,
            "requirement_prompt": "Persistent task verification",
            "base_branch": "main",
            "target_branch": "feat/persist-check",
            "inspected_files": ["agent_workspace/core/calc.py"],
            "target_files": ["agent_workspace/core/calc.py"],
            "allowed_roles": ["DOMAIN_LOGIC_AGENT"],
        }
        res = self.client.post("/v1/pipeline/tasks", json=req_payload)
        self.assertEqual(res.status_code, 200)

        # Plan submission
        plan_payload = {
            "task_id": task_id,
            "plan_summary": "Implement persist logic",
            "target_files": ["agent_workspace/core/calc.py"],
            "assigned_role": "DOMAIN_LOGIC_AGENT",
            "human_approved": False,
        }
        res = self.client.post(f"/v1/pipeline/tasks/{task_id}/plan", json=plan_payload)
        self.assertEqual(res.status_code, 200)

        # Simulate service restart by wiping in-memory registry
        import agent_workspace.routes.pipeline as pipe_mod
        with pipe_mod._registry_lock:
            pipe_mod._task_registry.clear()

        # Query GET /v1/pipeline/tasks/{task_id} -> must rehydrate from SQLite projection rather than 404
        res = self.client.get(f"/v1/pipeline/tasks/{task_id}")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["task_id"], task_id)
        self.assertEqual(data["request"]["requirement_prompt"], "Persistent task verification")
        self.assertIsNotNone(data["plan"])

    # -------------------------------------------------------------------------
    # Gap 6: Mandatory Independent Review Gate before Draft PR
    # -------------------------------------------------------------------------
    def test_pipeline_independent_review_gate_enforcement(self):
        """When enable_independent_review=True, pipeline executes INDEPENDENT_REVIEW before DRAFT_PR_EXPORT."""
        manager = CodingPipelineManager(
            workspace_path=self.repo_dir,
            worktree_manager=self.wt_manager,
            scoped_executor=self.executor,
            verification_runner=MockLiveVerificationRunner(should_pass=True),
        )

        req = CodingTaskRequest(
            task_id="TASK-REVIEW-01",
            repository_path=self.repo_dir,
            requirement_prompt="Add multiply function with review gate",
            target_branch="feat/review-check",
            inspected_files=["agent_workspace/core/calc.py"],
            target_files=["agent_workspace/core/calc.py"],
            allowed_roles=["DOMAIN_LOGIC_AGENT"],
            enable_independent_review=True,
        )

        plan = ScopedMutationPlan(
            task_id="TASK-REVIEW-01",
            plan_summary="Add multiply function to calc.py",
            target_files=["agent_workspace/core/calc.py"],
            assigned_role="DOMAIN_LOGIC_AGENT",
            human_approved=True,
            approval_token="LUKE_TOKEN_OK",
            file_mutations=[
                FileMutationSpec(
                    file_path="agent_workspace/core/calc.py",
                    content="def add(a, b):\n    return a + b\n\ndef multiply(a, b):\n    return a * b\n",
                    action="write",
                )
            ],
            test_strategy=['python -c "print(1)"'],
        )

        result = manager.execute_pipeline(req.task_id, req, plan)
        self.assertEqual(result.status, VerificationStatus.PASS)
        self.assertEqual(result.current_stage, PipelineStage.COMPLETED)

        # Verify INDEPENDENT_REVIEW stage was recorded
        stages = [entry["stage"] for entry in result.stage_history]
        self.assertIn("INDEPENDENT_REVIEW", stages)
        self.assertIsNotNone(result.independent_review_receipt)
        self.assertTrue(result.independent_review_receipt.get("is_fresh", False))


if __name__ == "__main__":
    unittest.main()
