"""Unit & Integration Tests for Multi-Agent Consensus Debate & Committee Protocol (Phase 85).

Tests:
1. CommitteeCoordinator role auto-selection (security triggers, architectural boundaries, QA enforcement).
2. PipelineDebateProtocol consensus synthesis (weights, dissent recording, scorecard generation).
3. Critical security objection triggering REJECTED_NEEDS_REVISION.
4. CodingPipelineManager end-to-end integration with COMMITTEE_DEBATE stage and PR scorecard export.
5. REST endpoint POST /v1/pipeline/tasks/{task_id}/debate and WebSocket telemetry broadcasting.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from fastapi.testclient import TestClient

from agent_workspace.api import app
from agent_workspace.core.pipeline.models import (
    CodingTaskRequest,
    PipelineStage,
    ScopedMutationPlan,
    VerificationStatus,
    VerificationReceipt,
    DraftPRPayload,
    WorktreeSessionConfig,
)
from agent_workspace.core.pipeline.committee import (
    CommitteeCoordinator,
    CommitteeFormation,
)
from agent_workspace.core.pipeline.debate_protocol import PipelineDebateProtocol
from agent_workspace.core.pipeline.manager import CodingPipelineManager
from agent_workspace.core.pipeline.contracts import (
    IWorktreeManager,
    IScopedExecutor,
    IVerificationRunner,
    IDraftPRPublisher,
)


# ---------------------------------------------------------------------------
# Stubs & Test Doubles
# ---------------------------------------------------------------------------

class StubWorktreeManager(IWorktreeManager):
    def create_worktree(self, repo_path: str, branch_name: str, base_ref: str = "main") -> WorktreeSessionConfig:
        return WorktreeSessionConfig(
            session_id=f"wt-test-{branch_name}",
            worktree_path=repo_path,
            branch_name=branch_name,
            base_commit="mock-base-sha-123456",
        )

    def commit_changes(self, session: WorktreeSessionConfig, message: str) -> str:
        return "mock-commit-sha-789012"

    def cleanup_worktree(self, session: WorktreeSessionConfig, remove_branch_on_abort: bool = False) -> bool:
        return True

    def get_diff(self, session: WorktreeSessionConfig) -> str:
        return "+ // Committee-verified production code\n+ def test_func(): pass"


class StubScopedExecutor(IScopedExecutor):
    def execute_plan(self, session: WorktreeSessionConfig, plan: ScopedMutationPlan) -> dict[str, Any]:
        return {"status": "success", "modified_files": plan.target_files}

    def validate_scope_compliance(self, role: str, target_files: list[str]) -> tuple[bool, Optional[str]]:
        return True, None


class StubVerificationRunner(IVerificationRunner):
    def run_verification_ladder(self, worktree_path: str, test_strategy: list[str]) -> list[VerificationReceipt]:
        return [
            VerificationReceipt(
                step_name="test_suite",
                command="pytest agent_workspace/tests/",
                exit_code=0,
                status=VerificationStatus.PASS,
                duration_ms=45,
            )
        ]


class StubDraftPRPublisher(IDraftPRPublisher):
    def publish_draft_pr(self, payload: DraftPRPayload, repo_path: str) -> str:
        return "https://github.com/mock-org/LLM-Agent-System/pull/85"


# ---------------------------------------------------------------------------
# Test Suite
# ---------------------------------------------------------------------------

class TestPipelineCommitteeP85(unittest.TestCase):
    """Test suite for Phase 85 Committee Deliberation & Consensus Protocol."""

    def test_committee_coordinator_security_trigger(self):
        """Validates that security keywords strictly enforce the Security Auditor persona."""
        coordinator = CommitteeCoordinator()
        req = CodingTaskRequest(
            task_id="TASK-SEC-01",
            repository_path=str(Path(".").resolve()),
            requirement_prompt="Implement JWT auth token validator and secure credential sandbox",
            target_branch="feat/auth-sandbox",
            target_files=["agent_workspace/core/security.py"],
        )

        formation = coordinator.evaluate_committee(req)
        self.assertTrue(formation.enforced_security_audit)
        self.assertTrue(any(m.role == "securityauditor" for m in formation.members))
        self.assertIn(formation.risk_level, ("HIGH", "CRITICAL"))
        self.assertTrue(any(m.role == "qaengineer" for m in formation.members))

    def test_committee_coordinator_architecture_trigger(self):
        """Validates that cross-cutting target files trigger Principal System Architect inclusion."""
        coordinator = CommitteeCoordinator()
        req = CodingTaskRequest(
            task_id="TASK-ARCH-01",
            repository_path=str(Path(".").resolve()),
            requirement_prompt="Refactor database gateway interface and add distributed session cache",
            target_branch="feat/arch-refactor",
            target_files=[
                "agent_workspace/core/database.py",
                "agent_workspace/core/models.py",
                "agent_workspace/core/pipeline/manager.py",
                "agent_workspace/api.py",
            ],
        )

        formation = coordinator.evaluate_committee(req)
        self.assertTrue(formation.enforced_architect_review)
        self.assertTrue(any(m.role == "architect" for m in formation.members))
        self.assertTrue(any(m.role == "qaengineer" for m in formation.members))

    def test_committee_debate_protocol_approved(self):
        """Validates multi-agent deliberation producing CONSENSUS_APPROVED scorecard."""
        protocol = PipelineDebateProtocol()
        coordinator = CommitteeCoordinator()

        req = CodingTaskRequest(
            task_id="TASK-OK-01",
            repository_path=str(Path(".").resolve()),
            requirement_prompt="Add utility helper for timestamp normalization",
            target_branch="feat/timestamp-helper",
            target_files=["agent_workspace/core/utils.py"],
            debate_rounds=1,
        )

        formation = coordinator.evaluate_committee(req)
        debate_record = protocol.run_debate(req, formation)

        self.assertEqual(debate_record.task_id, "TASK-OK-01")
        self.assertEqual(len(debate_record.rounds), 1)
        self.assertGreaterEqual(len(debate_record.rounds[0].turns), 2)
        self.assertEqual(debate_record.consensus_scorecard.decision, "CONSENSUS_APPROVED")
        self.assertGreaterEqual(debate_record.consensus_scorecard.composite_score, 0.70)
        self.assertIsNotNone(debate_record.synthesized_mutation_plan)
        self.assertGreater(len(debate_record.synthesized_mutation_plan.test_strategy), 0)

    def test_committee_debate_protocol_security_rejection(self):
        """Validates that attempts to bypass auth/sandbox trigger REJECTED_NEEDS_REVISION."""
        protocol = PipelineDebateProtocol()
        coordinator = CommitteeCoordinator()

        req = CodingTaskRequest(
            task_id="TASK-EXPLOIT-01",
            repository_path=str(Path(".").resolve()),
            requirement_prompt="Provide backdoor to bypass auth and disable sandbox in production",
            target_branch="feat/bypass",
            target_files=["agent_workspace/core/security.py"],
            debate_rounds=1,
        )

        formation = coordinator.evaluate_committee(req)
        debate_record = protocol.run_debate(req, formation)

        self.assertEqual(debate_record.consensus_scorecard.decision, "REJECTED_NEEDS_REVISION")
        self.assertLess(debate_record.consensus_scorecard.security_assurance, 0.70)
        self.assertGreater(len(debate_record.consensus_scorecard.dissenting_opinions), 0)
        self.assertTrue(any("CRITICAL SECURITY ALERT" in turn.content for r in debate_record.rounds for turn in r.turns))

    def test_pipeline_manager_with_committee_execution(self):
        """Validates end-to-end CodingPipelineManager execution with COMMITTEE_DEBATE stage enabled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create minimal git repository skeleton to pass Anti-Summary preflight
            repo_path = Path(tmpdir)
            (repo_path / ".git").mkdir()
            (repo_path / "AGENTS.md").write_text("# Project Agent Entry Point\nCanonical Coordination Workspace", encoding="utf-8")
            (repo_path / "src").mkdir()
            (repo_path / "src" / "service.py").write_text("def hello(): pass\n", encoding="utf-8")

            manager = CodingPipelineManager(
                workspace_path=str(repo_path),
                worktree_manager=StubWorktreeManager(),
                scoped_executor=StubScopedExecutor(),
                verification_runner=StubVerificationRunner(),
                draft_pr_publisher=StubDraftPRPublisher(),
            )

            req = CodingTaskRequest(
                task_id="TASK-P85-COMMITTEE",
                repository_path=str(repo_path),
                requirement_prompt="Implement secure service helper with automated validation",
                target_branch="feat/p85-service",
                inspected_files=["AGENTS.md"],
                target_files=["src/service.py"],
                allowed_roles=["DOMAIN_LOGIC_AGENT"],
                enable_committee=True,
                debate_rounds=1,
            )

            plan = ScopedMutationPlan(
                task_id="TASK-P85-COMMITTEE",
                plan_summary="Add service helper",
                target_files=["src/service.py"],
                assigned_role="DOMAIN_LOGIC_AGENT",
                human_approved=True,
                approval_token="TOKEN_P85_VERIFIED",
            )

            result = manager.execute_pipeline("TASK-P85-COMMITTEE", req, plan)

            self.assertEqual(result.status, VerificationStatus.PASS)
            self.assertEqual(result.current_stage, PipelineStage.COMPLETED)
            self.assertIsNotNone(result.committee_debate)
            self.assertEqual(result.committee_debate.consensus_scorecard.decision, "CONSENSUS_APPROVED")

            # Verify stage history includes COMMITTEE_DEBATE
            stages_visited = [e["stage"] for e in result.stage_history]
            self.assertIn(PipelineStage.COMMITTEE_DEBATE.value, stages_visited)
            self.assertIn(PipelineStage.PLAN_AND_GATE.value, stages_visited)

            # Verify PR body contains the Committee Consensus Scorecard section
            self.assertIsNotNone(result.pr_payload)
            self.assertIn("Multi-Agent Committee Consensus Scorecard (P85)", result.pr_payload.body)
            self.assertIn("CONSENSUS_APPROVED", result.pr_payload.body)

    def test_api_debate_endpoint_integration(self):
        """Validates FastAPI REST endpoint POST /v1/pipeline/tasks/{task_id}/debate."""
        client = TestClient(app)

        task_id = "TASK-API-DEBATE-01"
        intake_payload = {
            "task_id": task_id,
            "repository_path": str(Path(".").resolve()),
            "requirement_prompt": "Audit core module boundaries and add test coverage",
            "target_branch": "feat/api-debate-test",
            "inspected_files": ["AGENTS.md"],
            "target_files": ["agent_workspace/api.py"],
            "allowed_roles": ["BACKEND_INFRA_AGENT"],
        }

        # 1. Create task
        create_res = client.post("/v1/pipeline/tasks", json=intake_payload)
        self.assertEqual(create_res.status_code, 200)

        # 2. Trigger debate endpoint
        debate_res = client.post(
            f"/v1/pipeline/tasks/{task_id}/debate",
            json={"debate_rounds": 1, "committee_roles": ["architect", "qaengineer"]},
        )
        self.assertEqual(debate_res.status_code, 200)
        debate_data = debate_res.json()
        self.assertEqual(debate_data["status"], "success")
        self.assertIn("debate", debate_data)
        self.assertEqual(debate_data["debate"]["consensus_scorecard"]["decision"], "CONSENSUS_APPROVED")
        self.assertEqual(len(debate_data["debate"]["rounds"]), 1)

        # 3. Verify task detail includes committee debate
        get_res = client.get(f"/v1/pipeline/tasks/{task_id}")
        self.assertEqual(get_res.status_code, 200)
        detail = get_res.json()
        self.assertIsNotNone(detail["committee_debate"])
        self.assertEqual(detail["committee_debate"]["task_id"], task_id)


if __name__ == "__main__":
    unittest.main()
