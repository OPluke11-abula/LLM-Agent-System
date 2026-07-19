"""Protected REST routes for Mission control-plane state operations."""

from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from agent_workspace.core.mission_api_contracts import (
    ApprovalRecordRequest,
    EvidenceRecordRequest,
    MissionActor,
    MissionCreateRequest,
    MissionTransitionAPIRequest,
    MissionTransitionResponse,
    MissionCapabilitiesResponse,
    MissionErrorResponse,
    PlanAttachRequest,
    VerificationRecordRequest,
)
from agent_workspace.core.mission_contracts import ApprovalGate, EvidenceRecord
from agent_workspace.core.mission_model import Mission, MissionAggregateError, TransitionRequest
from agent_workspace.core.mission_state_machine import MissionStateMachine, MissionTransitionError
from agent_workspace.core.mission_store import (
    MAX_MISSION_PAGE_SIZE,
    MissionPage,
    MissionStore,
    MissionStoreConflictError,
    MissionStoreCorruptionError,
    MissionStoreError,
    MissionTransitionPage,
    MissionStoreValidationError,
)
from agent_workspace.routes.dependencies import (
    _api_key_principal,
    get_workspace,
    verify_jwt,
)


router = APIRouter(
    prefix="/v1/missions",
    tags=["missions"],
    responses={
        401: {"model": MissionErrorResponse},
        404: {"model": MissionErrorResponse},
        409: {"model": MissionErrorResponse},
        422: {"model": MissionErrorResponse},
        500: {"model": MissionErrorResponse},
        503: {"model": MissionErrorResponse},
    },
)


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
    if error.code == "mission_not_found":
        response_status = status.HTTP_404_NOT_FOUND
    elif isinstance(error, MissionStoreValidationError):
        response_status = status.HTTP_422_UNPROCESSABLE_CONTENT
    elif isinstance(error, MissionStoreCorruptionError):
        response_status = status.HTTP_500_INTERNAL_SERVER_ERROR
    elif error.code == "store_unavailable":
        response_status = status.HTTP_503_SERVICE_UNAVAILABLE
    else:
        response_status = status.HTTP_409_CONFLICT
    return JSONResponse(status_code=response_status, content={"code": error.code, "message": error.detail})


def _transition_error(error: MissionTransitionError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={"code": error.code.value, "message": error.detail},
    )


def _aggregate_error(error: MissionAggregateError | ValidationError) -> JSONResponse:
    code = error.code if isinstance(error, MissionAggregateError) else "invalid_aggregate_contract"
    response_status = (
        status.HTTP_409_CONFLICT
        if code in {"immutable_decision_conflict", "immutable_plan_conflict", "idempotency_conflict"}
        else status.HTTP_422_UNPROCESSABLE_CONTENT
    )
    return JSONResponse(
        status_code=response_status,
        content={"code": code, "message": "Mission aggregate validation failed"},
    )


def _owned_mission(store: MissionStore, mission_id: str, actor: MissionActor) -> Mission | JSONResponse:
    try:
        mission = store.get(mission_id, owner_id=actor.actor_id)
    except MissionStoreError as error:
        return _store_error(error)
    if mission is None:
        return JSONResponse(status_code=404, content={"code": "mission_not_found", "message": "Mission does not exist"})
    return mission


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
        owner_actor_id=actor.actor_id,
    )
    try:
        return store.create(mission)
    except MissionStoreError as error:
        return _store_error(error)


@router.get("", response_model=MissionPage)
def list_missions(
    limit: int = Query(default=50, ge=1, le=MAX_MISSION_PAGE_SIZE),
    offset: int = Query(default=0, ge=0),
    actor: MissionActor = Depends(require_mission_actor),
    store: MissionStore = Depends(get_mission_store),
) -> MissionPage | JSONResponse:
    try:
        return store.list(limit=limit, offset=offset, owner_id=actor.actor_id)
    except MissionStoreError as error:
        return _store_error(error)


@router.get("/{mission_id}", response_model=Mission)
def get_mission(
    mission_id: str,
    actor: MissionActor = Depends(require_mission_actor),
    store: MissionStore = Depends(get_mission_store),
) -> Mission | JSONResponse:
    return _owned_mission(store, mission_id, actor)


@router.get("/{mission_id}/capabilities", response_model=MissionCapabilitiesResponse)
def get_mission_capabilities(
    mission_id: str,
    actor: MissionActor = Depends(require_mission_actor),
    store: MissionStore = Depends(get_mission_store),
) -> MissionCapabilitiesResponse | JSONResponse:
    mission_result = _owned_mission(store, mission_id, actor)
    if isinstance(mission_result, JSONResponse):
        return mission_result
    return MissionStateMachine().capabilities(mission_result)


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
            owner_id=actor.actor_id,
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


