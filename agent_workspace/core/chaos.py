"""
LAS Distributed P2P Mesh - Chaos Fault Injection & Resilience Testing
Phase 91 (Aligned with ADR-005 and ADR-006).

Provides deterministic and stochastic fault injection across P2P mesh nodes and Raft consensus:
  1. NETWORK_PARTITION: Simulates split-brain by partitioning nodes into isolated groups.
  2. LATENCY_SPIKE: Injects artificial delay into inter-node RPC communications.
  3. PACKET_DROP: Stochastically or deterministically drops messages between nodes.
  4. NODE_ISOLATION: Completely isolates a specific node from all incoming and outgoing mesh traffic.
  5. BYZANTINE_TAMPER: Simulates payload corruption to verify Zero-Trust signature verification.
"""

from __future__ import annotations

import logging
import random
import threading
import time
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger("MeshChaosManager")


class ChaosFaultType(str, Enum):
    NETWORK_PARTITION = "NETWORK_PARTITION"
    LATENCY_SPIKE = "LATENCY_SPIKE"
    PACKET_DROP = "PACKET_DROP"
    NODE_ISOLATION = "NODE_ISOLATION"
    BYZANTINE_TAMPER = "BYZANTINE_TAMPER"


class ChaosFaultRule(BaseModel):
    """Represents an active chaos fault rule applied to the mesh transport."""
    model_config = ConfigDict(extra="forbid")

    rule_id: str = Field(default_factory=lambda: f"chaos-{uuid.uuid4().hex[:8]}")
    fault_type: ChaosFaultType
    source_node_ids: List[str] = Field(
        default_factory=list,
        description="Source nodes affected by the rule. Empty list applies to all source nodes.",
    )
    target_node_ids: List[str] = Field(
        default_factory=list,
        description="Target nodes affected by the rule. Empty list applies to all target nodes.",
    )
    probability: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Probability (0.0 - 1.0) of applying fault on eligible calls.",
    )
    latency_ms: float = Field(
        default=0.0,
        ge=0.0,
        description="Artificial delay in milliseconds for LATENCY_SPIKE faults.",
    )
    duration_seconds: Optional[float] = Field(
        default=None,
        description="Optional auto-expiration duration in seconds.",
    )
    created_at: float = Field(default_factory=time.time)
    expires_at: Optional[float] = None
    description: str = Field(default="")

    def is_expired(self, current_time: Optional[float] = None) -> bool:
        now = current_time or time.time()
        return self.expires_at is not None and now > self.expires_at


