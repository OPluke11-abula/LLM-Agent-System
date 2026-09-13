"""Abstract interface contracts for the LAS Autonomous Coding Pipeline (Phase 1).

Defines the behavioral boundaries to be implemented by Phase 2 (P2):
- Git Worktree isolation management
- Scoped Agent mutation execution
- Verification ladder execution and receipt collection
- Draft PR publication and cognitive relay sync
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional

from .models import (
    CodingTaskRequest,
    WorktreeSessionConfig,
    ScopedMutationPlan,
    VerificationReceipt,
    DraftPRPayload,
)


class IWorktreeManager(ABC):
    """Interface for managing isolated git worktree environments."""

    @abstractmethod
    def create_worktree(
        self, repo_path: str, branch_name: str, base_ref: str = "main"
    ) -> WorktreeSessionConfig:
        """Create a dedicated, isolated git worktree branch without dirtying the main working tree."""
        raise NotImplementedError

    @abstractmethod
    def cleanup_worktree(
        self, session: WorktreeSessionConfig, remove_branch_on_abort: bool = False
    ) -> bool:
        """Clean up and prune the isolated worktree directory."""
        raise NotImplementedError

    @abstractmethod
    def get_diff(self, session: WorktreeSessionConfig) -> str:
        """Return the unified git diff of modifications inside the worktree."""
        raise NotImplementedError

    @abstractmethod
    def commit_changes(
        self, session: WorktreeSessionConfig, commit_message: str
    ) -> str:
        """Stage and commit modified files inside the worktree, returning the new commit SHA."""
        raise NotImplementedError


class IScopedExecutor(ABC):
    """Interface for executing code modifications within strict role boundaries."""

    @abstractmethod
    def execute_plan(
        self, session: WorktreeSessionConfig, plan: ScopedMutationPlan
    ) -> dict[str, Any]:
        """Execute the planned code modifications inside the isolated worktree."""
        raise NotImplementedError

    @abstractmethod
    def validate_scope_compliance(
        self, role: str, target_files: list[str]
    ) -> tuple[bool, Optional[str]]:
        """Verify that the targeted files strictly respect the role's mutable boundaries."""
        raise NotImplementedError


class IVerificationRunner(ABC):
    """Interface for executing verification test ladders and collecting objective receipts."""

    @abstractmethod
    def run_verification_ladder(
        self, worktree_path: str, test_strategy: list[str]
    ) -> list[VerificationReceipt]:
        """Run verification commands inside the worktree and collect structured evidence receipts."""
        raise NotImplementedError


class IDraftPRPublisher(ABC):
    """Interface for publishing verified Draft Pull Requests and updating cognitive relay."""

    @abstractmethod
    def publish_draft_pr(
        self, payload: DraftPRPayload, repo_path: str
    ) -> str:
        """Publish the draft PR to remote repository or generate a local verifiable patch bundle."""
        raise NotImplementedError
