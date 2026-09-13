"""FastAPI Route Adapter for LAS Autonomous Coding Pipeline (Phase 82-01).

Implements REST and WebSocket interfaces for the 5-stage product loop:
1. POST /v1/pipeline/tasks -> Intake & Anti-Summary Preflight
2. POST /v1/pipeline/tasks/{task_id}/plan -> Stop-and-Wait Gate Plan Submission
3. POST /v1/pipeline/tasks/{task_id}/approve -> HITL Architecture Gate Approval
4. POST /v1/pipeline/tasks/{task_id}/execute -> Isolated Worktree Mutation & Test Ladder
5. POST /v1/pipeline/tasks/run -> End-to-end full execution (with pre-approved plan)
6. GET  /v1/pipeline/tasks -> List active and historical pipeline tasks
7. GET  /v1/pipeline/tasks/{task_id} -> Retrieve task state, stage history & receipts
8. GET  /v1/pipeline/tasks/{task_id}/events -> Retrieve cryptographic Merkle ledger
9. GET  /v1/pipeline/tasks/{task_id}/preservation -> Verify host canonical preservation
10. WS  /v1/pipeline/ws -> Real-time pipeline stage & verification event stream
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, ConfigDict, Field

from agent_workspace.core.agent_executor import AgentExecutor
from agent_workspace.core.git_worktree import GitWorktreeManager
from agent_workspace.core.pipeline.benchmark import (
    GoldenBenchmarkScorecard,
    GoldenFlowBenchmarkEngine,
)
from agent_workspace.core.pipeline.manager import CodingPipelineManager, PipelineError
from agent_workspace.core.pipeline.models import (
    CodingPipelineResult,
    CodingTaskRequest,
    PipelineStage,
    ScopedMutationPlan,
    VerificationStatus,
)
from agent_workspace.core.repository import (
    CanonicalPreservationReceipt,
    RepositoryInspector,
)
from agent_workspace.core.runtime_events import (
    GitHubDraftPRPublisher,
    LiveFeedbackRunner,
    RuntimeEventType,
    RuntimeEventsLedger,
)
from agent_workspace.routes.dependencies import get_workspace

logger = logging.getLogger("api.pipeline")

router = APIRouter(prefix="/v1/pipeline", tags=["pipeline"])


# ---------------------------------------------------------------------------
# WebSocket Telemetry Broadcast Manager
# ---------------------------------------------------------------------------

class PipelineBroadcastManager:
    """Manages live WebSocket subscriptions for pipeline lifecycle telemetry."""

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []
        self._lock = threading.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        with self._lock:
            self.active_connections.append(websocket)
        logger.info("[PipelineWS] Client connected. Total subscribers: %d", len(self.active_connections))

    def disconnect(self, websocket: WebSocket) -> None:
        with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
        logger.info("[PipelineWS] Client disconnected. Total subscribers: %d", len(self.active_connections))

    async def broadcast(self, event: dict[str, Any]) -> None:
        dead: list[WebSocket] = []
        with self._lock:
            targets = list(self.active_connections)

        for ws in targets:
            try:
                await ws.send_json(event)
            except Exception:
                dead.append(ws)

        if dead:
            with self._lock:
                for ws in dead:
                    if ws in self.active_connections:
                        self.active_connections.remove(ws)


pipeline_broadcaster = PipelineBroadcastManager()


# ---------------------------------------------------------------------------
# Request & Response Schemas
# ---------------------------------------------------------------------------

class PlanApprovalRequest(BaseModel):
    """Payload for human-in-the-loop approval at the Stop-and-Wait Gate."""
    model_config = ConfigDict(extra="forbid")

    approval_token: str = Field(..., description="Cryptographic or human approval token")
    approver: str = Field(default="PO / Domain Owner", description="Identity of the approver")
    notes: Optional[str] = Field(default=None, description="Optional architecture review notes")


class FullPipelineRunRequest(BaseModel):
    """Payload for executing an autonomous coding task in a single call."""
    model_config = ConfigDict(extra="forbid")

    request: CodingTaskRequest
    plan: ScopedMutationPlan


# ---------------------------------------------------------------------------
# In-Memory Pipeline Registry
# ---------------------------------------------------------------------------

class TaskRecord:
    def __init__(
        self,
        request: CodingTaskRequest,
        result: CodingPipelineResult,
        preservation_receipt: CanonicalPreservationReceipt,
        ledger: RuntimeEventsLedger,
    ) -> None:
        self.request = request
        self.result = result
        self.preservation_receipt = preservation_receipt
        self.ledger = ledger
        self.plan: Optional[ScopedMutationPlan] = None


_task_registry: dict[str, TaskRecord] = {}
_registry_lock = threading.Lock()
_manager_instance: Optional[CodingPipelineManager] = None
_inspector_instance: Optional[RepositoryInspector] = None


def get_pipeline_manager() -> CodingPipelineManager:
    global _manager_instance
    if _manager_instance is None:
        ws = get_workspace()
        _manager_instance = CodingPipelineManager(
            workspace_path=ws,
            worktree_manager=GitWorktreeManager(),
            scoped_executor=AgentExecutor(),
            verification_runner=LiveFeedbackRunner(),
            draft_pr_publisher=GitHubDraftPRPublisher(),
        )
    return _manager_instance


def get_repository_inspector() -> RepositoryInspector:
    global _inspector_instance
    if _inspector_instance is None:
        _inspector_instance = RepositoryInspector()
    return _inspector_instance


# ---------------------------------------------------------------------------
# REST Endpoints
# ---------------------------------------------------------------------------

@router.post("/tasks")
async def create_pipeline_task(request: CodingTaskRequest) -> dict[str, Any]:
    """
    Stage 1 & 2: Intake & Precheck.
    Validates Anti-Summary Invariant and creates an initial CanonicalPreservationReceipt.
    """
    manager = get_pipeline_manager()
    inspector = get_repository_inspector()

    try:
        receipt = inspector.generate_preservation_receipt(request.repository_path)
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Target repository verification failed: {exc}",
        ) from exc

    result = manager.start_pipeline(request)

    ledger = RuntimeEventsLedger(workspace_path=get_workspace())
    ledger.record_event(
        task_id=request.task_id,
        event_type=RuntimeEventType.TASK_STARTED,
        payload={
            "requirement": request.requirement_prompt,
            "target_branch": request.target_branch,
            "inspected_files": request.inspected_files,
            "initial_head": receipt.initial_head,
        },
    )

    record = TaskRecord(
        request=request,
        result=result,
        preservation_receipt=receipt,
        ledger=ledger,
    )

    with _registry_lock:
        _task_registry[request.task_id] = record

    # Broadcast event
    asyncio.create_task(
        pipeline_broadcaster.broadcast(
            {
                "event": "pipeline_task_created",
                "task_id": request.task_id,
                "stage": result.current_stage.value,
                "status": result.status.value,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
    )

    if result.current_stage == PipelineStage.FAILED:
        raise HTTPException(
            status_code=400,
            detail=f"Precheck failed: {result.error_message}",
        )

    return {
        "status": "success",
        "task_id": request.task_id,
        "stage": result.current_stage.value,
        "result": result.model_dump(),
    }


@router.post("/tasks/{task_id}/plan")
async def submit_mutation_plan(task_id: str, plan: ScopedMutationPlan) -> dict[str, Any]:
    """
    Submits a ScopedMutationPlan for Stop-and-Wait Architecture Gate review.
    """
    with _registry_lock:
        record = _task_registry.get(task_id)

    if not record:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found.")

    manager = get_pipeline_manager()
    is_valid, err_msg = manager.validate_role_scope(plan.assigned_role, plan.target_files)
    if not is_valid:
        raise HTTPException(status_code=403, detail=f"Role scope violation: {err_msg}")

    record.plan = plan
    gate_status = "APPROVED" if plan.human_approved else "AWAITING_APPROVAL"

    record.ledger.record_event(
        task_id=task_id,
        event_type=RuntimeEventType.STAGE_TRANSITION,
        payload={
            "stage": PipelineStage.PLAN_AND_GATE.value,
            "plan_summary": plan.plan_summary,
            "target_files": plan.target_files,
            "human_approved": plan.human_approved,
        },
    )

    asyncio.create_task(
        pipeline_broadcaster.broadcast(
            {
                "event": "pipeline_plan_submitted",
                "task_id": task_id,
                "gate_status": gate_status,
                "target_files": plan.target_files,
            }
        )
    )

    return {
        "status": "success",
        "task_id": task_id,
        "gate_status": gate_status,
        "plan": plan.model_dump(),
    }


@router.post("/tasks/{task_id}/approve")
async def approve_mutation_plan(task_id: str, approval: PlanApprovalRequest) -> dict[str, Any]:
    """
    Human-in-the-loop (HITL) approval endpoint to unlock the Stop-and-Wait Architecture Gate.
    """
    with _registry_lock:
        record = _task_registry.get(task_id)

    if not record:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found.")

    if not record.plan:
        raise HTTPException(status_code=400, detail=f"No plan has been submitted for task '{task_id}'.")

    record.plan.human_approved = True
    record.plan.approval_token = approval.approval_token
    record.plan.approval_timestamp = datetime.now(timezone.utc).isoformat()

    record.ledger.record_event(
        task_id=task_id,
        event_type=RuntimeEventType.STAGE_TRANSITION,
        payload={
            "action": "GATE_APPROVED",
            "approver": approval.approver,
            "token": approval.approval_token,
            "notes": approval.notes,
        },
    )

    asyncio.create_task(
        pipeline_broadcaster.broadcast(
            {
                "event": "pipeline_gate_approved",
                "task_id": task_id,
                "approver": approval.approver,
                "token": approval.approval_token,
            }
        )
    )

    return {
        "status": "success",
        "task_id": task_id,
        "gate_status": "APPROVED",
        "approval_token": approval.approval_token,
    }


@router.post("/tasks/{task_id}/execute")
async def execute_pipeline_task(task_id: str) -> dict[str, Any]:
    """
    Executes Stages 3-5: Isolated Worktree setup, Bounded Mutation, Verification Ladder, and Draft PR export.
    Enforces that the Stop-and-Wait Architecture Gate has been confirmed.
    """
    with _registry_lock:
        record = _task_registry.get(task_id)

    if not record:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found.")

    if not record.plan:
        raise HTTPException(status_code=400, detail="Plan must be submitted before execution.")

    if not record.plan.human_approved:
        raise HTTPException(
            status_code=403,
            detail="STOP_AND_WAIT_GATE_LOCKED: Plan has not been approved by human domain owner.",
        )

    manager = get_pipeline_manager()
    record.ledger.record_event(
        task_id=task_id,
        event_type=RuntimeEventType.STAGE_TRANSITION,
        payload={"stage": PipelineStage.ISOLATED_MUTATION.value},
    )

    result = manager.execute_pipeline(task_id, record.request, record.plan)
    record.result = result

    # Record completion in ledger
    record.ledger.record_event(
        task_id=task_id,
        event_type=RuntimeEventType.TASK_COMPLETED if result.status == VerificationStatus.PASS else RuntimeEventType.RECOVERY_TRIGGERED,
        payload={
            "status": result.status.value,
            "final_stage": result.current_stage.value,
            "receipts_count": len(result.receipts),
            "pr_url": result.pr_payload.pr_url if result.pr_payload else None,
        },
    )

    asyncio.create_task(
        pipeline_broadcaster.broadcast(
            {
                "event": "pipeline_completed",
                "task_id": task_id,
                "status": result.status.value,
                "stage": result.current_stage.value,
                "pr_url": result.pr_payload.pr_url if result.pr_payload else None,
            }
        )
    )

    return {
        "status": "success",
        "task_id": task_id,
        "result": result.model_dump(),
    }


@router.post("/tasks/run")
async def run_full_pipeline(payload: FullPipelineRunRequest) -> dict[str, Any]:
    """
    Convenience endpoint to execute an autonomous coding task with a pre-approved plan in a single request.
    """
    req = payload.request
    plan = payload.plan

    if not plan.human_approved:
        raise HTTPException(
            status_code=403,
            detail="STOP_AND_WAIT_GATE_LOCKED: Provided plan must have human_approved=True.",
        )

    manager = get_pipeline_manager()
    inspector = get_repository_inspector()

    try:
        preservation_receipt = inspector.generate_preservation_receipt(req.repository_path)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Repository precheck failed: {exc}") from exc

    ledger = RuntimeEventsLedger(workspace_path=get_workspace())
    ledger.record_event(
        task_id=req.task_id,
        event_type=RuntimeEventType.TASK_STARTED,
        payload={"requirement": req.requirement_prompt, "target_branch": req.target_branch},
    )

    result = manager.execute_pipeline(req.task_id, req, plan)

    record = TaskRecord(
        request=req,
        result=result,
        preservation_receipt=preservation_receipt,
        ledger=ledger,
    )
    record.plan = plan

    with _registry_lock:
        _task_registry[req.task_id] = record

    verified = inspector.verify_preservation(preservation_receipt)

    return {
        "status": "success",
        "task_id": req.task_id,
        "is_preserved": verified.is_preserved,
        "result": result.model_dump(),
    }


@router.get("/tasks")
async def list_pipeline_tasks() -> dict[str, Any]:
    """Lists all active and historical autonomous pipeline tasks."""
    with _registry_lock:
        tasks = [
            {
                "task_id": tid,
                "requirement": rec.request.requirement_prompt,
                "stage": rec.result.current_stage.value,
                "status": rec.result.status.value,
                "target_branch": rec.request.target_branch,
                "pr_url": rec.result.pr_payload.pr_url if rec.result.pr_payload else None,
                "has_plan": rec.plan is not None,
                "plan_approved": rec.plan.human_approved if rec.plan else False,
            }
            for tid, rec in _task_registry.items()
        ]

    return {"status": "success", "total": len(tasks), "tasks": tasks}


@router.get("/tasks/{task_id}")
async def get_pipeline_task(task_id: str) -> dict[str, Any]:
    """Retrieves full details, stage history, and receipts for a task."""
    with _registry_lock:
        record = _task_registry.get(task_id)

    if not record:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found.")

    return {
        "status": "success",
        "task_id": task_id,
        "request": record.request.model_dump(),
        "plan": record.plan.model_dump() if record.plan else None,
        "result": record.result.model_dump(),
        "preservation_receipt": record.preservation_receipt.model_dump(),
    }


@router.get("/tasks/{task_id}/events")
async def get_pipeline_events(task_id: str) -> dict[str, Any]:
    """Retrieves cryptographically chained events and Merkle root for a task."""
    with _registry_lock:
        record = _task_registry.get(task_id)

    if not record:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found.")

    events = record.ledger.get_events_for_task(task_id)
    merkle_root = record.ledger.calculate_merkle_root(task_id)
    is_valid = record.ledger.verify_chain_integrity(task_id)

    return {
        "status": "success",
        "task_id": task_id,
        "merkle_root": merkle_root,
        "chain_integrity": is_valid,
        "event_count": len(events),
        "events": [
            {
                "event_id": ev.event_id,
                "event_type": ev.event_type.value,
                "current_hash": ev.current_hash,
                "previous_hash": ev.previous_hash,
                "payload": ev.payload,
                "timestamp": ev.timestamp,
            }
            for ev in events
        ],
    }


@router.get("/tasks/{task_id}/preservation")
async def get_pipeline_preservation(task_id: str) -> dict[str, Any]:
    """Verifies that the canonical host repository was 100% preserved."""
    with _registry_lock:
        record = _task_registry.get(task_id)

    if not record:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found.")

    inspector = get_repository_inspector()
    verified = inspector.verify_preservation(record.preservation_receipt)

    return {
        "status": "success",
        "task_id": task_id,
        "is_preserved": verified.is_preserved,
        "initial_head": verified.initial_head,
        "initial_status_hash": verified.initial_status_hash,
        "final_status_hash": verified.final_status_hash,
        "details": verified.details,
    }


# ---------------------------------------------------------------------------
# WebSocket Telemetry Stream
# ---------------------------------------------------------------------------

@router.websocket("/ws")
async def pipeline_websocket_stream(websocket: WebSocket) -> None:
    """Live streaming endpoint for pipeline stage transitions and receipts."""
    await pipeline_broadcaster.connect(websocket)
    try:
        while True:
            # Keep socket alive and allow client pings
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        pipeline_broadcaster.disconnect(websocket)
    except Exception as exc:
        logger.warning("[PipelineWS] WebSocket error: %s", exc)
        pipeline_broadcaster.disconnect(websocket)


# ---------------------------------------------------------------------------
# Phase 83 (P4): Golden Flow Benchmark Endpoints
# ---------------------------------------------------------------------------

_latest_benchmark_scorecard: Optional[GoldenBenchmarkScorecard] = None


@router.post("/benchmark/run")
async def run_pipeline_benchmark(repo_path: Optional[str] = None) -> dict[str, Any]:
    """Runs the Golden Flow Benchmark Suite across all 3 scenarios and computes ADR-006 KPIs."""
    global _latest_benchmark_scorecard
    engine = GoldenFlowBenchmarkEngine()
    scorecard = await asyncio.to_thread(engine.run_benchmark_suite, repo_path)
    _latest_benchmark_scorecard = scorecard

    receipt_path = Path(".agent/evidence/golden_benchmark_receipt.json")
    try:
        engine.export_receipt(scorecard, str(receipt_path))
    except Exception as e:
        logger.warning("Could not export benchmark receipt: %s", e)

    return {
        "status": "success",
        "scorecard": scorecard.model_dump(),
    }


@router.get("/benchmark/latest")
async def get_latest_benchmark_scorecard() -> dict[str, Any]:
    """Returns the most recent Golden Flow Benchmark Scorecard and KPI metrics."""
    global _latest_benchmark_scorecard
    if _latest_benchmark_scorecard:
        return {
            "status": "success",
            "scorecard": _latest_benchmark_scorecard.model_dump(),
        }

    receipt_path = Path(".agent/evidence/golden_benchmark_receipt.json")
    if receipt_path.exists():
        try:
            data = json.loads(receipt_path.read_text(encoding="utf-8"))
            return {
                "status": "success",
                "scorecard": data,
            }
        except Exception as e:
            logger.warning("Failed to parse existing benchmark receipt: %s", e)

    raise HTTPException(status_code=404, detail="No benchmark run recorded yet.")
