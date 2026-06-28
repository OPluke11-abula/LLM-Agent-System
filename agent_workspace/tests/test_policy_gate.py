from pathlib import Path

from agent_workspace.core.audit_ledger import AuditLedger
from agent_workspace.core.discussion_room import ProofOfConsensus
from agent_workspace.core.policy_gate import PolicyGateRequest, UnifiedPolicyGate


def _workspace(tmp_path: Path) -> str:
    (tmp_path / ".agent" / "memory").mkdir(parents=True)
    return str(tmp_path)


def test_external_api_requires_proof_of_consensus_and_logs_denial(tmp_path):
    workspace = _workspace(tmp_path)
    gate = UnifiedPolicyGate(workspace)

    decision = gate.evaluate(
        PolicyGateRequest(
            action="external_api",
            scope="workspace",
            session_id="session-1",
            resource="https://api.example.com/v1/sync",
        )
    )

    assert decision.allowed is False
    assert decision.required_guard == "proof_of_consensus"
    assert decision.reason == "proof of consensus required"

    logs = AuditLedger(workspace).get_logs("policy_gate_decision")
    assert logs[-1]["payload"]["allowed"] is False
    assert logs[-1]["payload"]["action"] == "external_api"


def test_consensus_certificate_allows_browser_use_and_records_policy_decision(tmp_path):
    workspace = _workspace(tmp_path)
    gate = UnifiedPolicyGate(workspace)
    request = PolicyGateRequest(
        action="browser_use",
        scope="session",
        session_id="session-2",
        resource="workspace/browser-task.json",
        metadata={"purpose": "regression-test", "secret": "not logged"},
    )
    payload_hash = gate.payload_hash_for(request)
    certificate = ProofOfConsensus.create_consensus_certificate(payload_hash, ["ceo", "cto", "dev"])

    decision = gate.evaluate(request.model_copy(update={"consensus_certificate": certificate}))

    assert decision.allowed is True
    assert decision.payload_hash == payload_hash
    assert decision.reason == "proof of consensus accepted"

    logs = AuditLedger(workspace).get_logs("policy_gate_decision")
    assert logs[-1]["payload"]["allowed"] is True
    assert logs[-1]["payload"]["metadata_keys"] == ["purpose", "secret"]
    assert "not logged" not in str(logs[-1]["payload"])


def test_registered_consensus_allows_computer_use_without_inline_certificate(tmp_path):
    workspace = _workspace(tmp_path)
    gate = UnifiedPolicyGate(workspace)
    request = PolicyGateRequest(
        action="computer_use",
        scope="workspace",
        session_id="session-3",
        resource="scripts/verify.cmd",
    )
    payload_hash = gate.payload_hash_for(request)
    certificate = ProofOfConsensus.create_consensus_certificate(payload_hash, ["ceo", "cto", "dev"])
    ProofOfConsensus.register_consensus(workspace, payload_hash, certificate)

    decision = gate.evaluate(request.model_copy(update={"payload_hash": payload_hash}))

    assert decision.allowed is True
    assert decision.required_guard == "proof_of_consensus"


def test_safety_scan_is_audit_only_but_still_scope_guarded(tmp_path):
    workspace = _workspace(tmp_path)
    gate = UnifiedPolicyGate(workspace)

    decision = gate.evaluate(
        PolicyGateRequest(
            action="safety_scan",
            scope="workspace",
            session_id="session-4",
            resource="agent_workspace/core/policy_gate.py",
        )
    )

    assert decision.allowed is True
    assert decision.required_guard == "audit_only"
    assert decision.reason == "audit-only policy accepted"


def test_scope_guard_rejects_workspace_escape_before_consensus(tmp_path):
    workspace = _workspace(tmp_path)
    gate = UnifiedPolicyGate(workspace)
    outside = tmp_path.parent / "outside.txt"

    decision = gate.evaluate(
        PolicyGateRequest(
            action="computer_use",
            scope="workspace",
            session_id="session-5",
            resource=str(outside),
        )
    )

    assert decision.allowed is False
    assert decision.required_guard == "scope_guard"
    assert decision.reason == "resource outside workspace scope"
