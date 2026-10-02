import os
import json
import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("GovernanceManager")

LATENCY_RULE_TEMPLATE = "Optimize agent latency by disabling verbose debug loops and enforcing strict token limits."
SAFETY_RULE_TEMPLATE = "Enforce strict validation of system commands, blocking unauthorized access to workspace configurations."

def _get_governance_file(workspace_path: str) -> Path:
    project_root = Path(workspace_path)
    if not (project_root / ".agent").is_dir() and (project_root.parent / ".agent").is_dir():
        project_root = project_root.parent
    governance_dir = project_root / ".agent" / "memory"
    governance_dir.mkdir(parents=True, exist_ok=True)
    return governance_dir / "governance_rules.json"

def _load_governance(workspace_path: str) -> dict:
    file_path = _get_governance_file(workspace_path)
    if not file_path.is_file():
        return {"proposals": {}}
    try:
        return json.loads(file_path.read_text(encoding="utf-8"))
    except Exception:
        return {"proposals": {}}

def _save_governance(workspace_path: str, data: dict):
    file_path = _get_governance_file(workspace_path)
    file_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

class GovernanceManager:
    """Manages swarm prompt policy calibrations and decentralized voting."""

    @classmethod
    def check_and_trigger_calibration(cls, workspace_path: str) -> Optional[dict]:
        """Scans the AuditLedger logs for anomalies and triggers proposals."""
        from agent_workspace.core.audit_ledger import AuditLedger

        audit = AuditLedger(workspace_path)
        logs = audit.get_logs()

        latency_anomaly = False
        safety_anomaly = False

        for log in logs:
            event_type = log.get("event_type")
            payload = log.get("payload") or {}

            if event_type in ("SOC2_VIOLATION", "safety_exception"):
                safety_anomaly = True

            if isinstance(payload, dict):
                duration = payload.get("duration_ms")
                try:
                    if duration is not None and float(duration) > 5000:
                        latency_anomaly = True
                except ValueError:
                    pass
                if payload.get("active_latency_alert") is True:
                    latency_anomaly = True

        data = _load_governance(workspace_path)
        proposals = data.get("proposals", {})

        new_proposal = None

        # Check and propose for latency anomaly
        if latency_anomaly:
            # check if proposed or accepted already exists
            existing = any(
                p.get("rule_type") == "latency_overrun" and p.get("status") in ("proposed", "accepted")
                for p in proposals.values()
            )
            if not existing:
                proposal_id = f"prop_latency_{int(datetime.now(timezone.utc).timestamp())}"
                payload_hash = hashlib.sha256(LATENCY_RULE_TEMPLATE.encode("utf-8")).hexdigest()
                new_proposal = {
                    "id": proposal_id,
                    "rule_type": "latency_overrun",
                    "rule_text": LATENCY_RULE_TEMPLATE,
                    "status": "proposed",
                    "payload_hash": payload_hash,
                    "votes": {},
                    "signatures": {},
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                proposals[proposal_id] = new_proposal

        # Check and propose for safety anomaly
        if safety_anomaly and not new_proposal:
            existing = any(
                p.get("rule_type") == "safety_violation" and p.get("status") in ("proposed", "accepted")
                for p in proposals.values()
            )
            if not existing:
                proposal_id = f"prop_safety_{int(datetime.now(timezone.utc).timestamp())}"
                payload_hash = hashlib.sha256(SAFETY_RULE_TEMPLATE.encode("utf-8")).hexdigest()
                new_proposal = {
                    "id": proposal_id,
                    "rule_type": "safety_violation",
                    "rule_text": SAFETY_RULE_TEMPLATE,
                    "status": "proposed",
                    "payload_hash": payload_hash,
                    "votes": {},
                    "signatures": {},
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                proposals[proposal_id] = new_proposal

        if new_proposal:
            data["proposals"] = proposals
            _save_governance(workspace_path, data)
            logger.info("Triggered calibration proposal: %s", new_proposal["id"])

        return new_proposal

    @classmethod
    def cast_vote(cls, workspace_path: str, proposal_id: str, role: str, vote: str, signature: str) -> bool:
        """Verifies vote signature and updates proposal status upon cryptographic consensus."""
        from agent_workspace.core.discussion_room import ProofOfConsensus

        data = _load_governance(workspace_path)
        proposals = data.get("proposals", {})

        if proposal_id not in proposals:
            raise ValueError(f"Proposal '{proposal_id}' not found.")

        proposal = proposals[proposal_id]
        payload_hash = proposal["payload_hash"]

        # Verify cryptographic signature
        expected_sig = ProofOfConsensus.generate_member_signature(role, payload_hash)
        if signature != expected_sig:
            logger.warning("Invalid vote signature from role %s for proposal %s", role, proposal_id)
            return False

        # Record vote
        proposal["votes"][role.lower()] = vote.lower()
        proposal["signatures"][role.lower()] = signature

        # Evaluate consensus status
        approved_roles = [r for r, v in proposal["votes"].items() if v == "approve"]
        rejected_roles = [r for r, v in proposal["votes"].items() if v == "reject"]

        # Swarm has 5 roles: ceo, cto, dev, qa, cfo
        # Majority is strictly > 50% (i.e., >= 3)
        if len(approved_roles) >= 3:
            try:
                cert = ProofOfConsensus.create_consensus_certificate(payload_hash, approved_roles)
                ProofOfConsensus.register_consensus(workspace_path, payload_hash, cert)
                proposal["status"] = "accepted"
                proposal["certificate"] = cert
                logger.info("Proposal %s accepted by cryptographic consensus.", proposal_id)
            except Exception as e:
                logger.error("Failed to register consensus for proposal %s: %s", proposal_id, e)
                return False
        elif len(rejected_roles) >= 3:
            proposal["status"] = "rejected"
            logger.info("Proposal %s rejected.", proposal_id)

        _save_governance(workspace_path, data)
        return True

    @classmethod
    def get_active_rules(cls, workspace_path: str) -> List[str]:
        """Returns the list of active calibrated rules certified by cryptographic consensus."""
        from agent_workspace.core.discussion_room import ProofOfConsensus

        data = _load_governance(workspace_path)
        proposals = data.get("proposals", {})

        active_rules = []
        for prop in proposals.values():
            if prop.get("status") == "accepted":
                payload_hash = prop["payload_hash"]
                if ProofOfConsensus.is_consensus_approved(workspace_path, payload_hash):
                    active_rules.append(prop["rule_text"])

        return active_rules

    @classmethod
    def get_all_proposals(cls, workspace_path: str) -> dict:
        """Helper to return all proposals."""
        data = _load_governance(workspace_path)
        return data.get("proposals", {})
