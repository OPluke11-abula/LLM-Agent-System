import os
import sys
import tempfile
import sqlite3
import hashlib
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

# Add project root to sys.path
workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)

from core.sandbox import SandboxGuard
from core.discussion_room import ProofOfConsensus
from core.audit_ledger import AuditLedger
from api import app

@pytest.fixture
def temp_workspace():
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create standard .agent folders
        agent_dir = Path(temp_dir) / ".agent"
        agent_dir.mkdir(parents=True, exist_ok=True)
        (agent_dir / "memory").mkdir(parents=True, exist_ok=True)
        yield temp_dir

@pytest.fixture
def api_client():
    return TestClient(app)

@pytest.fixture
def mock_docker_sys_module():
    # Save original docker module if it exists
    orig_docker = sys.modules.get("docker")
    yield
    # Restore original docker module
    if orig_docker is None:
        sys.modules.pop("docker", None)
    else:
        sys.modules["docker"] = orig_docker

def test_audit_ledger_chaining_and_tampering(temp_workspace):
    # Initialize ledger in temp workspace
    ledger = AuditLedger(temp_workspace)
    
    # 1. Record events
    id1 = ledger.record_event("system_call", {"cmd": "echo 1"})
    id2 = ledger.record_event("websocket_packet", {"msg": "hello"})
    id3 = ledger.record_event("consensus_vote", {"vote": "approve"})
    
    # Ensure they are incrementing
    assert id1 < id2 < id3
    
    # Verify chain integrity originally is valid
    res = ledger.verify_chain_integrity()
    assert res["valid"] is True
    assert res["tampered_id"] is None
    
    # 2. Query logs
    logs = ledger.get_logs()
    assert len(logs) == 3
    assert logs[0]["event_type"] == "system_call"
    assert logs[1]["event_type"] == "websocket_packet"
    assert logs[2]["event_type"] == "consensus_vote"
    
    # Verify previous_hash pointing
    assert logs[0]["previous_hash"] == "0" * 64
    assert logs[1]["previous_hash"] == logs[0]["current_hash"]
    assert logs[2]["previous_hash"] == logs[1]["current_hash"]
    
    # 3. Simulate tampering/corruption of a row payload
    db_path = Path(temp_workspace) / "memory" / "audit_ledger.db"
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("UPDATE audit_ledger SET payload = ? WHERE id = ?", (json.dumps({"cmd": "tampered"}), id2))
        conn.commit()
    finally:
        conn.close()
        
    # Re-verify integrity - should fail and report id2 as the tampered record
    res_tampered = ledger.verify_chain_integrity()
    assert res_tampered["valid"] is False
    assert res_tampered["tampered_id"] == id2
    assert "mismatch" in res_tampered["error"]

def test_sandbox_docker_fallback_to_ast(temp_workspace, mock_docker_sys_module):
    # Mock docker module
    mock_docker = MagicMock()
    mock_docker.from_env.side_effect = Exception("No Docker Daemon")
    sys.modules["docker"] = mock_docker

    code = "result = 100 + 200"
    payload_hash = hashlib.sha256(code.encode("utf-8")).hexdigest()
    
    # Register consensus
    cert = ProofOfConsensus.create_consensus_certificate(payload_hash, ["ceo", "cto", "dev"])
    ProofOfConsensus.register_consensus(temp_workspace, payload_hash, cert)
    
    with patch("subprocess.run") as mock_run:
        # Force exceptions on CLI to ensure fallback
        mock_run.side_effect = Exception("No Docker CLI")
        
        with pytest.raises(RuntimeError, match="Docker sandbox unavailable"):
            SandboxGuard.execute_safe(temp_workspace, code, sandbox_type="docker")

