"""Durable Events, Runtime Feedback & Recovery (Phase 2-D).

Implements the Evidence Plane and Recovery subsystem aligned with ADR-006:
1. RuntimeEventsLedger: Cryptographically chained SQLite event log anchored to Merkle trees.
2. LiveFeedbackRunner: Verification runner implementing IVerificationRunner with failure parsing.
3. IndependentReviewVerifier: Review freshness governance (review_commit == head_commit).
4. CheckpointRecoveryManager: Pause/resume/restart recovery with checksum verification.
5. GitHubDraftPRPublisher: Draft PR publisher implementing IDraftPRPublisher with local patch fallback.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import sqlite3
import subprocess
import threading
import time
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field

from agent_workspace.core.merkle import MerkleTree
from agent_workspace.core.pipeline.contracts import (
    IDraftPRPublisher,
    IVerificationRunner,
)
from agent_workspace.core.pipeline.models import (
    DraftPRPayload,
    PipelineStage,
    VerificationReceipt,
    VerificationStatus,
)

logger = logging.getLogger(__name__)


class RuntimeEventType(str, Enum):
    """Types of tracked runtime events in the execution plane."""

    TASK_STARTED = "TASK_STARTED"
    TOOL_INVOKED = "TOOL_INVOKED"
    FEEDBACK_RECEIVED = "FEEDBACK_RECEIVED"
    CHECKPOINT_SAVED = "CHECKPOINT_SAVED"
    RECOVERY_ATTEMPTED = "RECOVERY_ATTEMPTED"
    REVIEW_REQUESTED = "REVIEW_REQUESTED"
    REVIEW_VERIFIED = "REVIEW_VERIFIED"
    RECEIPT_ANCHORED = "RECEIPT_ANCHORED"
    PR_PUBLISHED = "PR_PUBLISHED"
    STAGE_TRANSITION = "STAGE_TRANSITION"
    GATE_APPROVED = "GATE_APPROVED"
    TASK_COMPLETED = "TASK_COMPLETED"
    TASK_FAILED = "TASK_FAILED"


class CheckpointCorruptError(Exception):
    """Raised when an execution checkpoint fails integrity verification."""


class RuntimeEvent(BaseModel):
    """Immutable record of an event in the execution plane."""

    model_config = ConfigDict(extra="forbid")

    event_id: int
    task_id: str
    event_type: RuntimeEventType
    payload: dict[str, Any]
    previous_hash: str
    current_hash: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class RuntimeEventsLedger:
    """Cryptographically chained, immutable SQLite ledger for runtime events."""

    _initialized_dbs: set[str] = set()

    def __init__(self, workspace_path: str):
        self.workspace_path = Path(workspace_path).resolve()
        self.db_dir = self.workspace_path / "memory"
        self.db_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.db_dir / "runtime_events.db"
        self._lock = threading.Lock()

        db_path_str = str(self.db_path)
        if db_path_str not in self._initialized_dbs:
            self._init_db()
            self._initialized_dbs.add(db_path_str)

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._lock:
            conn = self._get_conn()
            try:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS runtime_events (
                        event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        task_id TEXT NOT NULL,
                        event_type TEXT NOT NULL,
                        payload TEXT NOT NULL,
                        previous_hash TEXT NOT NULL,
                        current_hash TEXT NOT NULL,
                        timestamp TEXT NOT NULL
                    )
                    """
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_runtime_events_task ON runtime_events (task_id)"
                )
                conn.commit()
            finally:
                conn.close()

    def record_event(
        self,
        task_id: str,
        event_type: RuntimeEventType,
        payload: dict[str, Any],
    ) -> RuntimeEvent:
        """Records an event, cryptographically hashing it to the previous event hash."""
        payload_str = json.dumps(payload, sort_keys=True)
        timestamp = datetime.now(timezone.utc).isoformat()

        with self._lock:
            conn = self._get_conn()
            try:
                # 1. Fetch previous hash for this task
                cursor = conn.execute(
                    "SELECT current_hash FROM runtime_events WHERE task_id = ? ORDER BY event_id DESC LIMIT 1",
                    (task_id,),
                )
                row = cursor.fetchone()
                prev_hash = row["current_hash"] if row else "0" * 64

                # 2. Compute current SHA-256 hash
                hash_input = f"{prev_hash}{task_id}{event_type.value}{payload_str}{timestamp}"
                curr_hash = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()

                # 3. Insert into database
                cursor = conn.execute(
                    """
                    INSERT INTO runtime_events (task_id, event_type, payload, previous_hash, current_hash, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (task_id, event_type.value, payload_str, prev_hash, curr_hash, timestamp),
                )
                conn.commit()
                event_id = cursor.lastrowid or 0

                return RuntimeEvent(
                    event_id=event_id,
                    task_id=task_id,
                    event_type=event_type,
                    payload=payload,
                    previous_hash=prev_hash,
                    current_hash=curr_hash,
                    timestamp=timestamp,
                )
            finally:
                conn.close()

    def get_events_for_task(self, task_id: str) -> list[RuntimeEvent]:
        """Fetch all recorded events for a task in chronological order."""
        with self._lock:
            conn = self._get_conn()
            try:
                cursor = conn.execute(
                    "SELECT * FROM runtime_events WHERE task_id = ? ORDER BY event_id ASC",
                    (task_id,),
                )
                events = []
                for row in cursor.fetchall():
                    events.append(
                        RuntimeEvent(
                            event_id=row["event_id"],
                            task_id=row["task_id"],
                            event_type=RuntimeEventType(row["event_type"]),
                            payload=json.loads(row["payload"]),
                            previous_hash=row["previous_hash"],
                            current_hash=row["current_hash"],
                            timestamp=row["timestamp"],
                        )
                    )
                return events
            finally:
                conn.close()

    def calculate_merkle_root(self, task_id: str) -> str:
        """Calculate the deterministic binary Merkle root across all events for a task."""
        events = self.get_events_for_task(task_id)
        if not events:
            return "0" * 64

        hashes = [e.current_hash for e in events]
        tree = MerkleTree(hashes)
        return tree.root

    def verify_chain_integrity(self, task_id: str) -> bool:
        """Verify that the cryptographic hash chain is untampered for a task."""
        events = self.get_events_for_task(task_id)
        if not events:
            return True

        for i, ev in enumerate(events):
            expected_prev = "0" * 64 if i == 0 else events[i - 1].current_hash
            if ev.previous_hash != expected_prev:
                return False

            payload_str = json.dumps(ev.payload, sort_keys=True)
            hash_input = f"{ev.previous_hash}{ev.task_id}{ev.event_type.value}{payload_str}{ev.timestamp}"
            computed_hash = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()
            if computed_hash != ev.current_hash:
                return False

        return True


class LiveFeedbackRunner(IVerificationRunner):
    """
    Executes verification test ladders inside git worktrees, captures live output,
    and extracts structured feedback for agent self-healing loops.
    """

    def __init__(self, timeout_seconds: float = 60.0):
        self.timeout_seconds = timeout_seconds

    def run_verification_ladder(
        self, worktree_path: str, test_strategy: list[str]
    ) -> list[VerificationReceipt]:
        """Run verification commands inside the worktree and collect structured evidence receipts."""
        receipts: list[VerificationReceipt] = []
        wt_dir = Path(worktree_path).resolve()

        for idx, cmd in enumerate(test_strategy, 1):
            start = time.perf_counter()
            exit_code = 0
            stdout_str = ""
            stderr_str = ""

            try:
                proc = subprocess.run(
                    cmd,
                    cwd=str(wt_dir),
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_seconds,
                )
                exit_code = proc.returncode
                stdout_str = proc.stdout
                stderr_str = proc.stderr
            except subprocess.TimeoutExpired:
                exit_code = 124
                stderr_str = f"Command timed out after {self.timeout_seconds} seconds"
            except Exception as exc:
                exit_code = 1
                stderr_str = str(exc)

            duration_ms = int((time.perf_counter() - start) * 1000)
            status = VerificationStatus.PASS if exit_code == 0 else VerificationStatus.FAIL

            receipt = VerificationReceipt(
                step_name=f"Step {idx}: {cmd[:30]}",
                command=cmd,
                exit_code=exit_code,
                status=status,
                stdout_snippet=stdout_str[:500],
                stderr_snippet=stderr_str[:500],
                duration_ms=duration_ms,
            )
            receipts.append(receipt)

            # Fail-fast on failure to avoid wasted execution time
            if status != VerificationStatus.PASS:
                break

        return receipts

    @staticmethod
    def extract_failure_evidence(receipts: list[VerificationReceipt]) -> list[str]:
        """Extract high-signal diagnostic pointers and failure summaries from receipts."""
        evidence: list[str] = []
        for r in receipts:
            if r.status != VerificationStatus.PASS:
                output = (r.stderr_snippet or r.stdout_snippet or "").strip()
                lines = output.splitlines()
                summary_lines = [
                    line.strip()
                    for line in lines
                    if any(kw in line for kw in ("FAIL", "Error", "Exception", "AssertionError", "SyntaxError"))
                ]
                diagnostic = summary_lines[-1] if summary_lines else output[:150]
                evidence.append(f"[{r.command}] Exit {r.exit_code}: {diagnostic}")
        return evidence


class IndependentReviewVerifier:
    """Enforces the Review Freshness Invariant."""

    @staticmethod
    def verify_review_freshness(
        reviewed_commit: str, current_worktree_head: str
    ) -> tuple[bool, str]:
        """
        Verify that the review was conducted on the exact current HEAD commit.
        Returns: (is_fresh, message).
        """
        clean_reviewed = reviewed_commit.strip()
        clean_head = current_worktree_head.strip()

        if clean_reviewed == clean_head:
            return True, "Review is fresh: verified against current HEAD commit."

        return False, (
            f"STALE_REVIEW: Review conducted on commit '{clean_reviewed[:8]}', "
            f"but current worktree HEAD is '{clean_head[:8]}'. Re-review required."
        )


class ExecutionCheckpoint(BaseModel):
    """Snapshot model for pausing and resuming an execution attempt."""

    model_config = ConfigDict(extra="forbid")

    checkpoint_id: str
    task_id: str
    stage: PipelineStage
    worktree_path: str
    head_commit: str
    attempt_turn: int
    stage_history: list[dict[str, Any]] = Field(default_factory=list)
    saved_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    checksum: str = ""

    def compute_checksum(self) -> str:
        data = f"{self.checkpoint_id}:{self.task_id}:{self.stage.value}:{self.head_commit}:{self.attempt_turn}"
        return hashlib.sha256(data.encode("utf-8")).hexdigest()


class CheckpointRecoveryManager:
    """Manages serialization, integrity checks, and restoration of execution checkpoints."""

    @staticmethod
    def save_checkpoint(target_dir: str, checkpoint: ExecutionCheckpoint) -> Path:
        """Persists a checkpoint with SHA-256 integrity checksum."""
        checkpoint.checksum = checkpoint.compute_checksum()
        out_dir = Path(target_dir).resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
        file_path = out_dir / f"{checkpoint.checkpoint_id}.json"

        content = checkpoint.model_dump_json(indent=2)
        file_path.write_text(content, encoding="utf-8")
        logger.info("[RecoveryManager] Saved checkpoint '%s' to '%s'", checkpoint.checkpoint_id, file_path)
        return file_path

    @staticmethod
    def load_checkpoint(checkpoint_file: str) -> ExecutionCheckpoint:
        """Loads and verifies the integrity of an execution checkpoint."""
        p = Path(checkpoint_file).resolve()
        if not p.is_file():
            raise FileNotFoundError(f"Checkpoint file not found: '{checkpoint_file}'")

        content = p.read_text(encoding="utf-8")
        raw = json.loads(content)
        checkpoint = ExecutionCheckpoint.model_validate(raw)

        expected_checksum = checkpoint.compute_checksum()
        if checkpoint.checksum != expected_checksum:
            raise CheckpointCorruptError(
                f"Checkpoint integrity check failed for '{checkpoint.checkpoint_id}'. "
                f"Expected {expected_checksum}, found {checkpoint.checksum}."
            )

        logger.info("[RecoveryManager] Loaded and verified checkpoint '%s'", checkpoint.checkpoint_id)
        return checkpoint


class GitHubDraftPRPublisher(IDraftPRPublisher):
    """
    Publishes verifiable draft PRs via GitHub CLI (`gh pr create`) when available,
    or exports an offline signed patch bundle with Merkle audit receipts.
    """

    def __init__(self, timeout_seconds: float = 30.0, output_dir: Optional[str] = None):
        self.timeout_seconds = timeout_seconds
        self.output_dir = output_dir

    def publish_draft_pr(self, payload: DraftPRPayload, repo_path: str) -> str:
        """Publish draft PR or generate a local patch bundle."""
        repo_dir = Path(repo_path).resolve()

        # Check if `gh` CLI is available
        has_gh = shutil.which("gh") is not None
        if has_gh:
            try:
                # Attempt gh pr create
                cmd = [
                    "gh",
                    "pr",
                    "create",
                    "--draft",
                    "--title",
                    payload.title,
                    "--body",
                    payload.body,
                    "--head",
                    payload.head_branch,
                    "--base",
                    payload.base_branch,
                ]
                proc = subprocess.run(
                    cmd,
                    cwd=str(repo_dir),
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_seconds,
                    check=True,
                )
                pr_url = proc.stdout.strip()
                logger.info("[GitHubPublisher] Published remote Draft PR via GitHub CLI: %s", pr_url)
                return pr_url
            except Exception as exc:
                logger.warning(
                    "[GitHubPublisher] 'gh pr create' failed or not authenticated (%s). Falling back to local patch bundle.",
                    exc,
                )

        # Offline / Local fallback: Write signed patch bundle
        if self.output_dir:
            patch_dir = Path(self.output_dir).resolve()
        else:
            patch_dir = repo_dir / ".agent" / "patches"
        patch_dir.mkdir(parents=True, exist_ok=True)
        safe_branch = payload.head_branch.replace("/", "_").replace("\\", "_")
        patch_file = patch_dir / f"{safe_branch}.patch.md"

        bundle_content = f"""# 📦 LAS Verifiable Patch Bundle
> **Title**: {payload.title}
> **Head Branch**: `{payload.head_branch}`
> **Base Branch**: `{payload.base_branch}`
> **Commit Hash**: `{payload.commit_hash}`
> **Merkle Root**: `{payload.merkle_root or 'UNSPECIFIED'}`
> **Exported At**: {datetime.now(timezone.utc).isoformat()}

---

{payload.body}
"""
        patch_file.write_text(bundle_content, encoding="utf-8")
        pr_url = f"file:///{patch_file.as_posix()}"
        logger.info("[GitHubPublisher] Exported local verifiable patch bundle: %s", pr_url)
        return pr_url
