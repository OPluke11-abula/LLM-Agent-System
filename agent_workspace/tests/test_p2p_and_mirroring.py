import os
import sys
import json
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch

# Add project root to sys.path
workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)

from core.p2p_storage import P2PFileChunkDistributor
from core.memory import DeltaStateReconciler


@pytest.fixture
def temp_env():
    """Scaffolds temporary environment directories for testing P2P and Mirroring."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        tenant_1 = temp_path / "tenant_1"
        tenant_2 = temp_path / "tenant_2"
        tenant_3 = temp_path / "tenant_3"
        tenant_1.mkdir()
        tenant_2.mkdir()
        tenant_3.mkdir()
        yield {
            "root": temp_path,
            "tenants": [tenant_1, tenant_2, tenant_3]
        }


def test_p2p_chunking_and_reassembly(temp_env):
    """Verify that file chunk distributor correctly splits, distributes, and reassembles files with integrity checks."""
    tenants = temp_env["tenants"]
    distributor = P2PFileChunkDistributor(tenants)
    
    # 1. Create a dummy file
    src_file = temp_env["root"] / "source.dat"
    content = b"A" * 500 + b"B" * 500 + b"C" * 24  # 1024 bytes
    src_file.write_bytes(content)
    
    # 2. Distribute with chunk size of 300 bytes
    manifest = distributor.distribute_file(src_file, chunk_size_bytes=300, filename_prefix="log_data")
    
    assert manifest["original_size"] == 1024
    assert manifest["chunk_size"] == 300
    
    # 1024 / 300 -> 4 chunks (300, 300, 300, 124)
    assert len(manifest["chunks"]) == 4
    
    # Check that chunks are distributed across the tenant folders
    for chunk in manifest["chunks"]:
        chunk_file = Path(chunk["tenant_dir"]) / chunk["name"]
        assert chunk_file.is_file()
        assert len(chunk_file.read_bytes()) == chunk["size"]
        
    # 3. Reassemble
    out_file = temp_env["root"] / "recovered.dat"
    success = distributor.reassemble_file(manifest, out_file)
    assert success
    assert out_file.read_bytes() == content


def test_p2p_tamper_detection(temp_env):
    """Verify that modification or missing chunks are blocked by integrity checks."""
    tenants = temp_env["tenants"]
    distributor = P2PFileChunkDistributor(tenants)
    
    src_file = temp_env["root"] / "source.dat"
    src_file.write_bytes(b"Top secret project logs data stream")
    manifest = distributor.distribute_file(src_file, chunk_size_bytes=10, filename_prefix="secure")
    
    out_file = temp_env["root"] / "recovered.dat"
    
    # Tamper with chunk content
    first_chunk = manifest["chunks"][0]
    chunk_file_path = Path(first_chunk["tenant_dir"]) / first_chunk["name"]
    original_chunk_bytes = chunk_file_path.read_bytes()
    
    # Write tampered content
    chunk_file_path.write_bytes(b"TAMPERED!!")
    with pytest.raises(ValueError, match="Integrity check failed for chunk"):
        distributor.reassemble_file(manifest, out_file)
        
    # Restore original content but tamper with manifest hash
    chunk_file_path.write_bytes(original_chunk_bytes)
    corrupted_manifest = dict(manifest)
    corrupted_manifest["original_sha256"] = "badhash123"
    with pytest.raises(ValueError, match="Full file integrity check failed"):
        distributor.reassemble_file(corrupted_manifest, out_file)
        
    # Delete a chunk file
    os.remove(chunk_file_path)
    with pytest.raises(FileNotFoundError, match="Missing chunk"):
        distributor.reassemble_file(manifest, out_file)


def test_state_vault_mirroring(temp_env):
    """Assert that state reconciler replicates active session states to secondary folders."""
    root = temp_env["root"]
    workspace = root / "workspace"
    workspace.mkdir()
    
    mirror_1 = root / "mirrors" / "m1"
    mirror_2 = root / "mirrors" / "m2"
    mirror_paths = [mirror_1, mirror_2]
    
    reconciler = DeltaStateReconciler(str(workspace), mirror_paths=mirror_paths)
    reconciler.apply_update("setting_a", "active")
    
    # Assert primary file written
    primary_file = reconciler.state_file
    assert primary_file.is_file()
    
    # Assert mirror files written
    m1_file = mirror_1 / "reconciled_state.json"
    m2_file = mirror_2 / "reconciled_state.json"
    assert m1_file.is_file()
    assert m2_file.is_file()
    
    # Verify contents match
    primary_data = json.loads(primary_file.read_text(encoding="utf-8"))
    m1_data = json.loads(m1_file.read_text(encoding="utf-8"))
    m2_data = json.loads(m2_file.read_text(encoding="utf-8"))
    
    assert primary_data["values"]["setting_a"] == "active"
    assert m1_data["values"]["setting_a"] == "active"
    assert m2_data["values"]["setting_a"] == "active"


def test_state_vault_failover_and_auto_healing(temp_env):
    """Assert that reconciler fails over to mirrors and auto-heals when primary is lost, corrupt, or locked."""
    root = temp_env["root"]
    workspace = root / "workspace"
    workspace.mkdir()
    
    mirror_1 = root / "mirrors" / "m1"
    mirror_2 = root / "mirrors" / "m2"
    mirror_paths = [mirror_1, mirror_2]
    
    reconciler = DeltaStateReconciler(str(workspace), mirror_paths=mirror_paths)
    reconciler.apply_update("key_y", 12345)
    
    # 1. Test case: Primary file is missing
    os.remove(reconciler.state_file)
    assert not reconciler.state_file.is_file()
    
    # Load state should trigger failover and auto-heal
    state = reconciler.get_state()
    assert state["key_y"] == 12345
    assert reconciler.state_file.is_file()  # Verified auto-healed!
    
    # 2. Test case: Primary file contains corrupted JSON
    reconciler.state_file.write_text("invalid json structure {{", encoding="utf-8")
    state2 = reconciler.get_state()
    assert state2["key_y"] == 12345
    # Verified healed again
    primary_content = json.loads(reconciler.state_file.read_text(encoding="utf-8"))
    assert primary_content["values"]["key_y"] == 12345
    
    # 3. Test case: Primary file throws forced IO exceptions (PermissionError/OSError)
    # Patch read_text to raise OSError, simulating directory/file locks
    with patch.object(Path, "read_text", side_effect=OSError("Forced device/file lock error")):
        # Should still fall back to reading mirrors (Path.read_text patches will affect all paths, 
        # so we patch conditionally or mock only the reconciler's primary read).
        pass

    # A more precise way is to patch the path read specifically for the primary file
    original_read_text = Path.read_text
    def mock_read_text(self, *args, **kwargs):
        if self.name == "reconciled_state.json" and "vault_mirrors" not in str(self) and "mirrors" not in str(self):
            raise PermissionError("Forced file lock exception on primary")
        return original_read_text(self, *args, **kwargs)
        
    with patch.object(Path, "read_text", mock_read_text):
        state3 = reconciler.get_state()
        # Should successfully load from the mirrors
        assert state3["key_y"] == 12345
