"""Unified policy gate for high-impact LAS runtime actions."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field

from .audit_ledger import AuditLedger
from .discussion_room import ProofOfConsensus


PolicyAction = Literal[
    "ultra_mode",
    "browser_use",
    "computer_use",
    "safety_scan",
    "external_api",
]
PolicyScope = Literal["workspace", "session", "tenant"]


CONSENSUS_REQUIRED_ACTIONS: frozenset[str] = frozenset(
    {"ultra_mode", "browser_use", "computer_use", "external_api"}
)


class PolicyGateRequest(BaseModel):
    """Request evaluated by the runtime policy gate."""

    model_config = ConfigDict(extra="forbid")

    action: PolicyAction
    scope: PolicyScope
    session_id: str = Field(min_length=1)
    tenant_id: str = "default_tenant"
    actor: str = "system"
    resource: str | None = None
    payload_hash: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    consensus_certificate: dict[str, Any] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class PolicyGateDecision(BaseModel):
    """Audit-friendly decision returned by the unified policy gate."""

    model_config = ConfigDict(extra="forbid")

    allowed: bool
    action: PolicyAction
    scope: PolicyScope
    reason: str
    required_guard: str
    payload_hash: str
    audit_event_id: int


class UnifiedPolicyGate:
    """Fail-closed policy gate for sensitive runtime actions."""

    def __init__(self, workspace_path: str):
        self.workspace_path = str(Path(workspace_path).resolve())
        self._workspace_root = Path(self.workspace_path)
        self._audit = AuditLedger(self.workspace_path)

    @staticmethod
    def payload_hash_for(request: PolicyGateRequest) -> str:
        payload = request.model_dump(
            mode="json",
            exclude={"consensus_certificate", "payload_hash"},
        )
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def evaluate(self, request: PolicyGateRequest) -> PolicyGateDecision:
        payload_hash = request.payload_hash or self.payload_hash_for(request)
        allowed = False
        reason = "policy denied"
        required_guard = "audit_only"

        scope_error = self._validate_scope(request)
        if scope_error:
            reason = scope_error
            required_guard = "scope_guard"
        elif request.action in CONSENSUS_REQUIRED_ACTIONS:
            required_guard = "proof_of_consensus"
            if self._has_valid_consensus(request, payload_hash):
                allowed = True
                reason = "proof of consensus accepted"
            else:
                reason = "proof of consensus required"
        else:
            allowed = True
            reason = "audit-only policy accepted"

        event_id = self._record_decision(request, allowed, reason, required_guard, payload_hash)
        return PolicyGateDecision(
            allowed=allowed,
            action=request.action,
            scope=request.scope,
            reason=reason,
            required_guard=required_guard,
            payload_hash=payload_hash,
            audit_event_id=event_id,
        )

    def _validate_scope(self, request: PolicyGateRequest) -> str | None:
        if request.scope == "tenant" and not request.tenant_id:
            return "tenant scope requires tenant_id"
        if request.scope == "session" and not request.session_id:
            return "session scope requires session_id"
        if not request.resource:
            return None

        parsed = urlparse(request.resource)
        if parsed.scheme in {"http", "https"} and parsed.netloc:
            if request.action != "external_api":
                return "URL resources are only allowed for external API actions"
            if parsed.scheme != "https":
                return "external API resources require https"
            if parsed.username or parsed.password:
                return "external API resources must not embed credentials"
            return None

        resource_path = Path(request.resource)
        if not resource_path.is_absolute():
            resource_path = self._workspace_root / resource_path
        try:
            resource_path.resolve().relative_to(self._workspace_root)
        except ValueError:
            return "resource outside workspace scope"
        return None

    def _has_valid_consensus(self, request: PolicyGateRequest, payload_hash: str) -> bool:
        certificate = request.consensus_certificate
        if certificate is not None:
            if certificate.get("payload_hash") != payload_hash:
                return False
            return ProofOfConsensus.verify_consensus_certificate(certificate)
        return ProofOfConsensus.is_consensus_approved(self.workspace_path, payload_hash)

    def _record_decision(
        self,
        request: PolicyGateRequest,
        allowed: bool,
        reason: str,
        required_guard: str,
        payload_hash: str,
    ) -> int:
        return self._audit.record_event(
            "policy_gate_decision",
            {
                "action": request.action,
                "scope": request.scope,
                "session_id": request.session_id,
                "actor": request.actor,
                "resource": request.resource,
                "allowed": allowed,
                "reason": reason,
                "required_guard": required_guard,
                "payload_hash": payload_hash,
                "metadata_keys": sorted(request.metadata.keys()),
            },
            tenant_id=request.tenant_id,
        )
