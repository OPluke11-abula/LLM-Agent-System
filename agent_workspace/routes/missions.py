"""Protected REST routes for Mission control-plane state operations."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from fastapi.responses import JSONResponse

from agent_workspace.core.mission_api_contracts import (
    ApprovalRecordRequest,
    EvidenceRecordRequest,
    MissionActor,
    MissionCreateRequest,
    MissionTransitionAPIRequest,
    MissionTransitionResponse,
    PlanAttachRequest,
    VerificationRecordRequest,
)
from agent_workspace.core.mission_contracts import ApprovalGate, EvidenceRecord
from agent_workspace.core.mission_model import Mission, TransitionRequest
from agent_workspace.core.mission_state_machine import MissionTransitionError
from agent_workspace.core.mission_store import (
    MAX_MISSION_PAGE_SIZE,
    MissionPage,
    MissionStore,
    MissionStoreConflictError,
    MissionStoreError,
)
from agent_workspace.routes.dependencies import (
    _api_key_principal,
    get_workspace,
    verify_jwt,
)


router = APIRouter(prefix="/v1/missions", tags=["missions"])


def get_mission_store() -> MissionStore:
    return MissionStore(Path(get_workspace()) / "memory" / "missions.db")


def require_mission_actor(
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None),
) -> MissionActor:
    principal = None
    if x_api_key:
        principal = _api_key_principal(x_api_key)
    elif authorization and authorization.startswith("Bearer "):
        try:
            principal = verify_jwt(authorization[7:])
        except RuntimeError:
            principal = None
    if principal is None:
        raise HTTPException(status_code=401, detail="Mission authentication required")
    actor_value = principal.get("sub", principal.get("tenant_id"))
    if not isinstance(actor_value, str) or not actor_value:
        raise HTTPException(status_code=401, detail="Authenticated actor is invalid")
    return MissionActor(actor_id=actor_value)


def _store_error(error: MissionStoreError) -> JSONResponse:
    response_status = status.HTTP_404_NOT_FOUND if error.code == "mission_not_found" else status.HTTP_409_CONFLICT
    return JSONResponse(status_code=response_status, content={"code": error.code, "message": error.detail})


def _transition_error(error: MissionTransitionError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={"code": error.code.value, "message": error.detail},
    )


@router.post("", response_model=Mission, status_code=status.HTTP_201_CREATED)
def create_mission(
    payload: MissionCreateRequest,
    actor: MissionActor = Depends(require_mission_actor),
    store: MissionStore = Depends(get_mission_store),
) -> Mission | JSONResponse:
    mission_id = payload.mission_id or f"mission-{uuid4().hex}"
    mission = Mission(
        mission_id=mission_id,
        requirement=payload.requirement,
        repository_id=payload.repository_id,
        execution_policy=payload.execution_policy,
        budget_policy=payload.budget_policy,
        actor_id=actor.actor_id,
    )
    try:
        return store.create(mission)
    except MissionStoreConflictError as error:
        return _store_error(error)


@router.get("", response_model=MissionPage)
def list_missions(
    limit: int = Query(default=50, ge=1, le=MAX_MISSION_PAGE_SIZE),
    offset: int = Query(default=0, ge=0),
    _: MissionActor = Depends(require_mission_actor),
    store: MissionStore = Depends(get_mission_store),
) -> MissionPage | JSONResponse:
    try:
        return store.list(limit=limit, offset=offset)
    except MissionStoreError as error:
        return _store_error(error)


@router.get("/{mission_id}", response_model=Mission)
def get_mission(
    mission_id: str,
    _: MissionActor = Depends(require_mission_actor),
    store: MissionStore = Depends(get_mission_store),
) -> Mission | JSONResponse:
    mission = store.get(mission_id)
    if mission is None:
        return JSONResponse(status_code=404, content={"code": "mission_not_found", "message": "Mission does not exist"})
    return mission


@router.post("/{mission_id}/transitions", response_model=MissionTransitionResponse)
def submit_transition(
    mission_id: str,
    payload: MissionTransitionAPIRequest,
    actor: MissionActor = Depends(require_mission_actor),
    store: MissionStore = Depends(get_mission_store),
) -> MissionTransitionResponse | JSONResponse:
    try:
        result = store.append_transition(
            mission_id,
            TransitionRequest(
                event=payload.event,
                actor_id=actor.actor_id,
                idempotency_key=payload.idempotency_key,
                approval_subject=payload.approval_subject,
            ),
            expected_revision=payload.expected_revision,
        )
        return MissionTransitionResponse(
            mission=result.mission,
            audit=result.audit,
            replayed=result.replayed,
        )
    except MissionStoreError as error:
        return _store_error(error)
    except MissionTransitionError as error:
        return _transition_error(error)


@router.get("/{mission_id}/transitions")
def get_transition_history(
    mission_id: str,
    _: MissionActor = Depends(require_mission_actor),
    store: MissionStore = Depends(get_mission_store),
) -> JSONResponse:
    mission = store.get(mission_id)
    if mission is None:
        return JSONResponse(status_code=404, content={"code": "mission_not_found", "message": "Mission does not exist"})
    return JSONResponse(content=[audit.model_dump(mode="json") for audit in mission.transition_audit])


@router.put("/{mission_id}/plan", response_model=Mission)
def attach_plan(
    mission_id: str,
    payload: PlanAttachRequest,
    _: MissionActor = Depends(require_mission_actor),
    store: MissionStore = Depends(get_mission_store),
) -> Mission | JSONResponse:
    mission = store.get(mission_id)
    if mission is None:
        return JSONResponse(status_code=404, content={"code": "mission_not_found", "message": "Mission does not exist"})
    if payload.execution_plan.mission_id != mission_id:
        return JSONResponse(status_code=422, content={"code": "plan_mission_mismatch", "message": "Plan Mission ID does not match"})
    updated = mission.model_copy(
        update={
            "execution_plan": payload.execution_plan,
            "plan_reference": payload.execution_plan.plan_id,
            "plan_revision": payload.execution_plan.revision,
            "required_verification": payload.execution_plan.required_verification,
        }
    )
    try:
        return store.save(updated, expected_revision=payload.expected_revision)
    except MissionStoreError as error:
        return _store_error(error)


@router.post("/{mission_id}/approvals", response_model=Mission)
def record_approval(
    mission_id: str,
    payload: ApprovalRecordRequest,
    actor: MissionActor = Depends(require_mission_actor),
    store: MissionStore = Depends(get_mission_store),
) -> Mission | JSONResponse:
    mission = store.get(mission_id)
    if mission is None:
        return JSONResponse(status_code=404, content={"code": "mission_not_found", "message": "Mission does not exist"})
    gate = ApprovalGate(
        gate_id=payload.gate_id,
        gate_type=payload.gate_type,
        subject=payload.subject,
        status=payload.status,
        actor_id=actor.actor_id,
        decided_at=datetime.now(timezone.utc),
        evidence_refs=payload.evidence_refs,
        idempotency_key=f"api-approval-{payload.gate_id}",
    )
    updated = mission.model_copy(update={"approval_gates": mission.approval_gates + (gate,)})
    try:
        return store.save(updated, expected_revision=payload.expected_revision)
    except MissionStoreError as error:
        return _store_error(error)


@router.post("/{mission_id}/evidence", response_model=Mission)
def record_evidence(
    mission_id: str,
    payload: EvidenceRecordRequest,
    actor: MissionActor = Depends(require_mission_actor),
    store: MissionStore = Depends(get_mission_store),
) -> Mission | JSONResponse:
    mission = store.get(mission_id)
    if mission is None:
        return JSONResponse(status_code=404, content={"code": "mission_not_found", "message": "Mission does not exist"})
    evidence: EvidenceRecord = payload.evidence.model_copy(update={"producing_agent": actor.actor_id})
    updated = mission.model_copy(update={"evidence_records": mission.evidence_records + (evidence,)})
    try:
        return store.save(updated, expected_revision=payload.expected_revision)
    except MissionStoreError as error:
        return _store_error(error)


@router.put("/{mission_id}/verification-gates", response_model=Mission)
def record_verification(
    mission_id: str,
    payload: VerificationRecordRequest,
    _: MissionActor = Depends(require_mission_actor),
    store: MissionStore = Depends(get_mission_store),
) -> Mission | JSONResponse:
    mission = store.get(mission_id)
    if mission is None:
        return JSONResponse(status_code=404, content={"code": "mission_not_found", "message": "Mission does not exist"})
    gates = tuple(gate for gate in mission.verification_gates if gate.gate != payload.gate.gate)
    updated = mission.model_copy(update={"verification_gates": gates + (payload.gate,)})
    try:
        return store.save(updated, expected_revision=payload.expected_revision)
    except MissionStoreError as error:
        return _store_error(error)
