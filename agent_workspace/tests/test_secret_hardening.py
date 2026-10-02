import pytest

from core.audit_ledger import AuditLedger
from core.discussion_room import ProofOfConsensus


def test_consensus_requires_configured_secret(monkeypatch):
    monkeypatch.delenv("LAS_TEST_MODE", raising=False)
    for role in ("ceo", "cto", "dev", "qa", "cfo"):
        monkeypatch.delenv(f"LAS_POC_SECRET_{role.upper()}", raising=False)
    ProofOfConsensus.SECRET_KEYS = {role: None for role in ("ceo", "cto", "dev", "qa", "cfo")}
    ProofOfConsensus.CONSENSUS_KEY = None

    with pytest.raises(RuntimeError, match="LAS_POC_SECRET_CEO"):
        ProofOfConsensus.generate_member_signature("ceo", "payload")


def test_consensus_test_mode_uses_nonproduction_mock_secret(monkeypatch):
    monkeypatch.setenv("LAS_TEST_MODE", "1")
    ProofOfConsensus.SECRET_KEYS = {role: None for role in ("ceo", "cto", "dev", "qa", "cfo")}
    ProofOfConsensus.CONSENSUS_KEY = None

    signature = ProofOfConsensus.generate_member_signature("ceo", "payload")
    assert signature


def test_audit_proof_requires_configured_secret(monkeypatch):
    monkeypatch.delenv("LAS_TEST_MODE", raising=False)
    monkeypatch.delenv("LAS_ZK_SECRET_KEY", raising=False)

    with pytest.raises(RuntimeError, match="LAS_ZK_SECRET_KEY"):
        AuditLedger.verify_zk_proof("event", "time", "previous", "current", {
            "payload_commitment": "commitment",
            "proof": "proof",
        })
