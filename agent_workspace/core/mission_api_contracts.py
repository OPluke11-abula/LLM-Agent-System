"""Stable Pydantic request and response contracts for the Mission API."""

from __future__ import annotations

from pydantic import Field, model_validator

from agent_workspace.core.mission_contracts import (
    ApprovalSubject,
    ApprovalType,
    EvidenceRecord,
    ExecutionPlan,
    MissionBudgetPolicy,
    VerificationGate,
)
from agent_workspace.core.mission_model import (
    Mission,
    MissionTransitionAudit,
    MissionEvent,
)
from agent_workspace.core.product_contracts import (
    ActorId,
    ApprovalStatus,
    ContractModel,
    EvidenceId,
    GateId,
    IdempotencyKey,
    MissionId,
    MissionPolicy,
    RepositoryId,
)


class MissionActor(ContractModel):
    actor_id: ActorId


class MissionCreateRequest(ContractModel):
    mission_id: MissionId | None = None
    requirement: str = Field(min_length=1, max_length=4000)
    repository_id: RepositoryId
    execution_policy: MissionPolicy = Field(default_factory=MissionPolicy)
    budget_policy: MissionBudgetPolicy = Field(default_factory=MissionBudgetPolicy)
    actor_id: ActorId | None = None


class MissionTransitionAPIRequest(ContractModel):
    event: MissionEvent
    idempotency_key: IdempotencyKey
    expected_revision: int = Field(ge=0)
    approval_subject: ApprovalSubject | None = None


class PlanAttachRequest(ContractModel):
    execution_plan: ExecutionPlan
    expected_revision: int = Field(ge=0)


class ApprovalRecordRequest(ContractModel):
    gate_id: GateId
    gate_type: ApprovalType
    subject: ApprovalSubject
    status: ApprovalStatus
    evidence_refs: tuple[EvidenceId, ...] = ()
    expected_revision: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_decision_subject(self) -> ApprovalRecordRequest:
        if self.subject.kind != self.gate_type.value:
            raise ValueError("approval subject must match gate type")
        if self.status is ApprovalStatus.PENDING:
            raise ValueError("approval recording requires an approved or rejected status")
        return self


class EvidenceRecordRequest(ContractModel):
    evidence: EvidenceRecord
    expected_revision: int = Field(ge=0)


class VerificationRecordRequest(ContractModel):
    gate: VerificationGate
    expected_revision: int = Field(ge=0)


class MissionTransitionResponse(ContractModel):
    mission: Mission
    audit: MissionTransitionAudit
    replayed: bool


class MissionErrorResponse(ContractModel):
    code: str
    message: str
