import os
import sys
import builtins
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
    with pytest.raises(PermissionError, match="in-process sandbox execution is disabled"):
        SandboxGuard.execute_safe(str(tmp_path), "import socket")

    # 2. Block name references like socket
    with pytest.raises(PermissionError, match="in-process sandbox execution is disabled"):
        SandboxGuard.execute_safe(str(tmp_path), "x = socket")

    # 3. Block attribute accesses
    with pytest.raises(PermissionError, match="in-process sandbox execution is disabled"):
        SandboxGuard.execute_safe(str(tmp_path), "y = obj.connect")

    # 4. Block blocked strings
    with pytest.raises(PermissionError, match="in-process sandbox execution is disabled"):
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


def test_safe_open_relative_path_reads_from_workspace(tmp_path, monkeypatch):
    """Verify relative paths resolve against the sandbox workspace, not process cwd."""
    safe_open = make_safe_open(str(tmp_path))
    inside_file = tmp_path / "inside.txt"
    inside_file.write_text("workspace content", encoding="utf-8")

    cwd = tmp_path / "cwd"
    cwd.mkdir()
    (cwd / "inside.txt").write_text("cwd content", encoding="utf-8")
    monkeypatch.chdir(cwd)

    with safe_open("inside.txt", "r") as f:
        assert f.read() == "workspace content"


def test_safe_open_blocks_pathlike_traversal(tmp_path, monkeypatch):
    """Verify pathlib paths cannot bypass workspace traversal checks."""
    safe_open = make_safe_open(str(tmp_path))
    outside_file = tmp_path.parent / "outside-safe-open.txt"
    outside_file.write_text("outside content", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    with pytest.raises(PermissionError, match="Directory traversal attempt outside workspace boundaries"):
        with safe_open(Path("..") / outside_file.name, "r"):
            pass


def test_safe_open_allows_dotdot_prefix_filename_inside_workspace(tmp_path):
    """Verify traversal checks do not reject legal filenames that merely start with '..'."""
    safe_open = make_safe_open(str(tmp_path))
    tricky_file = tmp_path / "..safe-name.txt"
    tricky_file.write_text("safe content", encoding="utf-8")

    with safe_open("..safe-name.txt", "r") as f:
        assert f.read() == "safe content"


def test_safe_open_rejects_file_descriptors(tmp_path, monkeypatch):
    """Verify raw file descriptors cannot bypass workspace path checks."""
    safe_open = make_safe_open(str(tmp_path))

    def fail_if_called(*args, **kwargs):
        raise AssertionError("safe_open delegated a raw file descriptor to open()")

    monkeypatch.setattr(builtins, "open", fail_if_called)

    with pytest.raises(PermissionError, match="File descriptor access is not allowed"):
        safe_open(0)


def test_safe_open_blocks_symlink_escape(tmp_path):
    """Verify symlinks inside the workspace cannot point reads outside it."""
    safe_open = make_safe_open(str(tmp_path))
    outside_file = tmp_path.parent / "outside-symlink-target.txt"
    outside_file.write_text("outside content", encoding="utf-8")
    link_path = tmp_path / "linked-outside.txt"

    try:
        link_path.symlink_to(outside_file)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"symlink creation unavailable in this environment: {exc}")

    with pytest.raises(PermissionError, match="Directory traversal attempt outside workspace boundaries"):
        with safe_open("linked-outside.txt", "r"):
            pass


def test_file_snapshot_preserves_symlinks_without_dereferencing(tmp_path):
    """Verify snapshots preserve symlink entries instead of copying external targets."""
    outside_file = tmp_path.parent / "outside-snapshot-target.txt"
    outside_file.write_text("outside content", encoding="utf-8")
    link_path = tmp_path / "linked-outside.txt"

    try:
        link_path.symlink_to(outside_file)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"symlink creation unavailable in this environment: {exc}")

    with FileSnapshotTransaction(str(tmp_path)) as transaction:
        snapshot_link = Path(transaction.temp_dir) / "linked-outside.txt"
        assert snapshot_link.is_symlink()
        assert snapshot_link.resolve() == outside_file.resolve()


def test_file_snapshot_preserves_directory_symlinks(tmp_path):
    """Verify snapshots preserve directory symlink entries without walking their targets."""
    outside_dir = tmp_path.parent / "outside-snapshot-dir"
    outside_dir.mkdir()
    (outside_dir / "outside.txt").write_text("outside content", encoding="utf-8")
    link_path = tmp_path / "linked-outside-dir"

    try:
        link_path.symlink_to(outside_dir, target_is_directory=True)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"directory symlink creation unavailable in this environment: {exc}")

    with FileSnapshotTransaction(str(tmp_path)) as transaction:
        snapshot_link = Path(transaction.temp_dir) / "linked-outside-dir"
        assert snapshot_link.is_symlink()
        assert snapshot_link.resolve() == outside_dir.resolve()
        assert list(Path(transaction.temp_dir).iterdir()) == [snapshot_link]


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


def test_file_snapshot_rollback_removes_new_directories(tmp_path):
    """Verify rollback removes directories created during a failed transaction."""
    source_file = tmp_path / "source.txt"
    source_file.write_text("source initial", encoding="utf-8")

    try:
        with FileSnapshotTransaction(str(tmp_path)):
            new_file = tmp_path / "newdir" / "nested" / "created.txt"
            new_file.parent.mkdir(parents=True)
            new_file.write_text("created", encoding="utf-8")
            raise RuntimeError("trigger rollback")
    except RuntimeError:
        pass

    assert source_file.read_text(encoding="utf-8") == "source initial"
    assert not (tmp_path / "newdir").exists()


def test_file_snapshot_ignores_generated_directories(tmp_path):
    """Verify rollback skips generated/cache directories instead of snapshotting them."""
    source_file = tmp_path / "source.txt"
    source_file.write_text("source initial", encoding="utf-8")

    generated_file = tmp_path / "dist" / "bundle.js"
    generated_file.parent.mkdir()
    generated_file.write_text("generated initial", encoding="utf-8")

    scratch_file = tmp_path / "scratch" / "run.log"
    scratch_file.parent.mkdir()
    scratch_file.write_text("scratch initial", encoding="utf-8")

    try:
        with FileSnapshotTransaction(str(tmp_path)):
            source_file.write_text("source modified", encoding="utf-8")
            generated_file.write_text("generated modified", encoding="utf-8")
            scratch_file.write_text("scratch modified", encoding="utf-8")
            raise RuntimeError("trigger rollback")
    except RuntimeError:
        pass

    assert source_file.read_text(encoding="utf-8") == "source initial"
    assert generated_file.read_text(encoding="utf-8") == "generated modified"
    assert scratch_file.read_text(encoding="utf-8") == "scratch modified"


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
