"""Proof of Consensus (PoC) decentralized verification and voting engine."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agent_workspace.core.security import get_secret_bytes
from .ids import SwarmIDS

logger = logging.getLogger(__name__)


class ProofOfConsensus:
    """Implements decentralized Proof of Consensus (PoC) for the swarm."""

    ROLES = ("ceo", "cto", "dev", "qa", "cfo")
    SECRET_KEYS: dict[str, str | None] = {role: None for role in ROLES}
    CONSENSUS_KEY: str | None = None

    @classmethod
    def _load_configured_keys(cls) -> None:
        cls.SECRET_KEYS = {
            role: get_secret_bytes(f"LAS_POC_SECRET_{role.upper()}").decode("utf-8")
            for role in cls.ROLES
        }
        cls.CONSENSUS_KEY = get_secret_bytes("LAS_POC_CONSENSUS_SECRET").decode("utf-8")

    @classmethod
    def rotate_session_keys(cls) -> None:
        """Rotates SECRET_KEYS and CONSENSUS_KEY dynamically using a random rotation suffix."""
        import secrets

        cls.SECRET_KEYS = {role: secrets.token_urlsafe(32) for role in cls.ROLES}
        cls.CONSENSUS_KEY = secrets.token_urlsafe(32)
        logger.info("[ProofOfConsensus] Swarm session keys rotated")

    @classmethod
    def reset_keys(cls) -> None:
        """Restores default SECRET_KEYS and CONSENSUS_KEY values."""
        cls._load_configured_keys()

    @classmethod
    def get_swarm_members(cls) -> list[str]:
        return list(cls.ROLES)

    @classmethod
    def generate_member_signature(cls, role: str, payload_hash: str) -> str:
        """Generates a SHA256 signature for a specific role and payload hash."""
        normalized_role = role.lower()
        if normalized_role not in cls.ROLES:
            raise ValueError(f"Unknown consensus role: {role}")
        if not cls.SECRET_KEYS.get(normalized_role):
            cls._load_configured_keys()
        secret = cls.SECRET_KEYS.get(normalized_role)
        if not secret:
            raise RuntimeError(f"Consensus secret for role {normalized_role} is unavailable.")
        return hashlib.sha256(f"{normalized_role}:{payload_hash}:{secret}".encode("utf-8")).hexdigest()

    @classmethod
    def create_consensus_certificate(cls, payload_hash: str, approved_roles: list[str]) -> dict[str, Any]:
        """Creates a signed consensus certificate if a majority approves."""
        swarm_members = cls.get_swarm_members()
        # Exclude quarantined roles
        approvals = [
            r.lower()
            for r in approved_roles
            if r.lower() in swarm_members and not SwarmIDS.is_quarantined(r.lower())
        ]

        # Majority is > 50% of the swarm
        majority_needed = (len(swarm_members) // 2) + 1  # 3 out of 5

        if len(approvals) < majority_needed:
            raise ValueError(f"Consensus failed: only got {len(approvals)}/{majority_needed} approvals.")

        signatures = {}
        for role in approvals:
            signatures[role] = cls.generate_member_signature(role, payload_hash)

        sorted_roles = sorted(approvals)
        roles_str = ",".join(sorted_roles)

        # Master signature
        master_sig = hashlib.sha256(
            f"consensus:{payload_hash}:{roles_str}:{cls.CONSENSUS_KEY}".encode("utf-8")
        ).hexdigest()

        return {
            "payload_hash": payload_hash,
            "approvals": approvals,
            "signatures": signatures,
            "consensus_signature": master_sig,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    @classmethod
    def verify_consensus_certificate(cls, certificate: dict[str, Any]) -> bool:
        """Verifies if the consensus certificate is cryptographically valid and has a majority."""
        try:
            payload_hash = certificate["payload_hash"]
            approvals = certificate["approvals"]
            signatures = certificate["signatures"]
            consensus_signature = certificate["consensus_signature"]

            swarm_members = cls.get_swarm_members()
            valid_approvals = []

            # Verify each signature
            for role in approvals:
                if role not in swarm_members:
                    continue
                if SwarmIDS.is_quarantined(role):
                    logger.warning("[ProofOfConsensus] Quarantined node '%s' signature validation skipped.", role)
                    continue
                expected_sig = cls.generate_member_signature(role, payload_hash)
                if signatures.get(role) == expected_sig:
                    valid_approvals.append(role)
                else:
                    logger.warning(
                        "[ProofOfConsensus] Signature mismatch for role '%s'. Expected %s, got %s",
                        role,
                        expected_sig,
                        signatures.get(role),
                    )
                    SwarmIDS.record_failure(role)

            majority_needed = (len(swarm_members) // 2) + 1
            if len(valid_approvals) < majority_needed:
                logger.warning(
                    "Verification failed: Not enough valid member signatures (%d/%d)",
                    len(valid_approvals),
                    majority_needed,
                )
                return False

            # Verify master consensus signature
            sorted_roles = sorted(valid_approvals)
            roles_str = ",".join(sorted_roles)
            expected_master_sig = hashlib.sha256(
                f"consensus:{payload_hash}:{roles_str}:{cls.CONSENSUS_KEY}".encode("utf-8")
            ).hexdigest()

            if consensus_signature != expected_master_sig:
                logger.warning("Verification failed: Master consensus signature mismatch")
                return False

            return True
        except Exception as e:
            logger.error("Failed to verify consensus certificate: %s", e)
            return False

    @classmethod
    def register_consensus(cls, workspace_path: str, payload_hash: str, certificate: dict[str, Any]) -> None:
        """Persists the verified consensus certificate to a local swarm registry."""
        if not cls.verify_consensus_certificate(certificate):
            raise ValueError("Cannot register invalid consensus certificate.")

        # Log consensus registration to AuditLedger
        from agent_workspace.core.audit_ledger import AuditLedger

        try:
            audit = AuditLedger(workspace_path)
            audit.record_event(
                "consensus_vote",
                {
                    "payload_hash": payload_hash,
                    "approvals": certificate.get("approvals", []),
                    "consensus_signature": certificate.get("consensus_signature"),
                },
            )
        except Exception as e:
            logger.warning("[ProofOfConsensus] Audit logging failed: %s", e)

        project_root = Path(workspace_path)
        if not (project_root / ".agent").is_dir() and (project_root.parent / ".agent").is_dir():
            project_root = project_root.parent

        registry_dir = project_root / ".agent" / "memory"
        registry_dir.mkdir(parents=True, exist_ok=True)
        registry_file = registry_dir / "consensus_registry.json"

        registry = {}
        if registry_file.is_file():
            try:
                registry = json.loads(registry_file.read_text(encoding="utf-8"))
            except Exception:
                registry = {}

        registry[payload_hash] = certificate

        try:
            registry_file.write_text(json.dumps(registry, indent=2, ensure_ascii=False), encoding="utf-8")
            logger.info("Successfully registered consensus certificate for hash: %s", payload_hash)
        except Exception as e:
            logger.error("Failed to write to consensus_registry.json: %s", e)

    @classmethod
    def is_consensus_approved(cls, workspace_path: str, payload_hash: str) -> bool:
        """Checks if a payload hash is registered and cryptographically valid in the local consensus registry."""
        project_root = Path(workspace_path)
        if not (project_root / ".agent").is_dir() and (project_root.parent / ".agent").is_dir():
            project_root = project_root.parent

        registry_file = project_root / ".agent" / "memory" / "consensus_registry.json"
        if not registry_file.is_file():
            return False

        try:
            registry = json.loads(registry_file.read_text(encoding="utf-8"))
            if payload_hash in registry:
                return cls.verify_consensus_certificate(registry[payload_hash])
        except Exception:
            pass
        return False
