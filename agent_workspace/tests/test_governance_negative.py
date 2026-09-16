"""Automated Negative Governance Test Suite (Phase C).

Verifies that the LLM Agent System (LAS) execution boundaries strictly reject
unauthorized tool execution, destructive commands, self-approvals, empty test ladders,
and reviewer role boundary violations.
"""

from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest

import pytest

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
from agent_workspace.core.pipeline.contracts import IVerificationRunner
from agent_workspace.core.pipeline.manager import CodingPipelineManager
from agent_workspace.core.pipeline.models import (
    CodingPipelineResult,
    CodingTaskRequest,
    PipelineStage,
    ScopedMutationPlan,
    VerificationReceipt,
    VerificationStatus,
)
from agent_workspace.core.product_contracts import MissionPolicy
from agent_workspace.core.task_environment import SandboxPolicy, TaskEnvironment


class MockEmptyVerificationRunner(IVerificationRunner):
    """Returns empty receipts simulating an unexecuted test ladder."""

    def run_verification_ladder(self, worktree_path: str, test_strategy: list[str]) -> list[VerificationReceipt]:
        return []


from dataclasses import dataclass

@dataclass
class MockWorktreeSession:
    worktree_path: str
    session_id: str
    branch_name: str


class MockWorktreeManager:
    def create_worktree(self, repo_path: str, branch_name: str, base_ref: str):
        return MockWorktreeSession(worktree_path=repo_path, session_id="test-session", branch_name=branch_name)

    def commit_changes(self, session, msg: str) -> str:
        return "mock_commit_hash"

    def get_diff(self, session) -> str:
        return "mock_diff"


class TestGovernanceNegative(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name)
        (self.workspace / "src").mkdir(parents=True)
        (self.workspace / "protected").mkdir(parents=True)
        (self.workspace / "src" / "app.py").write_text("print('hello')", encoding="utf-8")
        (self.workspace / "protected" / "secret.py").write_text("# secret", encoding="utf-8")

        self.env = TaskEnvironment(
            intent="Negative governance tests",
            agent_role="DOMAIN_LOGIC_AGENT",
            mutable_scope=["src/"],
            available_governed_tools=["filesystem.read", "filesystem.write", "shell.exec", "git.diff"],
        )
        self.guard = ScopeGuard(self.env, str(self.workspace))
        self.registry = GovernedToolRegistry(self.guard)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_governed_tool_registry_rejects_immutable_path_direct_call(self):
        """Direct call to GovernedToolRegistry.filesystem_write on immutable path must be blocked."""
        with self.assertRaises(ScopeExpansionRequest):
            self.registry.filesystem_write("protected/secret.py", "malicious_content = True")

    def test_governed_tool_registry_rejects_destructive_command_direct_call(self):
        """Direct call to GovernedToolRegistry.shell_exec with destructive git command must be blocked."""
        with self.assertRaises(SecurityViolationError):
            self.registry.shell_exec("git reset --hard HEAD~1")

    def test_mission_self_approval_prohibited(self):
        """Autonomous agent cannot approve an ApprovalGate on a Mission aggregate."""
        plan = ExecutionPlan(
            plan_id="plan-1",
            mission_id="mission-1",
            revision=1,
            tasks=[PlanTask(task_id="t1", title="task", order=1)],
        )
        mission = Mission(
            mission_id="mission-1",
            requirement="Ensure governance",
            repository_id="repo-1",
            execution_policy=MissionPolicy(),
            actor_id="owner-human",
            execution_plan=plan,
            plan_reference=plan.plan_id,
            plan_revision=plan.revision,
        )
        gate = ApprovalGate(
            gate_id="gate-1",
            gate_type=ApprovalType.PLAN,
            subject=PlanApprovalSubject(
                plan_id="plan-1",
                plan_revision=1,
                plan_digest=plan.canonical_digest(),
            ),
            status=ApprovalStatus.APPROVED,
            actor_id="agent-rogue",
            decided_at=datetime.now(timezone.utc),
            idempotency_key="key-1",
        )
        with self.assertRaises(MissionAggregateError) as ctx:
            mission.add_approval_gate(gate)
        self.assertEqual(ctx.exception.code, "self_approval_prohibited")

    def test_approval_request_self_approval_prohibited(self):
        """ApprovalRequest model validator blocks when approver equals requester."""
        with self.assertRaises(ValueError) as ctx:
            ApprovalRequest(
                request_id="req-1",
                decision_type=ApprovalType.PLAN,
                subject=PlanApprovalSubject(
                    plan_id="plan-1",
                    plan_revision=1,
                    plan_digest="a" * 64,
                ),
                requested_change="Approve plan",
                reason="Done",
                impact="None",
                requested_actor="agent-builder",
                idempotency_key="idem-1",
                decision=ApprovalDecision(
                    status=ApprovalStatus.APPROVED,
                    actor_id="agent-builder",  # Same actor: Self-approval!
                    decided_at=datetime.now(timezone.utc),
                ),
            )
        self.assertIn("self_approval_prohibited", str(ctx.exception))

    def test_pipeline_rejects_empty_test_ladder(self):
        """Pipeline must fail when verification ladder produces zero receipts (GAP-05)."""
        mgr = CodingPipelineManager(
            workspace_path=str(self.workspace),
            worktree_manager=MockWorktreeManager(),
            verification_runner=MockEmptyVerificationRunner(),
        )
        req = CodingTaskRequest(
            task_id="TASK-EMPTY-LADDER",
            repository_path=str(self.workspace),
            requirement_prompt="Add simple function",
            target_branch="feat/simple",
            inspected_files=[str(self.workspace / "src" / "app.py")],
            target_files=["src/app.py"],
            allowed_roles=["DOMAIN_LOGIC_AGENT"],
        )
        plan = ScopedMutationPlan(
            task_id="TASK-EMPTY-LADDER",
            plan_summary="Empty verification ladder test",
            target_files=["src/app.py"],
            assigned_role="DOMAIN_LOGIC_AGENT",
            human_approved=True,
            approval_token="TOKEN_HUMAN_OK",
            test_strategy=[],
        )
        result = mgr.execute_pipeline("TASK-EMPTY-LADDER", req, plan)
        self.assertEqual(result.status, VerificationStatus.FAIL)
        self.assertIn("empty", result.error_message.lower())

    def test_reviewer_role_rejects_code_modification(self):
        """Reviewer role (QA_TEST_AGENT) is strictly read-only and cannot mutate files."""
        reviewer_env = TaskEnvironment(
            intent="Review code",
            agent_role="QA_TEST_AGENT",
            mutable_scope=["src/"],
            available_governed_tools=["filesystem.read", "filesystem.write", "shell.exec", "git.diff"],
        )
        guard = ScopeGuard(reviewer_env, str(self.workspace))
        registry = GovernedToolRegistry(guard)

        with self.assertRaises(ScopeExpansionRequest) as ctx:
            registry.filesystem_write("src/app.py", "hacked = True")
        self.assertIn("read-only", ctx.exception.reason.lower())

    def test_terminal_stage_reentry_rejected(self):
        """Pipeline manager rejects transitioning backwards from terminal stages (GAP-06)."""
        mgr = CodingPipelineManager(workspace_path=str(self.workspace))
        res = CodingPipelineResult(
            task_id="TASK-TERMINAL",
            current_stage=PipelineStage.COMPLETED,
            status=VerificationStatus.PASS,
        )
        with self.assertRaises(ValueError) as ctx:
            mgr._record_stage(res, PipelineStage.PLAN_AND_GATE, "Attempted rewind")
        self.assertIn("Illegal state transition", str(ctx.exception))
