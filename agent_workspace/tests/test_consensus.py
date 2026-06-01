import os
import sys
import json
import tempfile
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add project root to sys.path
workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, workspace_dir)

from core.discussion_room import ProofOfConsensus
from core.skill_loader import DynamicSkillSynthesizer


@pytest.fixture
def temp_workspace():
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create standard .agent folders
        agent_dir = Path(temp_dir) / ".agent"
        agent_dir.mkdir(parents=True, exist_ok=True)
        (agent_dir / "memory").mkdir(parents=True, exist_ok=True)
        (Path(temp_dir) / "skills").mkdir(parents=True, exist_ok=True)
        yield temp_dir


def test_poc_member_signatures_and_master_signing(temp_workspace):
    payload = "def my_skill():\n    return 'hello'"
    import hashlib
    payload_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    
    # 1. Generate member signatures
    sig_ceo = ProofOfConsensus.generate_member_signature("ceo", payload_hash)
    sig_cto = ProofOfConsensus.generate_member_signature("cto", payload_hash)
    
    assert len(sig_ceo) == 64
    assert len(sig_cto) == 64
    assert sig_ceo != sig_cto
    
    # 2. Majority constraint: less than majority (e.g. only 2 approvals) should fail master certificate creation
    with pytest.raises(ValueError, match="Consensus failed: only got 2/3 approvals"):
        ProofOfConsensus.create_consensus_certificate(payload_hash, ["ceo", "cto"])
        
    # 3. Successful consensus certificate with a majority (3 approvals)
    cert = ProofOfConsensus.create_consensus_certificate(payload_hash, ["ceo", "cto", "dev"])
    assert cert["payload_hash"] == payload_hash
    assert sorted(cert["approvals"]) == ["ceo", "cto", "dev"]
    assert "signatures" in cert
    assert "consensus_signature" in cert
    
    # 4. Cryptographic validation of the consensus certificate
    assert ProofOfConsensus.verify_consensus_certificate(cert) is True
    
    # Modify a signature (tampering check)
    bad_cert = cert.copy()
    bad_cert["signatures"] = cert["signatures"].copy()
    bad_cert["signatures"]["dev"] = "tampered-signature-hash"
    assert ProofOfConsensus.verify_consensus_certificate(bad_cert) is False


def test_synthesis_rejected_without_consensus(temp_workspace):
    synthesizer = DynamicSkillSynthesizer(temp_workspace)
    mock_engine = MagicMock()
    
    valid_code = """
from pydantic import BaseModel

class SampleArgs(BaseModel):
    task: str

def sample_tool(args: SampleArgs) -> str:
    return "done"
"""
    # Attempting to synthesize dynamic skill should raise PermissionError due to failed consensus signature verification
    with pytest.raises(PermissionError, match="Security violation: dynamic script execution rejected. Swarm signature verification failed."):
        synthesizer.synthesize_and_register_skill(mock_engine, "sample_tool", valid_code)


def test_synthesis_accepted_with_consensus_registered(temp_workspace):
    synthesizer = DynamicSkillSynthesizer(temp_workspace)
    mock_engine = MagicMock()
    
    valid_code = """
from pydantic import BaseModel

class ValidSampleArgs(BaseModel):
    task: str

def valid_sample_tool(args: ValidSampleArgs) -> str:
    return "done"
"""
    import hashlib
    payload_hash = hashlib.sha256(valid_code.encode("utf-8")).hexdigest()
    
    # Create consensus certificate and register it
    cert = ProofOfConsensus.create_consensus_certificate(payload_hash, ["ceo", "cto", "dev"])
    ProofOfConsensus.register_consensus(temp_workspace, payload_hash, cert)
    
    # Assert that is_consensus_approved evaluates to True
    assert ProofOfConsensus.is_consensus_approved(temp_workspace, payload_hash) is True
    
    # Attempt synthesis (should pass the consensus hook check and reach contract checks)
    with patch("sys.path", [temp_workspace] + sys.path):
        mock_module = MagicMock()
        mock_module.valid_sample_tool = lambda args: "done"
        
        with patch("importlib.import_module") as mock_import_module:
            mock_import_module.return_value = mock_module
            success = synthesizer.synthesize_and_register_skill(mock_engine, "valid_sample_tool", valid_code)
            assert success is True