def test_sandbox_docker_success_mock(temp_workspace, mock_docker_sys_module):
    code = "print('Hello Docker')"
    payload_hash = hashlib.sha256(code.encode("utf-8")).hexdigest()
    
    # Register consensus
    cert = ProofOfConsensus.create_consensus_certificate(payload_hash, ["ceo", "cto", "dev"])
    ProofOfConsensus.register_consensus(temp_workspace, payload_hash, cert)
    
    # Mock Docker SDK success
    mock_container = MagicMock()
    mock_container.wait.return_value = {"StatusCode": 0}
    mock_container.logs.side_effect = lambda stdout, stderr: b"Hello Docker" if stdout else b""
    
    mock_client = MagicMock()
    mock_client.containers.run.return_value = mock_container
    
    mock_docker = MagicMock()
    mock_docker.from_env.return_value = mock_client
    sys.modules["docker"] = mock_docker
    
    res = SandboxGuard.execute_safe(temp_workspace, code, sandbox_type="docker")
    assert res["exit_code"] == 0
    assert "Hello Docker" in res["stdout"]
    assert res["status"] == "completed"
    
    # Verify the SDK container execution was configured properly
    mock_client.containers.run.assert_called_once()
    kwargs = mock_client.containers.run.call_args[1]
    assert kwargs["image"] == "python:3.11-slim"
    assert kwargs["mem_limit"] == "128m"
    assert kwargs["nano_cpus"] == 500_000_000
    assert kwargs["pids_limit"] == 64
    assert kwargs["network_mode"] == "none"
    assert kwargs["read_only"] is True
    assert kwargs["cap_drop"] == ["ALL"]
    assert kwargs["security_opt"] == ["no-new-privileges:true"]
    assert kwargs["tmpfs"] == {"/tmp": "rw,noexec,nosuid,size=16m"}
    assert kwargs["user"] == "65532:65532"
    assert kwargs["detach"] is True

def test_audit_endpoints(api_client, temp_workspace):
    # Use patch to route api's workspace variable to our temp_workspace
    with patch("api.workspace", temp_workspace):
        # 1. Initially verification should be valid (empty db is valid)
        resp = api_client.get("/v1/audit/verify")
        assert resp.status_code == 200
        assert resp.json()["status"] == "success"
        assert resp.json()["valid"] is True
        
        # 2. Try querying logs - should be empty
        resp_logs = api_client.get("/v1/audit/logs")
        assert resp_logs.status_code == 200
        assert resp_logs.json()["status"] == "success"
        assert len(resp_logs.json()["logs"]) == 0
        
        # 3. Register consensus on some code
        code = "val = 42"
        payload_hash = hashlib.sha256(code.encode("utf-8")).hexdigest()
        cert = ProofOfConsensus.create_consensus_certificate(payload_hash, ["ceo", "cto", "dev"])
        ProofOfConsensus.register_consensus(temp_workspace, payload_hash, cert)
        
        # 4. Run POST execute endpoint
        exec_payload = {
            "code_content": code,
            "sandbox_type": "ast"
        }
        resp_exec = api_client.post("/v1/sandbox/execute", json=exec_payload)
        assert resp_exec.status_code == 200
        assert resp_exec.json()["status"] == "success"
        assert resp_exec.json()["result"]["val"] == 42
        
        # 5. Query logs again - should contain consensus_vote and system_call events
        resp_logs2 = api_client.get("/v1/audit/logs")
        assert resp_logs2.status_code == 200
        logs = resp_logs2.json()["logs"]
        assert len(logs) >= 2
        event_types = [l["event_type"] for l in logs]
        assert "consensus_vote" in event_types
        assert "system_call" in event_types
        
        # Query filtered
        resp_filtered = api_client.get("/v1/audit/logs?event_type=consensus_vote")
        assert resp_filtered.status_code == 200
        for log in resp_filtered.json()["logs"]:
            assert log["event_type"] == "consensus_vote"
            
        # 6. Test unauthorized execute (without consensus)
        unauth_code = "val = 999"
        unauth_payload = {
            "code_content": unauth_code,
            "sandbox_type": "ast"
        }
        resp_unauth = api_client.post("/v1/sandbox/execute", json=unauth_payload)
        assert resp_unauth.status_code == 403
