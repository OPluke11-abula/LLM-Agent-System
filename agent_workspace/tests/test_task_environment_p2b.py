"""Unit tests for TaskEnvironment, TaskGraph, and TaskEnvironmentSynthesizer (Phase 2-B)."""

import unittest
from agent_workspace.core.task_environment import (
    AgentCapabilityRequirement,
    CyclicDependencyError,
    SandboxPolicy,
    ScopeBoundaryError,
    TaskEnvironment,
    TaskEnvironmentSynthesizer,
    TaskGraph,
    TaskNode,
    TaskStatus,
)
from agent_workspace.core.repository import RepositoryProfile


class TestTaskEnvironmentP2B(unittest.TestCase):
    """Verifies TaskEnvironment aggregate and path mutability validation."""

    def test_task_environment_15_attributes(self):
        env = TaskEnvironment(
            intent="Implement isolated worktree management",
            acceptance_criteria=["Git worktree creates cleanly", "Preservation receipt matches"],
            agent_role="BACKEND_INFRA_AGENT",
            mutable_scope=["agent_workspace/core/git_worktree.py", "agent_workspace/tests/"],
            protected_scope=[".env*", ".git/"],
            relevant_architecture=["docs/obsidian/01 Agent Strategy.md"],
            relevant_contracts=["spec/workflow.schema.json"],
            relevant_source=["agent_workspace/core/repository.py:L20-L80"],
            relevant_tests=["test_git_worktree_p2a.py"],
            current_failure_evidence=["None"],
            available_governed_tools=["filesystem.read", "filesystem.write", "shell.exec", "git.diff"],
            sandbox_policy=SandboxPolicy(isolation_level="worktree", max_execution_seconds=45.0),
            execution_environment=None,
            required_reviews=["QA_TEST_AGENT"],
            stop_condition={"max_turns": 3, "loop_limit": 3, "hitl_gate_required": True},
        )

        self.assertEqual(env.agent_role, "BACKEND_INFRA_AGENT")
        self.assertEqual(len(env.acceptance_criteria), 2)
        self.assertTrue(env.validate_tool_allowed("filesystem.read"))
        self.assertFalse(env.validate_tool_allowed("browser.open"))

    def test_is_path_mutable_enforcement(self):
        env = TaskEnvironment(
            intent="Update backend core",
            agent_role="BACKEND_INFRA_AGENT",
            mutable_scope=["agent_workspace/core/git_worktree.py", "agent_workspace/tests/"],
            protected_scope=[".env*", ".git/", "credentials.json"],
        )

        # 1. Allowed paths in mutable scope
        allowed, err = env.is_path_mutable("agent_workspace/core/git_worktree.py")
        self.assertTrue(allowed)
        self.assertIsNone(err)

        allowed, err = env.is_path_mutable("agent_workspace/tests/test_worktree.py")
        self.assertTrue(allowed)
        self.assertIsNone(err)

        # 2. Blocked path outside mutable scope
        allowed, err = env.is_path_mutable("viewer/src/App.tsx")
        self.assertFalse(allowed)
        self.assertIn("outside designated mutable scope", err)

        # 3. Blocked path matching protected scope
        allowed, err = env.is_path_mutable(".env.local")
        self.assertFalse(allowed)
        self.assertIn("matches protected pattern", err)

        allowed, err = env.is_path_mutable(".git/config")
        self.assertFalse(allowed)
        self.assertIn("protected directory", err)


