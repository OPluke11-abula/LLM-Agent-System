"""Tests for Phase 106 Task 106-03 Concurrent Multi-Agent Worktrees & UnifiedPolicyGate Arbitration."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from agent_workspace.core.git_worktree import GitWorktreeManager
from agent_workspace.core.pipeline.manager import CodingPipelineManager
from agent_workspace.core.pipeline.models import (
    CodingTaskRequest,
    ScopedMutationPlan,
    WorktreeSessionConfig,
)


class TestConcurrentMultiAgentWorktrees(unittest.TestCase):
    """Verifies concurrent role worktrees, policy gate boundaries, and overlap arbitration."""

    def setUp(self):
        self.mock_wt = MagicMock(spec=GitWorktreeManager)
        self.pipeline = CodingPipelineManager(
            workspace_path=".",
            worktree_manager=self.mock_wt,
        )

    def test_concurrent_pipeline_detects_policy_gate_scope_violation(self):
        """BACKEND_INFRA_AGENT attempting to edit UI file is rejected by policy gate."""
        req = CodingTaskRequest(
            task_id="task-concurrent-1",
            requirement_prompt="Add fullstack feature",
            target_branch="feat/fullstack",
            base_branch="main",
            repository_path=".",
        )
        plans = {
            "BACKEND_INFRA_AGENT": ScopedMutationPlan(
                task_id="task-concurrent-1",
                plan_summary="Add backend logic",
                assigned_role="BACKEND_INFRA_AGENT",
                target_files=["viewer/src/App.tsx"],  # VIOLATION: BACKEND_INFRA_AGENT forbidden from viewer/
                structural_diff_preview="diff",
                human_approved=True,
                approval_token="GATE_TOKEN_1",
            ),
        }
        res = self.pipeline.execute_concurrent_role_pipeline("task-concurrent-1", req, plans)
        self.assertFalse(res["success"])
        self.assertIn("Policy Gate violation", res["error"])

    def test_concurrent_pipeline_detects_file_overlap_conflict(self):
        """Two roles targeting the same file triggers arbitration conflict."""
        req = CodingTaskRequest(
            task_id="task-concurrent-2",
            requirement_prompt="Add feature",
            target_branch="feat/feature",
            base_branch="main",
            repository_path=".",
        )
        plans = {
            "BACKEND_INFRA_AGENT": ScopedMutationPlan(
                task_id="task-concurrent-2",
                plan_summary="Add backend logic",
                assigned_role="BACKEND_INFRA_AGENT",
                target_files=["agent_workspace/shared.py"],
                structural_diff_preview="diff",
                human_approved=True,
                approval_token="GATE_TOKEN_1",
            ),
            "DOMAIN_LOGIC_AGENT": ScopedMutationPlan(
                task_id="task-concurrent-2",
                plan_summary="Update domain logic",
                assigned_role="DOMAIN_LOGIC_AGENT",
                target_files=["agent_workspace/shared.py"],  # OVERLAP
                structural_diff_preview="diff",
                human_approved=True,
                approval_token="GATE_TOKEN_2",
            ),
        }
        res = self.pipeline.execute_concurrent_role_pipeline("task-concurrent-2", req, plans)
        self.assertFalse(res["success"])
        self.assertIn("arbitration conflict", res["error"])

    def test_concurrent_pipeline_successful_execution_and_squash(self):
        """Non-overlapping BACKEND_INFRA_AGENT and UI_UX_AGENT execute in isolated worktrees and squash merge."""
        req = CodingTaskRequest(
            task_id="task-concurrent-3",
            requirement_prompt="Add decoupled feature",
            target_branch="feat/concurrent-ok",
            base_branch="main",
            repository_path=".",
        )
        plans = {
            "BACKEND_INFRA_AGENT": ScopedMutationPlan(
                task_id="task-concurrent-3",
                plan_summary="Backend additions",
                assigned_role="BACKEND_INFRA_AGENT",
                target_files=["agent_workspace/core/new_feature.py"],
                structural_diff_preview="diff",
                human_approved=True,
                approval_token="GATE_TOKEN_1",
            ),
            "UI_UX_AGENT": ScopedMutationPlan(
                task_id="task-concurrent-3",
                plan_summary="Frontend additions",
                assigned_role="UI_UX_AGENT",
                target_files=["viewer/src/components/NewFeature.tsx"],
                structural_diff_preview="diff",
                human_approved=True,
                approval_token="GATE_TOKEN_2",
            ),
        }

        # Mock worktree sessions
        be_session = WorktreeSessionConfig(
            session_id="wt_be_123",
            worktree_path="/tmp/wt_be",
            branch_name="task_backend_infra_agent_123",
            base_commit="sha_base",
        )
        fe_session = WorktreeSessionConfig(
            session_id="wt_fe_456",
            worktree_path="/tmp/wt_fe",
            branch_name="task_ui_ux_agent_456",
            base_commit="sha_base",
        )
        self.mock_wt.create_multi_agent_worktrees.return_value = {
            "BACKEND_INFRA_AGENT": be_session,
            "UI_UX_AGENT": fe_session,
        }
        self.mock_wt.commit_changes.side_effect = ["sha_be_commit", "sha_fe_commit"]
        self.mock_wt.get_diff.return_value = "diff_content"
        self.mock_wt.squash_merge_worktree_branch.return_value = (True, "sha_squash_merged")

        res = self.pipeline.execute_concurrent_role_pipeline("task-concurrent-3", req, plans)
        self.assertTrue(res["success"])
        self.assertEqual(res["roles"], ["BACKEND_INFRA_AGENT", "UI_UX_AGENT"])
        self.assertEqual(res["arbitrated_files_count"], 2)
        self.mock_wt.cleanup_worktree.assert_any_call(be_session)
        self.mock_wt.cleanup_worktree.assert_any_call(fe_session)


if __name__ == "__main__":
    unittest.main()
