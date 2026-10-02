"""Native Git Worktree Manager for LAS (Phase 2-A).

Implements IWorktreeManager with native git CLI invocations, providing physical
isolation for agent execution attempts while strictly protecting the developer's
canonical checkout from uncommitted pollution or accidental branch mutations.
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Optional

from agent_workspace.core.pipeline.contracts import IWorktreeManager
from agent_workspace.core.pipeline.models import WorktreeSessionConfig

logger = logging.getLogger(__name__)


class GitWorktreeManager(IWorktreeManager):
    """Manages the full lifecycle of isolated git worktrees."""

    def __init__(
        self,
        base_worktrees_dir: Optional[str] = None,
        timeout_seconds: float = 30.0,
    ):
        """Initialize worktree manager.

        Args:
            base_worktrees_dir: Optional custom base directory for worktrees.
                If None, defaults to a sibling directory or secure tempdir.
            timeout_seconds: Subprocess execution timeout in seconds.
        """
        self.base_worktrees_dir = base_worktrees_dir
        self.timeout_seconds = timeout_seconds

    def _run_git(
        self, cwd: str, args: list[str], check: bool = True
    ) -> subprocess.CompletedProcess[str]:
        cmd = ["git"] + args
        try:
            return subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                check=check,
                timeout=self.timeout_seconds,
            )
        except subprocess.CalledProcessError as exc:
            logger.error("Git command failed in %s: %s; stderr: %s", cwd, cmd, exc.stderr)
            raise RuntimeError(
                f"Git command '{' '.join(cmd)}' failed in '{cwd}' with code {exc.returncode}: {exc.stderr.strip()}"
            ) from exc
        except subprocess.TimeoutExpired as exc:
            logger.error("Git command timed out in %s: %s", cwd, cmd)
            raise TimeoutError(f"Git command '{' '.join(cmd)}' timed out") from exc

    def _resolve_worktree_path(self, repo_path: str, session_id: str) -> str:
        if self.base_worktrees_dir:
            base = os.path.abspath(self.base_worktrees_dir)
            os.makedirs(base, exist_ok=True)
            return os.path.join(base, session_id)

        # Default: isolate in dedicated system temp or sibling worktree path
        temp_base = os.path.join(tempfile.gettempdir(), "las_worktrees")
        os.makedirs(temp_base, exist_ok=True)
        return os.path.join(temp_base, f"{Path(repo_path).name}_{session_id}")

    def create_worktree(
        self, repo_path: str, branch_name: str, base_ref: str = "main"
    ) -> WorktreeSessionConfig:
        """Create a dedicated, isolated git worktree branch without dirtying the main working tree."""
        abs_repo = os.path.abspath(repo_path)
        if not os.path.isdir(abs_repo):
            raise FileNotFoundError(f"Target repository not found: {abs_repo}")

        # Verify git repository
        self._run_git(abs_repo, ["rev-parse", "--git-dir"])

        session_id = f"wt_{uuid.uuid4().hex[:10]}"
        worktree_path = self._resolve_worktree_path(abs_repo, session_id)

        # Clean existing path if collision
        if os.path.exists(worktree_path):
            shutil.rmtree(worktree_path, ignore_errors=True)

        # Resolve base commit SHA from base_ref
        try:
            base_commit = self._run_git(abs_repo, ["rev-parse", base_ref]).stdout.strip()
        except RuntimeError:
            # Fallback to current HEAD if base_ref does not exist directly
            base_commit = self._run_git(abs_repo, ["rev-parse", "HEAD"]).stdout.strip()

        # Check if target branch already exists; preserve existing branch without destructive -D
        branch_check = self._run_git(abs_repo, ["branch", "--list", branch_name], check=False)
        target_branch = branch_name
        is_new_branch = True

        if branch_check.stdout.strip():
            # Check if existing branch points to base_commit
            try:
                branch_sha = self._run_git(abs_repo, ["rev-parse", branch_name]).stdout.strip()
            except RuntimeError:
                branch_sha = ""

            # Check if already checked out in any worktree
            wt_list = self._run_git(abs_repo, ["worktree", "list", "--porcelain"], check=False).stdout
            branch_checked_out = f"branch refs/heads/{branch_name}" in wt_list

            if branch_sha == base_commit and not branch_checked_out:
                # Safe to attach existing branch directly without creating a duplicate branch
                is_new_branch = False
                target_branch = branch_name
                logger.info(
                    "Target branch '%s' already exists at base commit '%s'; attaching to worktree.",
                    branch_name,
                    base_commit,
                )
            else:
                # Existing branch has divergent commits or is checked out elsewhere:
                # PROTECT IT: Never use `branch -D`. Use an isolated session branch suffix.
                target_branch = f"{branch_name}_{session_id}"
                is_new_branch = True
                logger.warning(
                    "Target branch '%s' exists with divergent commits or is in use; preserving it and creating isolated session branch '%s'",
                    branch_name,
                    target_branch,
                )

        # Execute git worktree add
        logger.info(
            "Creating isolated worktree for branch '%s' at '%s' off '%s'",
            target_branch,
            worktree_path,
            base_ref,
        )
        if is_new_branch:
            self._run_git(
                abs_repo,
                ["worktree", "add", "-b", target_branch, worktree_path, base_commit],
            )
        else:
            self._run_git(
                abs_repo,
                ["worktree", "add", worktree_path, target_branch],
            )

        return WorktreeSessionConfig(
            session_id=session_id,
            worktree_path=worktree_path,
            branch_name=target_branch,
            base_commit=base_commit,
            is_isolated=True,
        )

    def cleanup_worktree(
        self, session: WorktreeSessionConfig, remove_branch_on_abort: bool = False
    ) -> bool:
        """Clean up and prune the isolated worktree directory and optional aborted branch."""
        worktree_path = session.worktree_path
        repo_path = None

        # Find repo parent from git worktree link if possible
        git_link = os.path.join(worktree_path, ".git")
        if os.path.isfile(git_link):
            try:
                with open(git_link, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                if content.startswith("gitdir:"):
                    gitdir = content[len("gitdir:") :].strip()
                    # gitdir is inside <repo>/.git/worktrees/<name>
                    repo_git = Path(gitdir).parents[1]
                    if repo_git.name == ".git":
                        repo_path = str(repo_git.parent)
            except Exception as exc:
                logger.warning("Could not parse gitdir from .git link: %s", exc)

        logger.info("Tearing down worktree at '%s'", worktree_path)

        # 1. Attempt git worktree remove from main repo
        if repo_path and os.path.isdir(repo_path):
            self._run_git(repo_path, ["worktree", "remove", "--force", worktree_path], check=False)
            self._run_git(repo_path, ["worktree", "prune"], check=False)
            if remove_branch_on_abort:
                self._run_git(repo_path, ["branch", "-D", session.branch_name], check=False)

        # 2. Filesystem fallback cleanup
        if os.path.exists(worktree_path):
            def _remove_readonly(func, path, _):
                try:
                    os.chmod(path, 0o777)
                    func(path)
                except Exception:
                    pass

            shutil.rmtree(worktree_path, onerror=_remove_readonly)

        return not os.path.exists(worktree_path)

    def get_diff(self, session: WorktreeSessionConfig) -> str:
        """Return the unified git diff of modifications inside the worktree against base commit."""
        wt_path = session.worktree_path
        if not os.path.isdir(wt_path):
            raise FileNotFoundError(f"Worktree path does not exist: {wt_path}")

        # Capture both tracked diff against base commit and untracked files
        diff_res = self._run_git(wt_path, ["diff", session.base_commit], check=False)
        diff_text = diff_res.stdout

        # Also inspect untracked files
        status_res = self._run_git(wt_path, ["status", "--porcelain"], check=False)
        untracked = [
            line[3:].strip()
            for line in status_res.stdout.splitlines()
            if line.startswith("??")
        ]

        if untracked:
            untracked_header = "\n# Untracked files:\n" + "\n".join(f"# + {f}" for f in untracked)
            return (diff_text + untracked_header).strip()

        return diff_text.strip()

    def commit_changes(
        self, session: WorktreeSessionConfig, commit_message: str
    ) -> str:
        """Stage and commit modified files inside the worktree, returning the new commit SHA."""
        wt_path = session.worktree_path
        if not os.path.isdir(wt_path):
            raise FileNotFoundError(f"Worktree path does not exist: {wt_path}")

        # Stage all changes
        self._run_git(wt_path, ["add", "-A"])

        # Check if there are changes to commit
        diff_cached = self._run_git(wt_path, ["diff", "--cached", "--quiet"], check=False)
        if diff_cached.returncode != 0:
            # Changes exist, commit them
            self._run_git(wt_path, ["commit", "-m", commit_message])

        # Return new HEAD SHA
        new_commit = self._run_git(wt_path, ["rev-parse", "HEAD"]).stdout.strip()
        return new_commit

    def create_multi_agent_worktrees(
        self,
        repo_path: str,
        roles: list[str],
        base_ref: str = "main",
    ) -> dict[str, WorktreeSessionConfig]:
        """
        Creates isolated concurrent worktrees for multiple roles (e.g. BackendDev, FrontendDev).
        Returns a dict mapping role -> WorktreeSessionConfig.
        """
        sessions: dict[str, WorktreeSessionConfig] = {}
        for role in roles:
            sanitized_role = re.sub(r"[^a-zA-Z0-9_\-]", "_", role.lower())
            branch_name = f"task_{sanitized_role}_{uuid.uuid4().hex[:6]}"
            session = self.create_worktree(repo_path, branch_name=branch_name, base_ref=base_ref)
            sessions[role] = session
        return sessions

    def squash_merge_worktree_branch(
        self,
        repo_path: str,
        source_branch: str,
        target_branch: str = "main",
        commit_message: Optional[str] = None,
    ) -> tuple[bool, str]:
        """
        Squash merges a completed worktree branch into the target branch.
        Returns (success: bool, commit_or_error: str).
        """
        abs_repo = os.path.abspath(repo_path)
        msg = commit_message or f"chore(worktree): squash merge {source_branch} into {target_branch}"

        try:
            curr_branch = self._run_git(abs_repo, ["rev-parse", "--abbrev-ref", "HEAD"]).stdout.strip()

            if curr_branch != target_branch:
                self._run_git(abs_repo, ["checkout", target_branch])

            merge_res = self._run_git(abs_repo, ["merge", "--squash", source_branch], check=False)
            if merge_res.returncode != 0:
                self._run_git(abs_repo, ["reset", "--hard", "HEAD"], check=False)
                return False, f"Squash merge conflict or failure: {merge_res.stderr.strip()}"

            diff_cached = self._run_git(abs_repo, ["diff", "--cached", "--quiet"], check=False)
            if diff_cached.returncode != 0:
                self._run_git(abs_repo, ["commit", "-m", msg])
                new_sha = self._run_git(abs_repo, ["rev-parse", "HEAD"]).stdout.strip()
                return True, new_sha
            else:
                return True, "NOOP_NO_CHANGES"

        except Exception as exc:
            logger.error("Error squash merging branch '%s': %s", source_branch, exc)
            return False, str(exc)

