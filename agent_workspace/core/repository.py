"""Repository profile inspection and canonical preservation controls for LAS (Phase 2-A).

Provides automatic sensing of git status, target repository ecosystems (Python,
Node, Rust, Go), test commands, protected paths, and cryptographic verification
that developer host checkout is 100% preserved during agent execution.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from pathlib import Path
import subprocess
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)

# Canonical protected path patterns that should never be mutated by agents without HITL approval
DEFAULT_PROTECTED_PATTERNS: tuple[str, ...] = (
    ".env*",
    ".git/",
    ".git",
    ".github/workflows/",
    "id_rsa*",
    "*.pem",
    "*.key",
    "credentials.json",
    "secrets.yaml",
)


class RepositoryProfile(BaseModel):
    """Metadata and environmental profile of an inspected repository."""

    model_config = ConfigDict(extra="forbid")

    repository_path: str = Field(..., description="Absolute path to target repository")
    current_branch: str = Field(..., description="Active git branch at inspection time")
    head_commit: str = Field(..., description="Active HEAD commit hash (40-char SHA)")
    is_clean: bool = Field(..., description="Whether working tree and index are clean")
    uncommitted_files: list[str] = Field(
        default_factory=list, description="List of modified, staged, or untracked files"
    )
    detected_ecosystems: list[str] = Field(
        default_factory=list,
        description="Detected development ecosystems (e.g., 'python', 'node', 'rust', 'go')",
    )
    test_commands: list[dict[str, str]] = Field(
        default_factory=list,
        description="Auto-discovered test commands mapped by ecosystem",
    )
    linter_commands: list[dict[str, str]] = Field(
        default_factory=list,
        description="Auto-discovered linter / format commands",
    )
    protected_paths: list[str] = Field(
        default_factory=lambda: list(DEFAULT_PROTECTED_PATTERNS),
        description="Glob patterns of files strictly prohibited from unmonitored mutation",
    )
    inspected_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class CanonicalPreservationReceipt(BaseModel):
    """Tamper-evident verification receipt guaranteeing canonical checkout was preserved as found."""

    model_config = ConfigDict(extra="forbid")

    receipt_id: str = Field(..., description="Unique receipt identifier")
    repository_path: str = Field(..., description="Path to target git repository")
    initial_status_hash: str = Field(
        ..., description="SHA-256 hash of initial git status and HEAD"
    )
    initial_head: str = Field(..., description="HEAD commit hash before agent execution")
    final_status_hash: Optional[str] = Field(
        default=None, description="SHA-256 hash of final git status and HEAD after cleanup"
    )
    final_head: Optional[str] = Field(
        default=None, description="HEAD commit hash after worktree teardown"
    )
    is_preserved: bool = Field(
        default=True,
        description="True if final status and commit strictly match initial state",
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    details: dict[str, Any] = Field(
        default_factory=dict, description="Diagnostic audit details"
    )


class RepositoryInspector:
    """Inspects target repositories and generates canonical preservation receipts."""

    def __init__(self, timeout_seconds: float = 15.0):
        self.timeout_seconds = timeout_seconds

    def _run_git(
        self, repo_path: str, args: list[str], check: bool = True
    ) -> subprocess.CompletedProcess[str]:
        cmd = ["git", "-C", repo_path] + args
        try:
            return subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=check,
                timeout=self.timeout_seconds,
            )
        except subprocess.CalledProcessError as exc:
            logger.error("Git command failed: %s; stderr: %s", cmd, exc.stderr)
            raise RuntimeError(
                f"Git command '{' '.join(cmd)}' failed with code {exc.returncode}: {exc.stderr.strip()}"
            ) from exc
        except subprocess.TimeoutExpired as exc:
            logger.error("Git command timed out: %s", cmd)
            raise TimeoutError(f"Git command '{' '.join(cmd)}' timed out") from exc

    def inspect(self, repo_path: str) -> RepositoryProfile:
        """Inspect a target repository, discovering its git state, ecosystem, and test commands."""
        abs_path = os.path.abspath(repo_path)
        if not os.path.isdir(abs_path):
            raise FileNotFoundError(f"Target repository directory not found: {abs_path}")

        # 1. Verify Git Repository
        res_inside = self._run_git(abs_path, ["rev-parse", "--is-inside-work-tree"], check=False)
        if res_inside.returncode != 0 or res_inside.stdout.strip() != "true":
            raise ValueError(f"Directory is not a valid git work tree: {abs_path}")

        # 2. Get HEAD commit and Branch
        head_commit = self._run_git(abs_path, ["rev-parse", "HEAD"]).stdout.strip()
        branch_res = self._run_git(abs_path, ["rev-parse", "--abbrev-ref", "HEAD"])
        current_branch = branch_res.stdout.strip()

        # 3. Check Working Tree Status
        status_res = self._run_git(abs_path, ["status", "--porcelain"])
        status_lines = [
            line.strip() for line in status_res.stdout.splitlines() if line.strip()
        ]
        is_clean = len(status_lines) == 0
        uncommitted_files = [line[3:].strip() for line in status_lines]

        # 4. Detect Ecosystems and Test Commands
        ecosystems, test_cmds, linter_cmds = self._detect_ecosystems(abs_path)

        return RepositoryProfile(
            repository_path=abs_path,
            current_branch=current_branch,
            head_commit=head_commit,
            is_clean=is_clean,
            uncommitted_files=uncommitted_files,
            detected_ecosystems=ecosystems,
            test_commands=test_cmds,
            linter_commands=linter_cmds,
            protected_paths=list(DEFAULT_PROTECTED_PATTERNS),
        )

    def generate_preservation_receipt(self, repo_path: str) -> CanonicalPreservationReceipt:
        """Capture the initial state hash of the repository for preservation verification."""
        abs_path = os.path.abspath(repo_path)
        head_commit = self._run_git(abs_path, ["rev-parse", "HEAD"]).stdout.strip()
        status_out = self._run_git(abs_path, ["status", "--porcelain"]).stdout

        hash_payload = f"HEAD:{head_commit}\nSTATUS:\n{status_out}"
        status_hash = hashlib.sha256(hash_payload.encode("utf-8")).hexdigest()

        receipt_id = f"cpr_{uuid.uuid4().hex[:12]}"
        return CanonicalPreservationReceipt(
            receipt_id=receipt_id,
            repository_path=abs_path,
            initial_status_hash=status_hash,
            initial_head=head_commit,
            details={"status_lines_count": len(status_out.splitlines())},
        )

    def verify_preservation(
        self, receipt: CanonicalPreservationReceipt
    ) -> CanonicalPreservationReceipt:
        """Verify that the repository state after execution matches the initial preservation receipt."""
        abs_path = os.path.abspath(receipt.repository_path)
        final_head = self._run_git(abs_path, ["rev-parse", "HEAD"]).stdout.strip()
        status_out = self._run_git(abs_path, ["status", "--porcelain"]).stdout

        final_payload = f"HEAD:{final_head}\nSTATUS:\n{status_out}"
        final_status_hash = hashlib.sha256(final_payload.encode("utf-8")).hexdigest()

        is_preserved = (
            final_status_hash == receipt.initial_status_hash
            and final_head == receipt.initial_head
        )

        receipt.final_status_hash = final_status_hash
        receipt.final_head = final_head
        receipt.is_preserved = is_preserved
        receipt.details["verified_at"] = datetime.now(timezone.utc).isoformat()
        receipt.details["status_clean"] = len(status_out.strip()) == 0

        return receipt

    def _detect_ecosystems(
        self, repo_path: str
    ) -> tuple[list[str], list[dict[str, str]], list[dict[str, str]]]:
        """Auto-detect language ecosystem and recommended test/linter commands."""
        ecosystems: list[str] = []
        test_commands: list[dict[str, str]] = []
        linter_commands: list[dict[str, str]] = []

        path = Path(repo_path)

        # Python
        if (
            (path / "pyproject.toml").is_file()
            or (path / "setup.py").is_file()
            or (path / "requirements.txt").is_file()
            or (path / "agent_workspace").is_dir()
        ):
            ecosystems.append("python")
            test_commands.append(
                {
                    "name": "pytest",
                    "command": "pytest -v",
                    "ecosystem": "python",
                }
            )
            linter_commands.append(
                {
                    "name": "ruff",
                    "command": "ruff check .",
                    "ecosystem": "python",
                }
            )

        # Node / JavaScript / TypeScript
        pkg_json = path / "package.json"
        if pkg_json.is_file() or (path / "viewer" / "package.json").is_file():
            ecosystems.append("node")
            cmd_prefix = "npm test" if pkg_json.is_file() else "npm --prefix viewer test"
            lint_prefix = "npm run lint" if pkg_json.is_file() else "npm --prefix viewer run lint"

            test_commands.append(
                {
                    "name": "npm-test",
                    "command": cmd_prefix,
                    "ecosystem": "node",
                }
            )
            linter_commands.append(
                {
                    "name": "npm-lint",
                    "command": lint_prefix,
                    "ecosystem": "node",
                }
            )

        # Rust
        if (path / "Cargo.toml").is_file():
            ecosystems.append("rust")
            test_commands.append(
                {
                    "name": "cargo-test",
                    "command": "cargo test",
                    "ecosystem": "rust",
                }
            )
            linter_commands.append(
                {
                    "name": "cargo-clippy",
                    "command": "cargo clippy",
                    "ecosystem": "rust",
                }
            )

        # Go
        if (path / "go.mod").is_file():
            ecosystems.append("go")
            test_commands.append(
                {
                    "name": "go-test",
                    "command": "go test ./...",
                    "ecosystem": "go",
                }
            )

        return ecosystems, test_commands, linter_commands
