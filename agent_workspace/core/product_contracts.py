"""Canonical Developer Agent Control Plane contracts for P1."""

from __future__ import annotations

from enum import StrEnum, unique
from pathlib import PurePosixPath
from typing import Final, Literal, NewType
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator


SCHEMA_VERSION: Final[str] = "1.0"
MissionId = NewType("MissionId", str)
RepositoryId = NewType("RepositoryId", str)
PlanId = NewType("PlanId", str)
ActorId = NewType("ActorId", str)
IdempotencyKey = NewType("IdempotencyKey", str)


class ContractModel(BaseModel):
    """Immutable, strict Pydantic boundary model shared by product contracts."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
    )


@unique
class ExecutionPolicyPreset(StrEnum):
    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    EXPLORATORY = "exploratory"


@unique
class ApprovalType(StrEnum):
    PLAN = "plan"
    SCOPE_EXPANSION = "scope_expansion"
    DRAFT_PR = "draft_pr"


@unique
class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


@unique
class EvidenceType(StrEnum):
    COMMAND = "command"
    TEST = "test"
    CI = "ci"
    REVIEW = "review"
    SCOPE = "scope"
    ARCHITECTURE = "architecture"
    SECURITY = "security"
    QUALITY = "quality"
    COST = "cost"
    ARTIFACT = "artifact"
    PROVIDER_CALL = "provider_call"


@unique
class VerificationGateName(StrEnum):
    REQUIREMENT = "requirement"
    SCOPE = "scope"
    ARCHITECTURE = "architecture"
    TESTS = "tests"
    SECURITY = "security"
    QUALITY = "quality"
    CI = "ci"
    COST = "cost"


@unique
class GateStatus(StrEnum):
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    BLOCKED = "blocked"
    NOT_APPLICABLE = "not_applicable"


@unique
class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@unique
class CIStatus(StrEnum):
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    NOT_CONFIGURED = "not_configured"


@unique
class Mergeability(StrEnum):
    MERGEABLE = "mergeable"
    CONFLICTS = "conflicts"
    UNKNOWN = "unknown"


@unique
class HumanDecisionState(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REVISION_REQUESTED = "revision_requested"
    REJECTED = "rejected"


def _validate_relative_paths(paths: tuple[str, ...]) -> tuple[str, ...]:
    for path in paths:
        normalized = path.replace("\\", "/")
        if (
            not normalized
            or normalized.startswith("/")
            or (len(normalized) > 1 and normalized[1] == ":")
            or ".." in PurePosixPath(normalized).parts
        ):
            raise ValueError("paths must be non-empty repository-relative paths")
    return paths


class RepositorySizeIndicators(ContractModel):
    file_count: int = Field(default=0, ge=0)
    line_count: int = Field(default=0, ge=0)
    byte_count: int = Field(default=0, ge=0)


class RepositoryProfile(ContractModel):
    repository_id: RepositoryId
    repository_name: str = Field(min_length=1)
    local_path: str | None = Field(default=None, exclude=True)
    remote_url: str | None = None
    base_branch: str = Field(default="main", min_length=1)
    detected_languages: tuple[str, ...] = ()
    detected_frameworks: tuple[str, ...] = ()
    package_managers: tuple[str, ...] = ()
    test_commands: tuple[str, ...] = ()
    build_commands: tuple[str, ...] = ()
    ci_workflows: tuple[str, ...] = ()
    repository_size: RepositorySizeIndicators = Field(default_factory=RepositorySizeIndicators)
    dirty_worktree: bool = False
    protected_paths: tuple[str, ...] = ()
    architecture_documents: tuple[str, ...] = ()

    @field_validator("remote_url")
    @classmethod
    def reject_credentials_in_remote_url(cls, value: str | None) -> str | None:
        if value is not None and (urlsplit(value).username or urlsplit(value).password):
            raise ValueError("remote URLs must not contain credentials")
        return value

    @field_validator("protected_paths", "architecture_documents")
    @classmethod
    def validate_repository_paths(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return _validate_relative_paths(value)


class ScopePolicy(ContractModel):
    allowed_paths: tuple[str, ...] = ()
    protected_paths: tuple[str, ...] = ()
    dependency_change_permission: bool = False
    schema_change_permission: bool = False
    ci_change_permission: bool = False
    commit_permission: bool = False
    push_permission: bool = False
    draft_pr_permission: bool = False
    auto_merge_allowed: Literal[False] = False

    @field_validator("allowed_paths", "protected_paths")
    @classmethod
    def validate_scope_paths(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return _validate_relative_paths(value)


class MissionPolicy(ContractModel):
    preset: ExecutionPolicyPreset = ExecutionPolicyPreset.BALANCED
    scope: ScopePolicy = Field(default_factory=ScopePolicy)
    allow_database_changes: bool = False
    allow_ci_changes: bool = False
    max_provider_calls: int = Field(default=64, ge=1)
    max_cost: float | None = Field(default=None, ge=0)
