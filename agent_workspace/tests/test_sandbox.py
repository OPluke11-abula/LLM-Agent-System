import os
import sys
import tempfile
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add project root to sys.path
workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)

from core.sandbox import SandboxGuard
from core.discussion_room import ProofOfConsensus

@pytest.fixture
def temp_workspace():
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create standard .agent folders
        agent_dir = Path(temp_dir) / ".agent"
        agent_dir.mkdir(parents=True, exist_ok=True)
        (agent_dir / "memory").mkdir(parents=True, exist_ok=True)
        yield temp_dir

def test_sandbox_guard_rejects_missing_consensus(temp_workspace):
    code = "result = 1 + 1"
    
    # Attempt execution without consensus registered should raise PermissionError
    with pytest.raises(PermissionError, match="Consensus signature verification failed"):
        SandboxGuard.execute_safe(temp_workspace, code)

def test_sandbox_guard_allows_consensus_approved(temp_workspace):
    code = "result = 40 + 2"
    import hashlib
    payload_hash = hashlib.sha256(code.encode("utf-8")).hexdigest()
    
    cert = ProofOfConsensus.create_consensus_certificate(payload_hash, ["ceo", "cto", "dev"])
    ProofOfConsensus.register_consensus(temp_workspace, payload_hash, cert)
    
    locals_out = SandboxGuard.execute_safe(temp_workspace, code)
    assert locals_out["result"] == 42
    assert "__builtins__" not in locals_out

def test_sandbox_guard_ast_blocks_imports(temp_workspace):
    # Try importing blocked module 'os'
    code_import_os = "import os\nresult = os.getcwd()"
    import hashlib
    payload_hash = hashlib.sha256(code_import_os.encode("utf-8")).hexdigest()
    
    cert = ProofOfConsensus.create_consensus_certificate(payload_hash, ["ceo", "cto", "dev"])
    ProofOfConsensus.register_consensus(temp_workspace, payload_hash, cert)
    
    with pytest.raises(PermissionError, match="Import of blocked module 'os' detected"):
        SandboxGuard.execute_safe(temp_workspace, code_import_os)

    # Try importing from blocked module
    code_import_from = "from sys import exit\nresult = 1"
    payload_hash2 = hashlib.sha256(code_import_from.encode("utf-8")).hexdigest()
    cert2 = ProofOfConsensus.create_consensus_certificate(payload_hash2, ["ceo", "cto", "dev"])
    ProofOfConsensus.register_consensus(temp_workspace, payload_hash2, cert2)
    
    with pytest.raises(PermissionError, match="Import from blocked module 'sys' detected"):
        SandboxGuard.execute_safe(temp_workspace, code_import_from)

def test_sandbox_guard_ast_blocks_unsafe_builtins(temp_workspace):
    code_eval = "result = eval('2 * 2')"
    import hashlib
    payload_hash = hashlib.sha256(code_eval.encode("utf-8")).hexdigest()
    
    cert = ProofOfConsensus.create_consensus_certificate(payload_hash, ["ceo", "cto", "dev"])
    ProofOfConsensus.register_consensus(temp_workspace, payload_hash, cert)
    
    with pytest.raises(PermissionError, match="Unsafe call to 'eval' detected"):
        SandboxGuard.execute_safe(temp_workspace, code_eval)