@router.get("/{mission_id}/transitions", response_model=MissionTransitionPage)
def get_transition_history(
    mission_id: str,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    actor: MissionActor = Depends(require_mission_actor),
    store: MissionStore = Depends(get_mission_store),
) -> MissionTransitionPage | JSONResponse:
    try:
        return store.transition_history(
            mission_id,
            limit=limit,
            offset=offset,
            owner_id=actor.actor_id,
        )
    except MissionStoreError as error:
        return _store_error(error)


@router.put("/{mission_id}/plan", response_model=Mission)
def attach_plan(
    mission_id: str,
    payload: PlanAttachRequest,
    actor: MissionActor = Depends(require_mission_actor),
    store: MissionStore = Depends(get_mission_store),
) -> Mission | JSONResponse:
    mission_result = _owned_mission(store, mission_id, actor)
    if isinstance(mission_result, JSONResponse):
        return mission_result
    mission = mission_result
    try:
        updated = mission.attach_plan(payload.execution_plan)
        if updated == mission:
            if payload.expected_revision != mission.revision:
                raise MissionStoreConflictError("stale_revision", "Mission revision does not match expected revision")
            return mission
        return store.save(updated, expected_revision=payload.expected_revision, owner_id=actor.actor_id)
    except (MissionAggregateError, ValidationError) as error:
        return _aggregate_error(error)
    except MissionStoreError as error:
        return _store_error(error)


@router.post("/{mission_id}/approvals", response_model=Mission)
def record_approval(
    mission_id: str,
    payload: ApprovalRecordRequest,
    actor: MissionActor = Depends(require_mission_actor),
    store: MissionStore = Depends(get_mission_store),
) -> Mission | JSONResponse:
    mission_result = _owned_mission(store, mission_id, actor)
    if isinstance(mission_result, JSONResponse):
        return mission_result
    mission = mission_result
    gate = ApprovalGate(
        gate_id=payload.gate_id,
        gate_type=payload.gate_type,
        subject=payload.subject,
        status=payload.status,
        actor_id=actor.actor_id,
        decided_at=store.now(),
        evidence_refs=payload.evidence_refs,
        idempotency_key=payload.idempotency_key,
    )
    try:
        updated = mission.add_approval_gate(gate)
        if updated == mission:
            if payload.expected_revision != mission.revision:
                raise MissionStoreConflictError("stale_revision", "Mission revision does not match expected revision")
            return mission
        return store.save(updated, expected_revision=payload.expected_revision, owner_id=actor.actor_id)
    except (MissionAggregateError, ValidationError) as error:
        return _aggregate_error(error)
    except MissionStoreError as error:
        return _store_error(error)


@router.post("/{mission_id}/evidence", response_model=Mission)
def record_evidence(
    mission_id: str,
    payload: EvidenceRecordRequest,
    actor: MissionActor = Depends(require_mission_actor),
    store: MissionStore = Depends(get_mission_store),
) -> Mission | JSONResponse:
    mission_result = _owned_mission(store, mission_id, actor)
    if isinstance(mission_result, JSONResponse):
        return mission_result
    mission = mission_result
    evidence: EvidenceRecord = payload.evidence.with_producing_agent(actor.actor_id)
    try:
        updated = mission.add_evidence_record(evidence)
        return store.save(updated, expected_revision=payload.expected_revision, owner_id=actor.actor_id)
    except (MissionAggregateError, ValidationError) as error:
        return _aggregate_error(error)
    except MissionStoreError as error:
        return _store_error(error)


@router.post("/{mission_id}/test-fixture/evidence", response_model=Mission)
def record_test_fixture_evidence(
    mission_id: str,
    payload: EvidenceRecordRequest,
    actor: MissionActor = Depends(require_mission_actor),
    store: MissionStore = Depends(get_mission_store),
) -> Mission | JSONResponse:
    if os.environ.get("LAS_ENABLE_MISSION_TEST_FIXTURE") != "true":
        return JSONResponse(status_code=404, content={"code": "mission_not_found", "message": "Mission does not exist"})
    if payload.evidence.source != "test_fixture":
        return JSONResponse(status_code=422, content={"code": "invalid_contract", "message": "Test fixture evidence must use test_fixture provenance"})
    return record_evidence(mission_id, payload, actor, store)


@router.put("/{mission_id}/verification-gates", response_model=Mission)
def record_verification(
    mission_id: str,
    payload: VerificationRecordRequest,
    actor: MissionActor = Depends(require_mission_actor),
    store: MissionStore = Depends(get_mission_store),
) -> Mission | JSONResponse:
    mission_result = _owned_mission(store, mission_id, actor)
    if isinstance(mission_result, JSONResponse):
        return mission_result
    mission = mission_result
    try:
        updated = mission.record_verification_gate(payload.gate)
        return store.save(updated, expected_revision=payload.expected_revision, owner_id=actor.actor_id)
    except (MissionAggregateError, ValidationError) as error:
        return _aggregate_error(error)
    except MissionStoreError as error:
        return _store_error(error)
