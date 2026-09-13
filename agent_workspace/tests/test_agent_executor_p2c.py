"""Unit tests for ScopeGuard, GovernedToolRegistry, and AgentExecutor (Phase 2-C)."""

import os
import shutil
import subprocess
import tempfile
import unittest

from agent_workspace.core.agent_executor import (
    AgentExecutor,
    ExecutionAttempt,
    GovernedToolRegistry,
    ScopeExpansionRequest,
    ScopeGuard,
    SecurityViolationError,
    ToolCallEvidence,
)
from agent_workspace.core.pipeline.models import (
    CodingTaskRequest,
    PipelineStage,
    ScopedMutationPlan,
    VerificationReceipt,
    VerificationStatus,
    WorktreeSessionConfig,
)
from agent_workspace.core.pipeline.manager import CodingPipelineManager
from agent_workspace.core.task_environment import (
    SandboxPolicy,
    TaskEnvironment,
)


class TestScopeGuardP2C(unittest.TestCase):
    """Verifies ScopeGuard containment, path resolution, and command filtering."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="las_test_scope_")
        self.env = TaskEnvironment(
            intent="Update backend core",
            agent_role="BACKEND_INFRA_AGENT",
            mutable_scope=["agent_workspace/core/engine.py", "agent_workspace/tests/"],
            protected_scope=[".env*", ".git/", "secrets.yaml"],
            available_governed_tools=["filesystem.read", "filesystem.write", "shell.exec", "git.diff"],
        )
        self.guard = ScopeGuard(task_env=self.env, worktree_path=self.temp_dir)

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_path_traversal_escape_raises_security_violation(self):
        with self.assertRaises(SecurityViolationError):
            self.guard.resolve_and_verify_path("../../../outside.txt")

    def test_unallocated_tool_rejected(self):
        valid, err = self.guard.validate_tool_call("browser.open", {"url": "https://example.com"})
        self.assertFalse(valid)
        self.assertIn("not in the allocated governed toolchain", err)

    def test_write_to_mutable_scope_allowed(self):
        valid, err = self.guard.validate_tool_call(
            "filesystem.write",
            {"file_path": "agent_workspace/core/engine.py", "content": "# patch"},
        )
        self.assertTrue(valid)
        self.assertIsNone(err)

    def test_write_outside_mutable_scope_raises_scope_expansion(self):
        with self.assertRaises(ScopeExpansionRequest) as ctx:
            self.guard.validate_tool_call(
                "filesystem.write",
                {"file_path": "viewer/src/App.tsx", "content": "// forbidden"},
            )
        self.assertIn("outside designated mutable scope", str(ctx.exception))

    def test_write_to_protected_scope_raises_scope_expansion(self):
        with self.assertRaises(ScopeExpansionRequest) as ctx:
            self.guard.validate_tool_call(
                "filesystem.write",
                {"file_path": ".env.production", "content": "SECRET=123"},
            )
        self.assertIn("matches protected pattern", str(ctx.exception))

    def test_write_violating_role_boundary_raises_scope_expansion(self):
        ui_env = TaskEnvironment(
            intent="Update UI components",
            agent_role="UI_UX_AGENT",
            mutable_scope=["agent_workspace/core/engine.py"],
            available_governed_tools=["filesystem.write"],
        )
        ui_guard = ScopeGuard(task_env=ui_env, worktree_path=self.temp_dir)
        with self.assertRaises(ScopeExpansionRequest) as ctx:
            ui_guard.validate_tool_call(
                "filesystem.write",
                {"file_path": "agent_workspace/core/engine.py", "content": "# attack"},
            )
        self.assertIn("Violates role boundary prefix", str(ctx.exception))

    def test_destructive_shell_commands_intercepted(self):
        destructive_cmds = [
            "git push origin main --force",
            "git push -f origin main",
            "git reset --hard HEAD~1",
            "git clean -fd",
        ]
        for cmd in destructive_cmds:
            with self.assertRaises(SecurityViolationError) as ctx:
                self.guard.validate_tool_call("shell.exec", {"command": cmd})
            self.assertIn("Destructive shell command intercepted", str(ctx.exception))


class TestGovernedToolRegistryAndExecutorP2C(unittest.TestCase):
    """Verifies GovernedToolRegistry file operations and AgentExecutor execution loop."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="las_test_executor_")
        # Init a git repo inside temp_dir so git diff works
        subprocess.run(["git", "init", "-b", "main"], cwd=self.temp_dir, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test Agent"], cwd=self.temp_dir, check=True)
        subprocess.run(["git", "config", "user.email", "agent@test.local"], cwd=self.temp_dir, check=True)

        readme_file = os.path.join(self.temp_dir, "README.md")
        with open(readme_file, "w", encoding="utf-8") as f:
            f.write("# Hello\nLine 2\nLine 3\n")
        subprocess.run(["git", "add", "README.md"], cwd=self.temp_dir, check=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=self.temp_dir, check=True)

        self.env = TaskEnvironment(
            intent="Update README and add docs",
            agent_role="DOMAIN_LOGIC_AGENT",
            mutable_scope=["README.md", "docs/"],
            available_governed_tools=["filesystem.read", "filesystem.write", "shell.exec", "git.diff"],
            stop_condition={"max_turns": 3, "loop_limit": 3, "hitl_gate_required": True},
        )
        self.executor = AgentExecutor(task_env=self.env)
        self.session = WorktreeSessionConfig(
            session_id="sess-test-01",
            worktree_path=self.temp_dir,
            branch_name="feat/test",
            base_commit="abc",
        )

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_governed_tools_read_write_diff(self):
        res = self.executor.execute_plan(
            self.session,
            ScopedMutationPlan(
                task_id="t-01",
                plan_summary="Update docs",
                target_files=["README.md", "docs/guide.md"],
                assigned_role="DOMAIN_LOGIC_AGENT",
            ),
        )
        tools: GovernedToolRegistry = res["tools"]
        attempt: ExecutionAttempt = res["attempt"]

        # 1. Test filesystem.read
        read_res = self.executor.execute_tool(
            tools, attempt, "filesystem.read", {"file_path": "README.md", "start_line": 2, "end_line": 2}
        )
        self.assertEqual(read_res["content"], "Line 2")

        # 2. Test filesystem.write
        write_res = self.executor.execute_tool(
            tools,
            attempt,
            "filesystem.write",
            {"file_path": "docs/guide.md", "content": "# User Guide\nNew feature."},
        )
        self.assertEqual(write_res["status"], "SUCCESS")
        self.assertTrue(os.path.exists(os.path.join(self.temp_dir, "docs", "guide.md")))

        # 3. Test git.diff
        diff_res = self.executor.execute_tool(tools, attempt, "git.diff", {})
        self.assertIn("diff", diff_res)

        # 4. Verify evidence trail
        self.assertEqual(len(attempt.evidence_trail), 3)
        for ev in attempt.evidence_trail:
            self.assertIsInstance(ev, ToolCallEvidence)
            self.assertEqual(ev.exit_code, 0)
            self.assertIsNotNone(ev.merkle_hash)

    def test_loop_limit_safety_gate_enforcement(self):
        res = self.executor.execute_plan(
            self.session,
            ScopedMutationPlan(
                task_id="t-loop",
                plan_summary="Loop test",
                target_files=["README.md"],
                assigned_role="DOMAIN_LOGIC_AGENT",
            ),
        )
        tools: GovernedToolRegistry = res["tools"]
        attempt: ExecutionAttempt = res["attempt"]
        attempt.max_turns = 2

        # Turn 1
        self.executor.execute_tool(tools, attempt, "filesystem.read", {"file_path": "README.md"})
        self.assertEqual(attempt.turn_count, 1)

        # Turn 2
        self.executor.execute_tool(tools, attempt, "filesystem.read", {"file_path": "README.md"})
        self.assertEqual(attempt.turn_count, 2)

        # Turn 3 (exceeds max_turns=2) -> Must be blocked by loop limit
        blocked_res = self.executor.execute_tool(tools, attempt, "filesystem.read", {"file_path": "README.md"})
        self.assertEqual(blocked_res["status"], "BLOCKED")
        self.assertIn("Loop limit safety gate triggered", blocked_res["error"])
        self.assertEqual(attempt.status, VerificationStatus.BLOCKED)


class MockWorktreeManager:
    def __init__(self, path: str):
        self.path = path

    def create_worktree(self, repo_path: str, branch_name: str, base_ref: str = "main"):
        return WorktreeSessionConfig(
            session_id="sess-pipeline-test",
            worktree_path=self.path,
            branch_name=branch_name,
            base_commit="initial_sha",
        )

    def commit_changes(self, session, msg):
        return "mock_commit_sha_123"

    def get_diff(self, session):
        return "1 file changed, 1 insertion(+)"

    def cleanup_worktree(self, session, remove_branch_on_abort=False):
        return True


class MockVerificationRunner:
    def run_verification_ladder(self, worktree_path, test_strategy):
        return [
            VerificationReceipt(
                step_name="unit_tests",
                command="pytest",
                exit_code=0,
                status=VerificationStatus.PASS,
                stdout_snippet="1 passed",
                duration_ms=10,
            )
        ]


class TestPipelineIntegrationWithAgentExecutorP2C(unittest.TestCase):
    """Verifies that AgentExecutor plugs seamlessly into CodingPipelineManager via IScopedExecutor."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="las_test_pipeline_int_")
        core_dir = os.path.join(self.temp_dir, "agent_workspace", "core")
        os.makedirs(core_dir, exist_ok=True)
        with open(os.path.join(core_dir, "engine.py"), "w", encoding="utf-8") as f:
            f.write("# engine implementation\n")

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_pipeline_executes_with_agent_executor(self):
        executor = AgentExecutor()
        manager = CodingPipelineManager(
            workspace_path=self.temp_dir,
            worktree_manager=MockWorktreeManager(self.temp_dir),
            scoped_executor=executor,
            verification_runner=MockVerificationRunner(),
        )

        request = CodingTaskRequest(
            task_id="TASK-P2C-INT-001",
            repository_path=self.temp_dir,
            requirement_prompt="Update backend logic safely",
            target_branch="feat/test-p2c",
            inspected_files=["agent_workspace/core/engine.py"],
            target_files=["agent_workspace/core/engine.py"],
            allowed_roles=["DOMAIN_LOGIC_AGENT"],
        )

        plan = ScopedMutationPlan(
            task_id="TASK-P2C-INT-001",
            plan_summary="Safely patch core engine",
            target_files=["agent_workspace/core/engine.py"],
            assigned_role="DOMAIN_LOGIC_AGENT",
            human_approved=True,
            approval_token="PO_LUKE_TOKEN",
            test_strategy=["pytest"],
        )

        result = manager.execute_pipeline(request.task_id, request, plan)
        self.assertEqual(result.status, VerificationStatus.PASS)
        self.assertEqual(result.current_stage, PipelineStage.COMPLETED)
        self.assertIsNotNone(result.pr_payload)


if __name__ == "__main__":
    unittest.main()
