"""Dual-Stream Forensic Correlator (Phase 93 / GAP-07).

Unifies and cryptographically correlates two complementary ledgers:
1. AuditLedger (audit_ledger.db): Authoritative Merkle-chained compliance audit trail.
2. RuntimeEventsLedger (runtime_events.db): Granular execution plane lifecycle telemetry.

Provides a single forensic API and receipt verifying tamper-evident integrity across both streams.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from agent_workspace.core.audit_ledger import AuditLedger
from agent_workspace.core.runtime_events import RuntimeEventsLedger

logger = logging.getLogger(__name__)


class ForensicEventItem(BaseModel):
    """Normalized event record spanning compliance and runtime execution streams."""

    model_config = ConfigDict(extra="forbid")

    stream: Literal["compliance_audit", "runtime_execution"]
    event_id: int
    event_type: str
    timestamp: str
    session_id: str
    payload: dict[str, Any]
    current_hash: str
    previous_hash: str


class ForensicSessionTimeline(BaseModel):
    """Complete tamper-evident forensic timeline for an agent session."""

    model_config = ConfigDict(extra="forbid")

    session_id: str
    total_events: int
    audit_event_count: int
    runtime_event_count: int
    audit_chain_valid: bool
    audit_merkle_root: Optional[str] = None
    runtime_chain_valid: bool
    runtime_merkle_root: Optional[str] = None
    is_tamper_free: bool
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    timeline: list[ForensicEventItem] = Field(default_factory=list)


class ForensicCorrelator:
    """Forensic correlation engine unifying AuditLedger and RuntimeEventsLedger."""

    def __init__(self, workspace_path: str):
        self.workspace_path = str(Path(workspace_path).resolve())
        self.audit_ledger = AuditLedger(workspace_path=self.workspace_path)
        self.runtime_ledger = RuntimeEventsLedger(workspace_path=self.workspace_path)

    def correlate_session(
        self, session_id: str, tenant_id: str = "default_tenant"
    ) -> ForensicSessionTimeline:
        """Correlate all audit and runtime events for a session into a unified, verified timeline."""
        # 1. Verify and query compliance audit ledger
        audit_check = self.audit_ledger.verify_chain_integrity()
        audit_valid = bool(audit_check.get("valid", False))
        audit_root = audit_check.get("merkle_root")

        all_audit_logs = self.audit_ledger.get_logs(tenant_id=tenant_id)
        if tenant_id != "default_tenant":
            for l in self.audit_ledger.get_logs(tenant_id="default_tenant"):
                if l["id"] not in {x["id"] for x in all_audit_logs}:
                    all_audit_logs.append(l)
        if session_id not in (tenant_id, "default_tenant"):
            for l in self.audit_ledger.get_logs(tenant_id=session_id):
                if l["id"] not in {x["id"] for x in all_audit_logs}:
                    all_audit_logs.append(l)
        matched_audit_events: list[ForensicEventItem] = []

        for log in all_audit_logs:
            payload = log.get("payload") or {}
            if isinstance(payload, str):
                try:
                    payload = json.loads(payload)
                except Exception:
                    payload = {}

            # Check matching session or task
            log_session = (
                payload.get("session_id")
                or payload.get("task_id")
                or (log.get("tenant_id") if log.get("tenant_id") == session_id else None)
            )
            if log_session == session_id:
                matched_audit_events.append(
                    ForensicEventItem(
                        stream="compliance_audit",
                        event_id=log["id"],
                        event_type=log["event_type"],
                        timestamp=log["timestamp"],
                        session_id=session_id,
                        payload=payload,
                        current_hash=log["current_hash"],
                        previous_hash=log["previous_hash"],
                    )
                )

        # 2. Verify and query runtime execution ledger
        runtime_events = self.runtime_ledger.get_events_for_task(session_id)
        runtime_valid = self.runtime_ledger.verify_chain_integrity(session_id)
        runtime_root = self.runtime_ledger.calculate_merkle_root(session_id) if runtime_events else None

        matched_runtime_events: list[ForensicEventItem] = []
        for rev in runtime_events:
            matched_runtime_events.append(
                ForensicEventItem(
                    stream="runtime_execution",
                    event_id=rev.event_id,
                    event_type=rev.event_type.value if hasattr(rev.event_type, "value") else str(rev.event_type),
                    timestamp=rev.timestamp,
                    session_id=session_id,
                    payload=rev.payload,
                    current_hash=rev.current_hash,
                    previous_hash=rev.previous_hash,
                )
            )

        # 3. Merge and sort chronologically
        combined = matched_audit_events + matched_runtime_events
        combined.sort(key=lambda x: x.timestamp)

        # A session is tamper-free if both ledgers have valid hash chains
        is_tamper_free = audit_valid and runtime_valid

        return ForensicSessionTimeline(
            session_id=session_id,
            total_events=len(combined),
            audit_event_count=len(matched_audit_events),
            runtime_event_count=len(matched_runtime_events),
            audit_chain_valid=audit_valid,
            audit_merkle_root=audit_root,
            runtime_chain_valid=runtime_valid,
            runtime_merkle_root=runtime_root,
            is_tamper_free=is_tamper_free,
            timeline=combined,
        )

    def export_forensic_receipt(
        self, session_id: str, output_path: Optional[str] = None
    ) -> Path:
        """Export serialized forensic receipt to JSON file."""
        timeline = self.correlate_session(session_id)
        if output_path:
            target = Path(output_path)
        else:
            target = Path(self.workspace_path) / ".agent" / "evidence" / f"forensic_{session_id}.json"

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(timeline.model_dump_json(indent=2), encoding="utf-8")
        logger.info("[ForensicCorrelator] Exported forensic receipt to '%s'", target)
        return target
