"""Pydantic data models for the LAS Autonomous Coding Pipeline (Phase 1).

Implements the contract for:
Requirement Intake -> Bounded Mutation -> Verification Evidence -> Draft PR.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict, Field


class PipelineStage(str, Enum):
    """Execution stages of the autonomous coding product workflow."""
    INTAKE = "INTAKE"
    PRECHECK = "PRECHECK"
    PLAN_AND_GATE = "PLAN_AND_GATE"
    ISOLATED_MUTATION = "ISOLATED_MUTATION"
    VERIFY_AND_EVIDENCE = "VERIFY_AND_EVIDENCE"
    DRAFT_PR_EXPORT = "DRAFT_PR_EXPORT"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ABORTED = "ABORTED"


class VerificationStatus(str, Enum):
    """The five standard verification statuses defined in Protocol v3.8.0."""
    PASS = "PASS"
    FAIL = "FAIL"
    BLOCKED = "BLOCKED"
    NOT_RUN = "NOT_RUN"
    UNVERIFIED = "UNVERIFIED"


class CodingTaskRequest(BaseModel):
    """Contract for incoming developer coding task requests."""
    model_config = ConfigDict(extra="forbid")

    task_id: str = Field(..., description="Unique task identifier (e.g., TASK-2026-001)")
    repository_path: str = Field(..., description="Absolute path to target git repository")
    requirement_prompt: str = Field(..., description="Natural language description of developer requirement")
    base_branch: str = Field(default="main", description="Base git branch to branch off from")
    target_branch: str = Field(..., description="Feature branch name (e.g., feat/las-task-001)")
    inspected_files: list[str] = Field(
        default_factory=list,
        description="Primary source files inspected to satisfy Anti-Summary Invariant (調研先行)"
    )
    target_files: list[str] = Field(
        default_factory=list,
        description="Files intended to be created or modified"
    )
    allowed_roles: list[str] = Field(
        default_factory=lambda: ["DOMAIN_LOGIC_AGENT", "BACKEND_INFRA_AGENT"],
        description="Designated specialist roles authorized to modify target files"
    )
    max_turns: int = Field(
        default=3,
        ge=1,
        le=5,
        description="Loop limit safety gate threshold before requiring HITL re-approval"
    )
    issue_ref: Optional[str] = Field(default=None, description="Linked issue or ticket number")
    tenant_id: str = Field(default="default_tenant", description="Tenant identifier for audit and billing")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Arbitrary extension metadata")


class WorktreeSessionConfig(BaseModel):
    """Configuration for an isolated git worktree session."""
    model_config = ConfigDict(extra="forbid")

    session_id: str
    worktree_path: str
    branch_name: str
    base_commit: str
    is_isolated: bool = True
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ScopedMutationPlan(BaseModel):
    """Structured implementation plan required by the Stop-and-Wait Architecture Gate."""
    model_config = ConfigDict(extra="forbid")

    task_id: str
    plan_summary: str
    target_files: list[str]
    assigned_role: str
    structural_diff_preview: str = ""
    edge_cases: list[str] = Field(default_factory=list)
    test_strategy: list[str] = Field(default_factory=list)
    human_approved: bool = False
    approval_token: Optional[str] = None
    approval_timestamp: Optional[str] = None


class VerificationReceipt(BaseModel):
    """Tamper-evident verification receipt recording concrete command output."""
    model_config = ConfigDict(extra="forbid")

    step_name: str
    command: str
    exit_code: int
    status: VerificationStatus
    stdout_snippet: str = ""
    stderr_snippet: str = ""
    duration_ms: int = 0
    merkle_hash: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class DraftPRPayload(BaseModel):
    """Contract for the generated Draft Pull Request."""
    model_config = ConfigDict(extra="forbid")

    title: str
    body: str
    head_branch: str
    base_branch: str
    commit_hash: str
    changed_files: list[str] = Field(default_factory=list)
    receipts: list[VerificationReceipt] = Field(default_factory=list)
    pr_url: Optional[str] = None
    is_draft: bool = True
    merkle_root: Optional[str] = None


class CodingPipelineResult(BaseModel):
    """Comprehensive result emitted upon completion or termination of the coding pipeline."""
    model_config = ConfigDict(extra="forbid")

    task_id: str
    status: VerificationStatus
    current_stage: PipelineStage
    stage_history: list[dict[str, Any]] = Field(default_factory=list)
    worktree_config: Optional[WorktreeSessionConfig] = None
    mutation_plan: Optional[ScopedMutationPlan] = None
    receipts: list[VerificationReceipt] = Field(default_factory=list)
    pr_payload: Optional[DraftPRPayload] = None
    error_message: Optional[str] = None
    audit_events: list[dict[str, Any]] = Field(default_factory=list)