class TestTaskGraphSchedulerP2B(unittest.TestCase):
    """Verifies TaskGraph DAG scheduling, cycle detection, and parallel scope constraints."""

    def setUp(self):
        self.graph = TaskGraph(graph_id="graph-p2b-test", description="Phase 2-B Test Graph")

    def test_task_graph_dependency_resolution(self):
        t1 = TaskNode(
            task_id="t1",
            title="Setup Repo",
            intent="Initialize repository profile",
            assigned_role="BACKEND_INFRA_AGENT",
            mutable_scope=["agent_workspace/core/repository.py"],
        )
        t2 = TaskNode(
            task_id="t2",
            title="Setup Worktree",
            intent="Create git worktree manager",
            assigned_role="BACKEND_INFRA_AGENT",
            mutable_scope=["agent_workspace/core/git_worktree.py"],
            dependencies=["t1"],
        )

        self.graph.add_task(t1)
        self.graph.add_task(t2)

        # Initially, only t1 is ready
        ready = self.graph.get_ready_tasks()
        self.assertEqual(len(ready), 1)
        self.assertEqual(ready[0].task_id, "t1")

        # Mark t1 completed, now t2 should become ready
        self.graph.mark_completed("t1", "Repository profile completed")
        self.assertEqual(self.graph.get_task("t1").status, TaskStatus.COMPLETED)

        ready = self.graph.get_ready_tasks()
        self.assertEqual(len(ready), 1)
        self.assertEqual(ready[0].task_id, "t2")

    def test_task_graph_transitive_failure_blocking(self):
        t1 = TaskNode(
            task_id="t1",
            title="Base Task",
            intent="Base logic",
            assigned_role="DOMAIN_LOGIC_AGENT",
        )
        t2 = TaskNode(
            task_id="t2",
            title="Dependent Task",
            intent="Dependent logic",
            assigned_role="DOMAIN_LOGIC_AGENT",
            dependencies=["t1"],
        )
        self.graph.add_task(t1)
        self.graph.add_task(t2)

        # Mark t1 failed, t2 must become BLOCKED
        self.graph.mark_failed("t1", "Syntax error in base logic")
        self.assertEqual(self.graph.get_task("t1").status, TaskStatus.FAILED)
        self.assertEqual(self.graph.get_task("t2").status, TaskStatus.BLOCKED)

    def test_task_graph_cycle_detection(self):
        t1 = TaskNode(
            task_id="t1",
            title="Task 1",
            intent="Logic 1",
            assigned_role="DOMAIN_LOGIC_AGENT",
            dependencies=["t2"],
        )
        t2 = TaskNode(
            task_id="t2",
            title="Task 2",
            intent="Logic 2",
            assigned_role="DOMAIN_LOGIC_AGENT",
            dependencies=["t1"],
        )
        self.graph.add_task(t1)
        with self.assertRaises(CyclicDependencyError) as ctx:
            self.graph.add_task(t2)
        self.assertIn("Cyclic dependency detected", str(ctx.exception))

    def test_validate_no_overlapping_scopes_parallelism(self):
        t_ui = TaskNode(
            task_id="t_ui",
            title="UI Feature",
            intent="Update viewer sidebar",
            assigned_role="UI_UX_AGENT",
            mutable_scope=["viewer/src/components/Sidebar.tsx"],
        )
        t_backend = TaskNode(
            task_id="t_backend",
            title="Backend Feature",
            intent="Update repository inspector",
            assigned_role="BACKEND_INFRA_AGENT",
            mutable_scope=["agent_workspace/core/repository.py"],
        )
        t_collide = TaskNode(
            task_id="t_collide",
            title="Colliding UI Feature",
            intent="Update viewer components",
            assigned_role="UI_UX_AGENT",
            mutable_scope=["viewer/src/components/"],
        )

        self.graph.add_task(t_ui)
        self.graph.add_task(t_backend)
        self.graph.add_task(t_collide)

        # 1. Non-overlapping scopes (t_ui and t_backend) can run in parallel
        valid, err = self.graph.validate_no_overlapping_scopes(["t_ui", "t_backend"])
        self.assertTrue(valid)
        self.assertIsNone(err)

        # 2. Overlapping directory prefix (t_ui and t_collide) must be blocked
        valid, err = self.graph.validate_no_overlapping_scopes(["t_ui", "t_collide"])
        self.assertFalse(valid)
        self.assertIn("Parallel scope collision", err)


class TestTaskEnvironmentSynthesizerP2B(unittest.TestCase):
    """Verifies TaskEnvironment synthesis, role boundaries, and tool mounting."""

    def setUp(self):
        self.synthesizer = TaskEnvironmentSynthesizer()
        self.dummy_profile = RepositoryProfile(
            repository_path="D:/GitHub/LLM-Agent-System",
            current_branch="main",
            head_commit="abcdef1234567890abcdef1234567890abcdef12",
            is_clean=True,
            uncommitted_files=[],
            detected_ecosystems=["python"],
            test_commands=[{"name": "pytest", "command": "pytest agent_workspace/tests"}],
            linter_commands=[],
            protected_paths=[".env*", ".git/", "secrets.yaml"],
        )

    def test_synthesizer_success_path(self):
        node = TaskNode(
            task_id="task-p2b-01",
            title="Implement TaskEnvironment",
            intent="Create task_environment.py with ADR-006 spec",
            assigned_role="DOMAIN_LOGIC_AGENT",
            mutable_scope=["agent_workspace/core/task_environment.py", "agent_workspace/tests/"],
            acceptance_criteria=["15 attributes present", "Unit tests pass"],
        )

        env = self.synthesizer.synthesize(
            task=node,
            repo_profile=self.dummy_profile,
            relevant_contracts=["agent_workspace/core/pipeline/models.py"],
        )

        self.assertEqual(env.agent_role, "DOMAIN_LOGIC_AGENT")
        self.assertIn("agent_workspace/core/task_environment.py", env.mutable_scope)
        self.assertIn("secrets.yaml", env.protected_scope)
        self.assertIn("pytest: pytest agent_workspace/tests", env.relevant_tests)
        self.assertEqual(env.stop_condition["max_turns"], 3)
        self.assertTrue(env.stop_condition["hitl_gate_required"])

    def test_synthesizer_rejects_role_boundary_violation(self):
        # UI_UX_AGENT is forbidden from modifying agent_workspace/
        node = TaskNode(
            task_id="task-violate-01",
            title="UI modifying backend",
            intent="Illegally touch core",
            assigned_role="UI_UX_AGENT",
            mutable_scope=["agent_workspace/core/engine.py"],
        )

        with self.assertRaises(ScopeBoundaryError) as ctx:
            self.synthesizer.synthesize(task=node, repo_profile=self.dummy_profile)
        self.assertIn("violates boundary prefix", str(ctx.exception))

    def test_synthesizer_read_only_role_strips_write_tool(self):
        # SECURITY_AUDIT_AGENT is strictly read-only
        node = TaskNode(
            task_id="task-audit-01",
            title="Audit system",
            intent="Scan security without writing",
            assigned_role="SECURITY_AUDIT_AGENT",
            mutable_scope=[],
        )

        env = self.synthesizer.synthesize(task=node, repo_profile=self.dummy_profile)
        self.assertNotIn("filesystem.write", env.available_governed_tools)
        self.assertIn("filesystem.read", env.available_governed_tools)


if __name__ == "__main__":
    unittest.main()