class MeshChaosManager:
    """
    Central coordinator for managing chaos fault rules across the distributed mesh.
    All coordinators and Raft consensus engines consult this manager before dispatching RPCs.
    """

    _global_instance: Optional[MeshChaosManager] = None

    def __init__(self):
        self.rules: Dict[str, ChaosFaultRule] = {}
        self._lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> MeshChaosManager:
        if cls._global_instance is None:
            cls._global_instance = MeshChaosManager()
        return cls._global_instance

    def inject_fault(
        self,
        fault_type: ChaosFaultType,
        source_node_ids: Optional[List[str]] = None,
        target_node_ids: Optional[List[str]] = None,
        probability: float = 1.0,
        latency_ms: float = 0.0,
        duration_seconds: Optional[float] = None,
        description: str = "",
    ) -> ChaosFaultRule:
        """Injects a new chaos fault rule into the mesh."""
        now = time.time()
        expires_at = (now + duration_seconds) if duration_seconds is not None else None

        rule = ChaosFaultRule(
            fault_type=fault_type,
            source_node_ids=list(source_node_ids or []),
            target_node_ids=list(target_node_ids or []),
            probability=probability,
            latency_ms=latency_ms,
            duration_seconds=duration_seconds,
            created_at=now,
            expires_at=expires_at,
            description=description or f"Chaos {fault_type.value}",
        )

        with self._lock:
            self.rules[rule.rule_id] = rule

        logger.warning(
            f"[Chaos Injected] Rule {rule.rule_id}: {rule.fault_type.value} "
            f"(src={rule.source_node_ids or 'ALL'} -> dst={rule.target_node_ids or 'ALL'}, "
            f"prob={rule.probability}, delay={rule.latency_ms}ms, ttl={rule.duration_seconds}s)"
        )
        return rule

    def create_partition(
        self,
        partition_a: List[str],
        partition_b: List[str],
        duration_seconds: Optional[float] = None,
        description: str = "Split-brain network partition",
    ) -> List[str]:
        """Creates a bidirectional network partition between partition_a and partition_b."""
        rule_a_to_b = self.inject_fault(
            fault_type=ChaosFaultType.NETWORK_PARTITION,
            source_node_ids=partition_a,
            target_node_ids=partition_b,
            probability=1.0,
            duration_seconds=duration_seconds,
            description=f"{description} (A -> B)",
        )
        rule_b_to_a = self.inject_fault(
            fault_type=ChaosFaultType.NETWORK_PARTITION,
            source_node_ids=partition_b,
            target_node_ids=partition_a,
            probability=1.0,
            duration_seconds=duration_seconds,
            description=f"{description} (B -> A)",
        )
        return [rule_a_to_b.rule_id, rule_b_to_a.rule_id]

    def isolate_node(
        self,
        node_id: str,
        duration_seconds: Optional[float] = None,
        description: str = "Isolate single node from cluster",
    ) -> str:
        """Completely isolates a single node from all incoming and outgoing mesh traffic."""
        rule = self.inject_fault(
            fault_type=ChaosFaultType.NODE_ISOLATION,
            source_node_ids=[node_id],
            target_node_ids=[],
            probability=1.0,
            duration_seconds=duration_seconds,
            description=f"{description} (node={node_id})",
        )
        return rule.rule_id

    def clear_fault(self, rule_id: str) -> bool:
        """Removes a specific chaos fault rule."""
        with self._lock:
            removed = self.rules.pop(rule_id, None)
        if removed:
            logger.info(f"[Chaos Cleared] Rule {rule_id} removed.")
            return True
        return False

    def clear_all_faults(self) -> int:
        """Removes all active chaos fault rules."""
        with self._lock:
            count = len(self.rules)
            self.rules.clear()
        logger.info(f"[Chaos Cleared] All {count} active rules cleared.")
        return count

    def list_active_faults(self) -> List[ChaosFaultRule]:
        """Returns all currently active non-expired fault rules, pruning expired rules."""
        now = time.time()
        active: List[ChaosFaultRule] = []
        with self._lock:
            expired_keys = []
            for rid, rule in self.rules.items():
                if rule.is_expired(now):
                    expired_keys.append(rid)
                else:
                    active.append(rule)
            for k in expired_keys:
                del self.rules[k]
        return active

    def evaluate_traffic(
        self,
        source_node_id: str,
        target_node_id: str,
        rpc_type: str = "rpc",
    ) -> Tuple[bool, float, bool]:
        """
        Evaluates active chaos rules for a communication attempt from source to target.

        Returns:
            Tuple of:
              - is_blocked (bool): True if communication is dropped or partitioned.
              - latency_ms (float): Total injected artificial delay.
              - is_tampered (bool): True if Byzantine payload corruption is simulated.
        """
        active_rules = self.list_active_faults()
        if not active_rules:
            return False, 0.0, False

        is_blocked = False
        total_latency_ms = 0.0
        is_tampered = False

        for rule in active_rules:
            # Check source match
            if rule.source_node_ids and source_node_id not in rule.source_node_ids:
                # Special case for NODE_ISOLATION: also applies if target is isolated
                if rule.fault_type == ChaosFaultType.NODE_ISOLATION:
                    if target_node_id not in rule.source_node_ids:
                        continue
                else:
                    continue

            # Check target match
            if rule.target_node_ids and target_node_id not in rule.target_node_ids:
                continue

            # Apply probability dice roll
            if rule.probability < 1.0 and random.random() > rule.probability:
                continue

            # Apply fault action
            if rule.fault_type in (
                ChaosFaultType.NETWORK_PARTITION,
                ChaosFaultType.NODE_ISOLATION,
            ):
                is_blocked = True
                logger.debug(
                    f"[Chaos Blocked] {rpc_type} from {source_node_id} to {target_node_id} "
                    f"blocked by {rule.fault_type.value} ({rule.rule_id})"
                )
                break

            elif rule.fault_type == ChaosFaultType.PACKET_DROP:
                is_blocked = True
                logger.debug(
                    f"[Chaos Dropped] {rpc_type} from {source_node_id} to {target_node_id} "
                    f"dropped by PACKET_DROP ({rule.rule_id})"
                )
                break

            elif rule.fault_type == ChaosFaultType.LATENCY_SPIKE:
                total_latency_ms += rule.latency_ms

            elif rule.fault_type == ChaosFaultType.BYZANTINE_TAMPER:
                is_tampered = True

        return is_blocked, total_latency_ms, is_tampered
