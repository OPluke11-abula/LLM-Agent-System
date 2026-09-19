"""Intrusion Detection System (IDS) for Swarm Node/Role consensus auditing."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .consensus import ProofOfConsensus

logger = logging.getLogger(__name__)


class SwarmIDS:
    """Intrusion Detection System (IDS) for Swarm Node/Role consensus auditing."""

    quarantined_nodes: set[str] = set()
    failures_count: dict[str, int] = {}

    @classmethod
    def record_failure(cls, role: str) -> None:
        role_lower = role.lower()
        cls.failures_count[role_lower] = cls.failures_count.get(role_lower, 0) + 1
        logger.warning(
            "[SwarmIDS] Signature failure recorded for role: %s. Failure count: %d",
            role_lower,
            cls.failures_count[role_lower],
        )
        if cls.failures_count[role_lower] >= 3:
            cls.quarantine_node(role_lower)

    @classmethod
    def quarantine_node(cls, role: str) -> None:
        role_lower = role.lower()
        if role_lower not in cls.quarantined_nodes:
            cls.quarantined_nodes.add(role_lower)
            logger.error("[SwarmIDS] Quarantined malicious swarm node/role: %s", role_lower)
            from .consensus import ProofOfConsensus

            ProofOfConsensus.rotate_session_keys()

    @classmethod
    def is_quarantined(cls, role: str) -> bool:
        return role.lower() in cls.quarantined_nodes

    @classmethod
    def reset(cls) -> None:
        """Helper to clear failures and quarantine for testing."""
        cls.quarantined_nodes.clear()
        cls.failures_count.clear()
