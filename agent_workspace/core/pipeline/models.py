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
    COMMITTEE_DEBATE = "COMMITTEE_DEBATE"
    PLAN_AND_GATE = "PLAN_AND_GATE"
    ISOLATED_MUTATION = "ISOLATED_MUTATION"
    VERIFY_AND_EVIDENCE = "VERIFY_AND_EVIDENCE"
    SELF_HEALING = "SELF_HEALING"
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
    enable_committee: bool = Field(
        default=False,
        description="Enable multi-agent committee debate before architecture gate"
    )
    debate_rounds: int = Field(
        default=1,
        ge=1,
        le=3,
        description="Number of debate deliberation rounds"
    )
    committee_roles: list[str] = Field(
        default_factory=lambda: ["architect", "securityauditor", "qaengineer"],
        description="Specialist personas participating in the debate"
    )
    offline_mode: bool = Field(
        default=False,
        description="Enforce air-gapped local model execution via Ollama"
    )
    thinking_budget: Optional[int] = Field(
        default=None,
        description="Thinking token budget override for reasoning roles"
    )
    reasoning_effort: Optional[str] = Field(
        default=None,
        description="Reasoning intensity level: low, medium, high"
    )
    use_mesh: bool = Field(
        default=False,
        description="Offload committee reasoning and test execution across federated P2P mesh peers"
    )
    mesh_peers: list[str] = Field(
        default_factory=list,
        description="Explicit mesh peer seed addresses (e.g. host:port)"
    )
    use_raft_consensus: bool = Field(
        default=False,
        description="Enforce distributed Raft quorum consensus and replicated debate log across mesh"
    )
    enable_self_healing: bool = Field(
        default=True,
        description="Enable autonomous diagnostic extraction and corrective self-healing loop on verification failure"
    )
    max_healing_attempts: int = Field(
        default=2,
        ge=0,
        le=5,
        description="Maximum number of self-healing retry iterations before executing auto-rollback"
    )
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


class DebateSpeechTurn(BaseModel):
    """A single turn in the multi-agent committee debate."""
    model_config = ConfigDict(extra="forbid")

    speaker_role: str = Field(..., description="Role of the speaking agent (e.g., architect, securityauditor)")
    target_role: Optional[str] = Field(default=None, description="Addressed role or None if addressing the committee")
    round_index: int = Field(..., ge=1, description="1-indexed debate round number")
    turn_index: int = Field(..., ge=1, description="1-indexed turn index within the round")
    content: str = Field(..., description="Speech content containing critiques, requirements or justifications")
    critique_points: list[str] = Field(default_factory=list, description="Extracted actionable critique items")
    score_impact: float = Field(default=0.0, description="Estimated impact on composite confidence score (-1.0 to 1.0)")
    reasoning_content: Optional[str] = Field(default=None, description="Internal chain-of-thought or reasoning tokens")
    reasoning_tokens: int = Field(default=0, ge=0, description="Count of reasoning/thinking tokens consumed")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def agent_role(self) -> str:
        """Alias for speaker_role."""
        return self.speaker_role

    @property
    def speech_content(self) -> str:
        """Alias for content."""
        return self.content


class DebateRoundRecord(BaseModel):
    """Record of a complete deliberation round within the committee."""
    model_config = ConfigDict(extra="forbid")

    round_index: int = Field(..., ge=1)
    turns: list[DebateSpeechTurn] = Field(default_factory=list)
    round_summary: str = Field(default="", description="Summary of agreements and unresolved tensions in this round")


class CommitteeConsensusScorecard(BaseModel):
    """Multi-dimensional consensus scorecard synthesized by the committee."""
    model_config = ConfigDict(extra="forbid")

    architectural_integrity: float = Field(default=1.0, ge=0.0, le=1.0, description="Boundary compliance & design consistency")
    security_assurance: float = Field(default=1.0, ge=0.0, le=1.0, description="AST sandboxing, auth & zero-trust compliance")
    test_thoroughness: float = Field(default=1.0, ge=0.0, le=1.0, description="Verification ladder & edge case coverage")
    composite_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Weighted composite confidence score")
    total_reasoning_tokens: int = Field(default=0, ge=0, description="Sum of reasoning/thinking tokens consumed across deliberation turns")
    decision: str = Field(default="CONSENSUS_APPROVED", description="'CONSENSUS_APPROVED' or 'REJECTED_NEEDS_REVISION'")
    dissenting_opinions: list[str] = Field(default_factory=list, description="Unresolved critiques or minority objections")
    recommended_actions: list[str] = Field(default_factory=list, description="Directives to enrich the mutation plan")


