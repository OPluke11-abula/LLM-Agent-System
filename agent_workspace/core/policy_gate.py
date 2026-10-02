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
    "file_mutation",
    "tool_execution",
]
PolicyScope = Literal["workspace", "session", "tenant"]


CONSENSUS_REQUIRED_ACTIONS: frozenset[str] = frozenset(
    {"ultra_mode", "browser_use", "computer_use", "external_api"}
)

ROLE_SCOPE_RESTRICTIONS: dict[str, dict[str, Any]] = {
    "UI_UX_AGENT": {
        "forbidden_prefixes": ("agent_workspace/", "spec/", "migrations/"),
        "description": "UI_UX_AGENT is strictly prohibited from modifying backend or spec files",
    },
    "BACKEND_INFRA_AGENT": {
        "forbidden_prefixes": ("viewer/",),
        "description": "BACKEND_INFRA_AGENT is strictly prohibited from modifying presentation UI files",
    },
    "DOMAIN_LOGIC_AGENT": {
        "forbidden_prefixes": ("viewer/",),
        "description": "DOMAIN_LOGIC_AGENT must remain framework-agnostic and cannot touch presentation UI",
    },
    "SECURITY_AUDIT_AGENT": {
        "read_only": True,
        "description": "SECURITY_AUDIT_AGENT is a read-only review authority",
    },
    "ARCHITECT_PLANNER_AGENT": {
        "read_only": True,
        "description": "ARCHITECT_PLANNER_AGENT is an advisory specialist and cannot mutate code directly",
    },
    "QA_TEST_AGENT": {
        "read_only": True,
        "description": "QA_TEST_AGENT is a verification authority and cannot mutate production code",
    },
    "PERFORMANCE_LATENCY_AGENT": {
        "read_only": True,
        "description": "PERFORMANCE_LATENCY_AGENT is a benchmarking authority and cannot mutate code",
    },
    "APPLICATION_FLOW_AGENT": {
        "forbidden_prefixes": ("viewer/", "migrations/"),
        "description": "APPLICATION_FLOW_AGENT manages workflows and cannot mutate presentation UI or migrations",
    },
    "INTEGRATION_MERGE_AGENT": {
        "forbidden_prefixes": (),
        "description": "INTEGRATION_MERGE_AGENT handles PR and branch integration",
    },
    "KNOWLEDGE_TOPOLOGY_AGENT": {
        "forbidden_prefixes": ("agent_workspace/core/", "viewer/"),
        "description": "KNOWLEDGE_TOPOLOGY_AGENT maintains documentation and topology notes",
    },
}



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

        # Check command safety for shell / tool execution
        command = request.metadata.get("command") or request.metadata.get("cmd")
        if command and isinstance(command, str):
            from agent_workspace.core.agent_executor import DESTRUCTIVE_COMMAND_PATTERNS
            for pattern in DESTRUCTIVE_COMMAND_PATTERNS:
                if pattern.search(command):
                    return f"Destructive shell command rejected by PolicyGate: '{command}'"

        # Check anti-corruption code patterns if content is provided
        content = request.metadata.get("content")
        target_file = request.resource or request.metadata.get("target_file") or request.metadata.get("file_path")
        if content and isinstance(content, str) and target_file and str(target_file).endswith((".py", ".ts", ".js")):
            from agent_workspace.core.precheck import SkillsPrechecker
            violations = SkillsPrechecker.check_seven_anti_corruption(content, str(target_file))
            if violations:
                return f"Anti-Corruption violation rejected by PolicyGate: {violations[0]}"

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
            rel = resource_path.resolve().relative_to(self._workspace_root)
        except ValueError:
            return "resource outside workspace scope"

        # Check role-based boundary restrictions
        role = request.metadata.get("role") or (request.actor if "AGENT" in request.actor else None)
        if role and role in ROLE_SCOPE_RESTRICTIONS:
            role_rule = ROLE_SCOPE_RESTRICTIONS[role]
            rel_str = str(rel).replace("\\", "/")
            if role_rule.get("read_only") and request.metadata.get("is_write"):
                return f"Role {role} is read-only: {role_rule['description']}"
            for forbidden in role_rule.get("forbidden_prefixes", ()):
                if rel_str.startswith(forbidden):
                    return f"Boundary violation: {role_rule['description']} (attempted: {rel_str})"

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
