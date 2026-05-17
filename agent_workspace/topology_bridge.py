"""
Topology bridge for FindAi Studio.

This module is intentionally standalone. It can be mounted beside the engine's
existing broadcast path without importing or changing the closed-loop runtime.
"""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, ClassVar


SCHEMA_VERSION = "1.0.0"


def utc_now_iso() -> str:
    """Return an ISO-8601 UTC timestamp with a trailing Z."""
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace(
        "+00:00", "Z"
    )


@dataclass(slots=True)
class TopologyEvent:
    event_id: str
    timestamp: str
    session_id: str
    node_id: str
    parent_node_id: str | None
    node_type: str
    edge_type: str | None
    status: str
    payload: dict[str, Any] = field(default_factory=dict)

    ALLOWED_NODE_TYPES: ClassVar[set[str]] = {
        "session_root",
        "agent",
        "handoff",
        "tool_call",
        "hitl_gate",
        "error",
    }
    ALLOWED_EDGE_TYPES: ClassVar[set[str]] = {
        "handoff",
        "tool",
        "rbac",
        "error",
        "hitl",
    }
    ALLOWED_STATUSES: ClassVar[set[str]] = {
        "pending",
        "running",
        "completed",
        "error",
        "awaiting_approval",
    }

    def __post_init__(self) -> None:
        if self.node_type not in self.ALLOWED_NODE_TYPES:
            raise ValueError(f"Unsupported node_type: {self.node_type}")
        if self.edge_type is not None and self.edge_type not in self.ALLOWED_EDGE_TYPES:
            raise ValueError(f"Unsupported edge_type: {self.edge_type}")
        if self.status not in self.ALLOWED_STATUSES:
            raise ValueError(f"Unsupported status: {self.status}")

    @classmethod
    def create(
        cls,
        *,
        session_id: str,
        node_id: str | None = None,
        parent_node_id: str | None = None,
        node_type: str,
        edge_type: str | None = None,
        status: str = "pending",
        payload: dict[str, Any] | None = None,
        event_id: str | None = None,
        timestamp: str | None = None,
    ) -> "TopologyEvent":
        return cls(
            event_id=event_id or f"evt-{uuid.uuid4()}",
            timestamp=timestamp or utc_now_iso(),
            session_id=session_id,
            node_id=node_id or f"node-{uuid.uuid4()}",
            parent_node_id=parent_node_id,
            node_type=node_type,
            edge_type=edge_type,
            status=status,
            payload=payload or {},
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class TopologyEmitter:
    def __init__(self, session_id: str, output_path: str | os.PathLike[str]):
        self.session_id = session_id
        self.output_path = Path(output_path)
        self.started_at = utc_now_iso()
        self._nodes_by_id: dict[str, TopologyEvent] = {}
        self._edges_by_id: dict[str, dict[str, Any]] = {}
        self._load_existing_state()

    def emit(self, event: TopologyEvent) -> dict[str, Any]:
        if event.session_id != self.session_id:
            raise ValueError(
                f"Event session_id {event.session_id!r} does not match emitter "
                f"session_id {self.session_id!r}"
            )

        self._nodes_by_id[event.node_id] = event
        if event.parent_node_id and event.edge_type:
            edge = self._edge_from_event(event)
            self._edges_by_id[edge["id"]] = edge

        state = self._build_state(updated_at=event.timestamp)
        self._atomic_write(state)
        return state

    def _edge_from_event(self, event: TopologyEvent) -> dict[str, Any]:
        edge_id = f"edge-{event.parent_node_id}-{event.node_id}-{event.edge_type}"
        label = (
            event.payload.get("name")
            or event.payload.get("description")
            or event.edge_type
        )
        return {
            "id": edge_id,
            "source": event.parent_node_id,
            "target": event.node_id,
            "edge_type": event.edge_type,
            "label": str(label),
        }

    def _build_state(self, updated_at: str | None = None) -> dict[str, Any]:
        nodes = [
            event.to_dict()
            for event in sorted(self._nodes_by_id.values(), key=lambda item: item.timestamp)
        ]
        edges = sorted(self._edges_by_id.values(), key=lambda item: item["id"])
        stats = self._calculate_stats(nodes)
        return {
            "schema_version": SCHEMA_VERSION,
            "session_id": self.session_id,
            "started_at": self.started_at,
            "updated_at": updated_at or utc_now_iso(),
            "stats": stats,
            "nodes": nodes,
            "edges": edges,
        }

    def _calculate_stats(self, nodes: list[dict[str, Any]]) -> dict[str, int]:
        total_tokens = 0
        total_duration_ms = 0
        status_counts = {
            "completed": 0,
            "running": 0,
            "pending": 0,
            "errors": 0,
        }

        for node in nodes:
            status = node.get("status")
            if status == "completed":
                status_counts["completed"] += 1
            elif status == "running":
                status_counts["running"] += 1
            elif status == "pending":
                status_counts["pending"] += 1
            elif status == "error":
                status_counts["errors"] += 1

            payload = node.get("payload") or {}
            total_tokens += int(payload.get("token_used") or 0)
            total_duration_ms += int(payload.get("duration_ms") or 0)

        return {
            "total_nodes": len(nodes),
            **status_counts,
            "total_tokens": total_tokens,
            "total_duration_ms": total_duration_ms,
        }

    def _atomic_write(self, data: dict[str, Any]) -> None:
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.output_path.with_name(f"{self.output_path.name}.tmp")
        with tmp_path.open("w", encoding="utf-8", newline="\n") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, self.output_path)

    def _load_existing_state(self) -> None:
        if not self.output_path.is_file():
            return

        try:
            with self.output_path.open("r", encoding="utf-8") as handle:
                state = json.load(handle)
        except (json.JSONDecodeError, OSError):
            return

        if state.get("session_id") != self.session_id:
            return

        self.started_at = state.get("started_at") or self.started_at
        for node in state.get("nodes", []):
            event = TopologyEvent(**node)
            self._nodes_by_id[event.node_id] = event
        for edge in state.get("edges", []):
            edge_id = edge.get("id")
            if edge_id:
                self._edges_by_id[edge_id] = edge