class CommitteeDebateRecord(BaseModel):
    """Complete record of the committee debate deliberation."""
    model_config = ConfigDict(extra="forbid")

    debate_id: str = Field(..., description="Unique debate session identifier")
    task_id: str = Field(..., description="Target coding task identifier")
    committee_members: list[str] = Field(default_factory=list, description="List of participant specialist roles")
    rounds: list[DebateRoundRecord] = Field(default_factory=list)
    consensus_scorecard: CommitteeConsensusScorecard = Field(default_factory=CommitteeConsensusScorecard)
    synthesized_mutation_plan: Optional[ScopedMutationPlan] = Field(default=None, description="Plan enriched with committee findings")
    duration_ms: int = Field(default=0, description="Deliberation duration in milliseconds")
    raft_log_index: Optional[int] = Field(default=None, description="Replicated Raft log commit index")
    raft_term: Optional[int] = Field(default=None, description="Raft term under which consensus was committed")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class SelfHealingAttemptReceipt(BaseModel):
    """Telemetry and outcome receipt for an autonomous self-healing iteration."""
    model_config = ConfigDict(extra="forbid")

    attempt_index: int = Field(..., description="1-based attempt sequence number")
    failed_steps: list[str] = Field(default_factory=list, description="Names of verification ladder steps that failed")
    diagnostic_evidence: list[str] = Field(default_factory=list, description="Extracted high-signal failure messages")
    memory_precedents_used: list[str] = Field(default_factory=list, description="Historical vector memory lessons/error patterns retrieved")
    corrective_action: str = Field(default="", description="Description of corrective changes applied")
    modified_files: list[str] = Field(default_factory=list, description="Files updated during this healing attempt")
    ladder_passed: bool = Field(default=False, description="Whether re-verification succeeded")
    duration_ms: float = Field(default=0.0, description="Duration of self-healing attempt in milliseconds")


class RollbackReceipt(BaseModel):
    """Cryptographically verifiable receipt proving atomic worktree restoration upon failure."""
    model_config = ConfigDict(extra="forbid")

    task_id: str
    worktree_path: str
    branch_name: str
    restored_base_commit: str
    untracked_files_purged: list[str] = Field(default_factory=list)
    restoration_status: str = Field(default="PRISTINE_ROLLBACK", description="'PRISTINE_ROLLBACK' or 'BRANCH_TEARDOWN'")
    canonical_clean: bool = Field(default=True, description="True if no host repository pollution occurred")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class CodingPipelineResult(BaseModel):
    """Comprehensive result emitted upon completion or termination of the coding pipeline."""
    model_config = ConfigDict(extra="forbid")

    task_id: str
    status: VerificationStatus
    current_stage: PipelineStage
    stage_history: list[dict[str, Any]] = Field(default_factory=list)
    worktree_config: Optional[WorktreeSessionConfig] = None
    committee_debate: Optional[CommitteeDebateRecord] = Field(default=None, description="Multi-agent deliberation and consensus output")
    mutation_plan: Optional[ScopedMutationPlan] = None
    receipts: list[VerificationReceipt] = Field(default_factory=list)
    self_healing_attempts: list[SelfHealingAttemptReceipt] = Field(default_factory=list, description="Historical self-healing repair attempts")
    rollback_receipt: Optional[RollbackReceipt] = Field(default=None, description="Receipt proving clean rollback if execution failed")
    pr_payload: Optional[DraftPRPayload] = None
    error_message: Optional[str] = None
    audit_events: list[dict[str, Any]] = Field(default_factory=list)
