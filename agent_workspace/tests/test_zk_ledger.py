import os
import sys
import json
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure agent_workspace is in sys.path
workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)

from core.audit_ledger import AuditLedger
from api import app

@pytest.fixture(autouse=True)
def setup_api_workspace():
    import api
    orig = api.workspace
    api.workspace = workspace_dir
    yield
    api.workspace = orig


@pytest.fixture(autouse=True)
def clean_ledger():
    ledger = AuditLedger(workspace_dir)
    ledger.reset_ledger()
    yield
    ledger.reset_ledger()


def test_merkle_proof_generation_and_verification():
    ledger = AuditLedger(workspace_dir)
    
    # 1. Record events
    id1 = ledger.record_event("TASK_START", {"task": "A"})
    id2 = ledger.record_event("TASK_EXECUTE", {"task": "A", "node": "node-1"})
    id3 = ledger.record_event("TASK_COMPLETE", {"task": "A", "result": "done"})
    
    # Get chain status
    status = ledger.verify_chain_integrity()
    assert status["valid"] is True
    root_hash = status["merkle_root"]
    
    # 2. Generate and verify proof for id1
    proof_data1 = ledger.generate_merkle_proof(id1)
    assert proof_data1 is not None
    assert proof_data1["root_hash"] == root_hash
    
    valid1 = AuditLedger.verify_merkle_proof(
        proof_data1["event_hash"], proof_data1["proof"], root_hash
    )
    assert valid1 is True
    
    # 3. Generate and verify proof for id3
    proof_data3 = ledger.generate_merkle_proof(id3)
    assert proof_data3 is not None
    assert proof_data3["root_hash"] == root_hash
    
    valid3 = AuditLedger.verify_merkle_proof(
        proof_data3["event_hash"], proof_data3["proof"], root_hash
    )
    assert valid3 is True
    
    # 4. Verify with tampered root or event hash
    invalid_root = AuditLedger.verify_merkle_proof(
        proof_data1["event_hash"], proof_data1["proof"], "0" * 64
    )
    assert invalid_root is False

    invalid_hash = AuditLedger.verify_merkle_proof(
        "0" * 64, proof_data1["proof"], root_hash
    )
    assert invalid_hash is False


def test_zk_proof_generation_and_verification():
    ledger = AuditLedger(workspace_dir)
    
    payload = {"task": "B", "secret_key": "private_key_123", "sensitive_param": 999}
    event_id = ledger.record_event("SECURE_TASK", payload)
    
    # Generate ZK proof
    zk_proof = ledger.generate_zk_proof(event_id)
    assert zk_proof is not None
    
    # Verify raw payload is not exposed directly in proof
    assert payload["secret_key"] not in json.dumps(zk_proof)
    
    # Verify ZK proof
    is_valid = AuditLedger.verify_zk_proof(
        zk_proof["event_type"],
        zk_proof["timestamp"],
        zk_proof["previous_hash"],
        zk_proof["current_hash"],
        zk_proof
    )
    assert is_valid is True
    
    # Verify that changing parameters fails verification
    is_valid_tampered = AuditLedger.verify_zk_proof(
        "TAMPERED_TYPE",
        zk_proof["timestamp"],
        zk_proof["previous_hash"],
        zk_proof["current_hash"],
        zk_proof
    )
    assert is_valid_tampered is False


def test_http_proof_endpoints():
    client = TestClient(app)
    ledger = AuditLedger(workspace_dir)
    
    id1 = ledger.record_event("API_CALL", {"endpoint": "/v1/chat"})
    
    status = ledger.verify_chain_integrity()
    root_hash = status["merkle_root"]
    
    # 1. GET proof endpoint
    response = client.get(f"/v1/audit/proof/{id1}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["event_id"] == id1
    assert "merkle_proof" in data
    assert "zk_proof" in data
    assert data["zk_verification_key"] == "zk-audit-v1-key"
    
    # Test GET for non-existent event
    response_404 = client.get("/v1/audit/proof/99999")
    assert response_404.status_code == 404
    
    # 2. POST verify endpoint
    verify_payload = {
        "event_hash": data["event_hash"],
        "proof": data["merkle_proof"],
        "root_hash": root_hash
    }
    
    response_verify = client.post("/v1/audit/verify-proof", json=verify_payload)
    assert response_verify.status_code == 200
    verify_data = response_verify.json()
    assert verify_data["status"] == "success"
    assert verify_data["valid"] is True

    # Test POST with invalid root hash
    verify_payload_invalid = verify_payload.copy()
    verify_payload_invalid["root_hash"] = "0" * 64
    response_verify_invalid = client.post("/v1/audit/verify-proof", json=verify_payload_invalid)
    assert response_verify_invalid.status_code == 200
    assert response_verify_invalid.json()["valid"] is False
