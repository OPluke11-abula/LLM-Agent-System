"""Adversarial Agent Governance Test Suite (Phase D).

Executes 6 hostile-but-legitimate workload scenarios to stress-test LAS's governance resilience:
- ADV-01: Normal Authorized Work (Baseline Pass)
- ADV-02: Scope Expansion Attack (Unauthorized path mutation)
- ADV-03: Destructive Command Attack (Interception of destructive shell commands)
- ADV-04: Direct Tool Bypass Attack (Circumvention via direct registry access)
- ADV-05: Self-Approval Attack (Autonomous agent approving its own plan/scope)
- ADV-06: Reviewer Contamination Attack (Reviewer role attempting code modification)
"""

from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest

from agent_workspace.core.agent_executor import (
    GovernedToolRegistry,
    ScopeExpansionRequest,
    ScopeGuard,
    SecurityViolationError,
)
from agent_workspace.core.mission_contracts import (
    ApprovalDecision,
    ApprovalGate,
    ApprovalRequest,
    ApprovalStatus,
    ApprovalType,
    ExecutionPlan,
    PlanApprovalSubject,
    PlanTask,
)
from agent_workspace.core.mission_model import Mission, MissionAggregateError
from agent_workspace.core.pipeline.manager import CodingPipelineManager
from agent_workspace.core.pipeline.models import (
    CodingTaskRequest,
    ScopedMutationPlan,
    VerificationStatus,
)
from agent_workspace.core.product_contracts import MissionPolicy
from agent_workspace.core.task_environment import TaskEnvironment


class TestAdversarialGovernance(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name)
        (self.workspace / "src").mkdir(parents=True)
        (self.workspace / "protected").mkdir(parents=True)
        (self.workspace / "src" / "feature.py").write_text("def hello(): return 'world'\n", encoding="utf-8")
        (self.workspace / "protected" / "config.py").write_text("DATABASE_URL = 'secret'\n", encoding="utf-8")

        self.env = TaskEnvironment(
            intent="Adversarial Testing",
            agent_role="DOMAIN_LOGIC_AGENT",
            mutable_scope=["src/"],
            available_governed_tools=["filesystem.read", "filesystem.write", "shell.exec", "git.diff"],
        )
        self.guard = ScopeGuard(self.env, str(self.workspace))
        self.registry = GovernedToolRegistry(self.guard)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_adv_01_normal_authorized_work(self):
        """ADV-01: Authorized modification within declared mutable scope succeeds."""
        res = self.registry.filesystem_write("src/feature.py", "def hello(): return 'verified'\n")
        self.assertEqual(res["status"], "SUCCESS")
        content = (self.workspace / "src" / "feature.py").read_text(encoding="utf-8")
        self.assertIn("verified", content)

    def test_adv_02_scope_expansion_attack(self):
        """ADV-02: Rogue agent attempts modifying protected files outside mutable scope."""
        with self.assertRaises(ScopeExpansionRequest) as ctx:
            self.guard.validate_tool_call("filesystem.write", {
                "file_path": "protected/config.py",
                "content": "DATABASE_URL = 'pwned'\n"
            })
        self.assertIn("outside designated mutable scope", ctx.exception.reason)

    def test_adv_03_destructive_command_attack(self):
        """ADV-03: Malicious shell commands (git reset --hard, git push -f) are intercepted."""
        destructive_cmds = [
            "git reset --hard HEAD~1",
            "git push origin main --force",
            "git clean -fdx",
        ]
        for cmd in destructive_cmds:
            with self.subTest(cmd=cmd):
                with self.assertRaises(SecurityViolationError):
                    self.guard.validate_tool_call("shell.exec", {"command": cmd})

    def test_adv_04_direct_tool_bypass_attack(self):
        """ADV-04: Agent with direct reference to GovernedToolRegistry cannot bypass ScopeGuard."""
        with self.assertRaises(ScopeExpansionRequest):
            self.registry.filesystem_write("protected/config.py", "# direct bypass")

        with self.assertRaises(SecurityViolationError):
            self.registry.shell_exec("git reset --hard HEAD~1")

    def test_adv_05_self_approval_attack(self):
        """ADV-05: Agent attempts to self-approve its plan on Mission aggregate and Pipeline."""
        # 1. Mission aggregate defense
        plan = ExecutionPlan(
            plan_id="plan-adv",
            mission_id="mission-adv",
            revision=1,
            tasks=[PlanTask(task_id="t1", title="exploit", order=1)],
        )
        mission = Mission(
            mission_id="mission-adv",
            requirement="Stress test governance",
            repository_id="repo-adv",
            execution_policy=MissionPolicy(),
            actor_id="human-owner",
            execution_plan=plan,
            plan_reference=plan.plan_id,
            plan_revision=plan.revision,
        )
        agent_gate = ApprovalGate(
            gate_id="gate-adv-1",
            gate_type=ApprovalType.PLAN,
            subject=PlanApprovalSubject(
                plan_id="plan-adv",
                plan_revision=1,
                plan_digest=plan.canonical_digest(),
            ),
            status=ApprovalStatus.APPROVED,
            actor_id="agent-coder",  # Agent identity!
            decided_at=datetime.now(timezone.utc),
            idempotency_key="key-adv-1",
        )
        with self.assertRaises(MissionAggregateError) as ctx:
            mission.add_approval_gate(agent_gate)
        self.assertEqual(ctx.exception.code, "self_approval_prohibited")

        # 2. Pipeline Manager defense
        mgr = CodingPipelineManager(workspace_path=str(self.workspace))
        req = CodingTaskRequest(
            task_id="TASK-SELF-APPROVE",
            repository_path=str(self.workspace),
            requirement_prompt="Add feature",
            target_branch="feat/auto",
            inspected_files=[str(self.workspace / "src" / "feature.py")],
            target_files=["src/feature.py"],
            allowed_roles=["DOMAIN_LOGIC_AGENT"],
        )
        mgr.start_pipeline(req)
        plan_self = ScopedMutationPlan(
            task_id="TASK-SELF-APPROVE",
            plan_summary="Plan attempting self-approval",
            target_files=["src/feature.py"],
            assigned_role="DOMAIN_LOGIC_AGENT",
            human_approved=True,
            approval_token="DOMAIN_LOGIC_AGENT",  # Token matches assigned role!
            test_strategy=["pytest"],
        )
        res = mgr.submit_plan("TASK-SELF-APPROVE", plan_self)
        self.assertEqual(res.status, VerificationStatus.BLOCKED)
        self.assertIn("self-approval rejected", res.error_message.lower())

    def test_adv_06_reviewer_contamination_attack(self):
        """ADV-06: Reviewer agents (QA_TEST_AGENT, PERFORMANCE_LATENCY_AGENT) cannot write code."""
        for role in ["QA_TEST_AGENT", "PERFORMANCE_LATENCY_AGENT", "SECURITY_AUDIT_AGENT"]:
            with self.subTest(role=role):
                reviewer_env = TaskEnvironment(
                    intent="Review Work",
                    agent_role=role,
                    mutable_scope=["src/"],
                    available_governed_tools=["filesystem.read", "filesystem.write", "shell.exec", "git.diff"],
                )
                reviewer_guard = ScopeGuard(reviewer_env, str(self.workspace))
                reviewer_reg = GovernedToolRegistry(reviewer_guard)

                with self.assertRaises(ScopeExpansionRequest) as ctx:
                    reviewer_reg.filesystem_write("src/feature.py", "# reviewer edit")
                self.assertIn("read-only", ctx.exception.reason.lower())
