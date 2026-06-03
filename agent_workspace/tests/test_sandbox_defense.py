import os
import sys
import pytest
import shutil
import tempfile
import hashlib
from pathlib import Path
from unittest.mock import MagicMock

# Add project root to sys.path
workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)

from core.sandbox import SandboxGuard, FileSnapshotTransaction, make_safe_open
from core.discussion_room import ProofOfConsensus, SwarmIDS

@pytest.fixture(autouse=True)
def setup_and_teardown():
    # Reset SwarmIDS and ProofOfConsensus keys before and after each test
    SwarmIDS.reset()
    ProofOfConsensus.reset_keys()
    yield
    SwarmIDS.reset()
    ProofOfConsensus.reset_keys()

def test_ast_sandbox_blockades(tmp_path, monkeypatch):
    """Verify that SandboxGuard AST checks block imports, unsafe names, attributes, and strings."""
    # Mock ProofOfConsensus.is_consensus_approved to return True
    monkeypatch.setattr(ProofOfConsensus, "is_consensus_approved", lambda ws, h: True)

    # 1. Block Import
    with pytest.raises(PermissionError, match="Import of blocked module"):
        SandboxGuard.execute_safe(str(tmp_path), "import socket")

    # 2. Block name references like socket
    with pytest.raises(PermissionError, match="Reference to blocked name"):
        SandboxGuard.execute_safe(str(tmp_path), "x = socket")

    # 3. Block attribute accesses
    with pytest.raises(PermissionError, match="Access to blocked attribute"):
        SandboxGuard.execute_safe(str(tmp_path), "y = obj.connect")

    # 4. Block blocked strings
    with pytest.raises(PermissionError, match="Blocked string literal containing"):
        SandboxGuard.execute_safe(str(tmp_path), "z = '__globals__'")

def test_safe_open_traversal(tmp_path):
    """Verify make_safe_open allows workspace reads but blocks traversal outside."""
    safe_open = make_safe_open(str(tmp_path))
    
    # Create a file inside workspace
    inside_file = tmp_path / "inside.txt"
    inside_file.write_text("inside content", encoding="utf-8")
    
    # Try opening it - should succeed
    with safe_open(str(inside_file), "r") as f:
        assert f.read() == "inside content"

    # Try opening file outside workspace using relative path
    with pytest.raises(PermissionError, match="Directory traversal attempt outside workspace boundaries"):
        with safe_open("../outside.txt", "r"):
            pass

    # Try opening file outside workspace using absolute path
    with pytest.raises(PermissionError, match="Directory traversal attempt outside workspace boundaries"):
        with safe_open("C:/Windows/System32/drivers/etc/hosts" if os.name == 'nt' else "/etc/passwd", "r"):
            pass

def test_file_snapshot_rollback(tmp_path):
    """Verify FileSnapshotTransaction rolls back workspace modifications on error."""
    # Write initial files
    f1 = tmp_path / "file1.txt"
    f1.write_text("initial 1", encoding="utf-8")

    f2 = tmp_path / "subdir" / "file2.txt"
    os.makedirs(f2.parent, exist_ok=True)
    f2.write_text("initial 2", encoding="utf-8")

    # Run transaction that raises error
    try:
        with FileSnapshotTransaction(str(tmp_path)):
            # Modify file1
            f1.write_text("modified 1", encoding="utf-8")
            # Add file3
            f3 = tmp_path / "file3.txt"
            f3.write_text("created 3", encoding="utf-8")
            raise ValueError("Simulated runtime error")
    except ValueError:
        pass

    # Assert workspace is rolled back
    assert f1.read_text(encoding="utf-8") == "initial 1"
    assert f2.read_text(encoding="utf-8") == "initial 2"
    assert not (tmp_path / "file3.txt").exists()

def test_swarm_ids_quarantine_and_rotation():
    """Verify SwarmIDS quarantines nodes and rotates session keys after 3 failures."""
    initial_dev_key = ProofOfConsensus.SECRET_KEYS["dev"]
    initial_consensus_key = ProofOfConsensus.CONSENSUS_KEY

    # Record 2 failures - should not rotate keys yet
    SwarmIDS.record_failure("dev")
    SwarmIDS.record_failure("dev")
    assert not SwarmIDS.is_quarantined("dev")
    assert ProofOfConsensus.SECRET_KEYS["dev"] == initial_dev_key

    # Record 3rd failure - should quarantine and rotate keys
    SwarmIDS.record_failure("dev")
    assert SwarmIDS.is_quarantined("dev")
    assert ProofOfConsensus.SECRET_KEYS["dev"] != initial_dev_key
    assert ProofOfConsensus.CONSENSUS_KEY != initial_consensus_key

def test_quarantined_node_consensus_exclusion():
    """Verify that quarantined nodes are excluded from consensus approval and certificates."""
    payload_hash = hashlib.sha256(b"dynamic-code").hexdigest()
    
    # 1. Normal certificate generation works
    cert = ProofOfConsensus.create_consensus_certificate(payload_hash, ["ceo", "cto", "dev"])
    assert cert["approvals"] == ["ceo", "cto", "dev"]
    assert ProofOfConsensus.verify_consensus_certificate(cert) is True

    # 2. Quarantine "dev" after 3 failures
    SwarmIDS.record_failure("dev")
    SwarmIDS.record_failure("dev")
    SwarmIDS.record_failure("dev")
    assert SwarmIDS.is_quarantined("dev")

    # 3. Generating certificate with dev included fails consensus (since approvals is now 2/5 instead of 3/5 majority)
    with pytest.raises(ValueError, match="Consensus failed"):
        ProofOfConsensus.create_consensus_certificate(payload_hash, ["ceo", "cto", "dev"])

    # 4. Creating certificate with enough non-quarantined members (majority 3/5: ceo, cto, qa) works
    cert_no_dev = ProofOfConsensus.create_consensus_certificate(payload_hash, ["ceo", "cto", "qa"])
    assert "dev" not in cert_no_dev["approvals"]
    assert ProofOfConsensus.verify_consensus_certificate(cert_no_dev) is True
