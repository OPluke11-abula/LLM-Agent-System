"""Swarm Route Registry module for tracking and pruning agent execution paths."""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class SwarmRouteRegistry:
    """Registry tracking route health, latency history, active load, and automated pruning."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.routes: dict[str, dict[str, Any]] = {}
        self.pruned_history: list[dict[str, Any]] = []

    def register_route(self, node_id: str) -> None:
        with self.lock:
            if node_id not in self.routes:
                self.routes[node_id] = {
                    "node_id": node_id,
                    "latency_history": [],
                    "success_count": 0,
                    "failure_count": 0,
                    "success_rate": 1.0,
                    "active_load": 0,
                    "status": "active",
                    "last_seen": datetime.now(timezone.utc).isoformat(),
                }

    def start_dispatch(self, node_id: str) -> None:
        self.register_route(node_id)
        with self.lock:
            route = self.routes[node_id]
            route["active_load"] += 1
            route["last_seen"] = datetime.now(timezone.utc).isoformat()

    def end_dispatch(self, node_id: str, latency_sec: float, success: bool) -> None:
        with self.lock:
            if node_id not in self.routes:
                return
            route = self.routes[node_id]
            route["active_load"] = max(0, route["active_load"] - 1)
            route["latency_history"].append(latency_sec)
            if len(route["latency_history"]) > 20:
                route["latency_history"] = route["latency_history"][-20:]

            if success:
                route["success_count"] += 1
            else:
                route["failure_count"] += 1

            total = route["success_count"] + route["failure_count"]
            if total > 0:
                route["success_rate"] = route["success_count"] / total

            route["last_seen"] = datetime.now(timezone.utc).isoformat()

            # Check for auto-pruning
            self._check_auto_prune(route)

    def _check_auto_prune(self, route: dict[str, Any]) -> None:
        node_id = route["node_id"]
        if route["status"] == "pruned":
            return

        total = route["success_count"] + route["failure_count"]
        # Thresholds: success_rate < 70% or average latency of last 3 dispatches > 0.5s (500ms)
        # Only evaluate pruning if minimum dispatches >= 3
        if total >= 3:
            avg_latency = sum(route["latency_history"][-3:]) / min(len(route["latency_history"]), 3)
            reason = None
            if route["success_rate"] < 0.7:
                reason = f"Low success rate: {route['success_rate']:.2%}"
            elif avg_latency > 0.5:
                reason = f"High latency: {avg_latency*1000:.1f}ms"

            if reason:
                route["status"] = "pruned"
                prune_entry = {
                    "node_id": node_id,
                    "pruned_at": datetime.now(timezone.utc).isoformat(),
                    "reason": reason,
                    "success_rate": route["success_rate"],
                    "avg_latency_ms": avg_latency * 1000,
                }
                self.pruned_history.append(prune_entry)
                logger.warning("Pruned route '%s': %s", node_id, reason)

    def prune_stale_or_all(self, force_all: bool = False) -> bool:
        with self.lock:
            now = datetime.now(timezone.utc)
            pruned_any = False
            for node_id, route in list(self.routes.items()):
                if route["status"] == "pruned":
                    continue

                # Check stale
                last_seen_dt = datetime.fromisoformat(route["last_seen"])
                age_sec = (now - last_seen_dt).total_seconds()

                reason = None
                if force_all:
                    reason = "Manual administrative prune trigger"
                elif age_sec > 30.0:  # stale threshold of 30 seconds
                    reason = f"Stale route: inactive for {age_sec:.1f}s"

                if reason:
                    route["status"] = "pruned"
                    pruned_any = True
                    self.pruned_history.append({
                        "node_id": node_id,
                        "pruned_at": datetime.now(timezone.utc).isoformat(),
                        "reason": reason,
                        "success_rate": route["success_rate"],
                        "avg_latency_ms": (sum(route["latency_history"]) / len(route["latency_history"]) * 1000) if route["latency_history"] else 0.0,
                    })
                    logger.info("Administrative prune performed on '%s': %s", node_id, reason)
            return pruned_any


ROUTE_REGISTRY = SwarmRouteRegistry()
