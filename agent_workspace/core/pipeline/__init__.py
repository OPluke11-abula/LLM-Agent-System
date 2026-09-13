"""LAS Autonomous Coding Pipeline Core Module.

Coordinates the product workflow:
Requirement Intake -> Bounded Mutation -> Verification Evidence -> Draft PR.
"""

from __future__ import annotations

from .models import (
    PipelineStage,
    VerificationStatus,
    CodingTaskRequest,
    WorktreeSessionConfig,
    ScopedMutationPlan,
    VerificationReceipt,
    DraftPRPayload,
    CodingPipelineResult,
)
from .contracts import (
    IWorktreeManager,
    IScopedExecutor,
    IVerificationRunner,
    IDraftPRPublisher,
)
from .manager import CodingPipelineManager

__all__ = [
    "PipelineStage",
    "VerificationStatus",
    "CodingTaskRequest",
    "WorktreeSessionConfig",
    "ScopedMutationPlan",
    "VerificationReceipt",
    "DraftPRPayload",
    "CodingPipelineResult",
    "IWorktreeManager",
    "IScopedExecutor",
    "IVerificationRunner",
    "IDraftPRPublisher",
    "CodingPipelineManager",
]
