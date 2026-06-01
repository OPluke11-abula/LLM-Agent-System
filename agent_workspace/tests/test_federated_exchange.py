import os
import sys
import tempfile
import pytest
import json
from pathlib import Path
from fastapi.testclient import TestClient

# Add project root to sys.path
workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)

from api import app, TRUSTED_TENANTS_KEYS
from core.federated_sync import FederatedKnowledgeExchange


@pytest.fixture
def temp_workspace():
    """Scaffolds a mock temp workspace for federated sync."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        agent_dir = temp_path / ".agent" / "knowledge_base"
        agent_dir.mkdir(parents=True, exist_ok=True)
        
        # Write initial scaffold for lessons_learned.md
        lessons_content = (
            "# 🎓 FindAi Studio LAS Self-Learning Experience & Lessons Learned Registry\n\n"
            "This database catalogs engineering resolutions, compile-time errors, and dynamic swarms refactoring choices.\n\n"
            "---\n\n"
            "## ⚡ 1. Active Resolution Directory (Lessons Database)\n"
        )
        (agent_dir / "lessons_learned.md").write_text(lessons_content, encoding="utf-8")
        yield temp_dir


def test_federated_asymmetric_cryptography(temp_workspace):
    """Assert key generation, signature verification, and hybrid encryption function securely."""
    exchange = FederatedKnowledgeExchange(temp_workspace)
    
    # 1. Key pair generation
    priv_pem, pub_pem = exchange.generate_key_pair()
    assert "BEGIN PRIVATE KEY" in priv_pem
    assert "BEGIN PUBLIC KEY" in pub_pem
    
    exchange.save_local_keys(priv_pem, pub_pem)
    loaded_priv, loaded_pub = exchange.load_local_keys()
    assert loaded_priv == priv_pem
    assert loaded_pub == pub_pem
    
    # 2. Signing and verification
    payload = {"lesson_id": "L-20260601-ABC", "mistake": "Connection timeout"}
    sig = exchange.sign_payload(payload, priv_pem)
    assert isinstance(sig, str)
    assert len(sig) > 10
    
    # Verify valid
    is_valid = exchange.verify_signature(payload, sig, pub_pem)
    assert is_valid is True
    
    # Verify invalid if payload modified (tampering check)
    tampered_payload = {"lesson_id": "L-20260601-ABC", "mistake": "Connection timeout!", "extra": "tamper"}
    is_valid_tampered = exchange.verify_signature(tampered_payload, sig, pub_pem)
    assert is_valid_tampered is False
    
    # Verify invalid with wrong key
    priv_pem_alt, pub_pem_alt = exchange.generate_key_pair()
    is_valid_wrong_key = exchange.verify_signature(payload, sig, pub_pem_alt)
    assert is_valid_wrong_key is False
    
    # 3. Hybrid Encryption and Decryption
    encrypted = exchange.encrypt_payload(payload, pub_pem)
    assert "encrypted_key" in encrypted
    assert "ciphertext" in encrypted
    
    decrypted = exchange.decrypt_payload(encrypted, priv_pem)
    assert decrypted["lesson_id"] == "L-20260601-ABC"
    assert decrypted["mistake"] == "Connection timeout"


def test_secure_websocket_handlers(temp_workspace):
    """Test push and pull WebSocket handlers securely pushing/pulling signed lessons."""
    client = TestClient(app)
    
    # Initialize exchange on both client and server side
    server_exchange = FederatedKnowledgeExchange(temp_workspace)
    server_priv, server_pub = server_exchange.generate_key_pair()
    server_exchange.save_local_keys(server_priv, server_pub)
    
    client_exchange = FederatedKnowledgeExchange(temp_workspace)
    client_priv, client_pub = client_exchange.generate_key_pair()
    
    # Register client public key in trusted tenants
    client_id = "test-client-tenant"
    TRUSTED_TENANTS_KEYS[client_id] = client_pub
    
    # Mock api workspace location to use temp_workspace
    import api
    original_workspace = api.workspace
    api.workspace = temp_workspace
    
    try:
        with client.websocket_connect("/v1/federated/sync") as ws:
            # 1. Test pushing a valid signed and encrypted lesson learned
            lesson = {
                "lesson_id": "L-20260601-TEST123",
                "mistake": "Rate limit exceeded",
                "root_cause": "Called endpoint too fast",
                "resolution_code": "time.sleep(1)",
                "best_practice": "Throttle queries"
            }
            
            encrypted_payload = client_exchange.sign_and_encrypt_lesson(
                lesson, server_pub, client_priv, client_id
            )
            
            ws.send_json({
                "type": "push_lesson",
                "payload": encrypted_payload
            })
            
            resp = ws.receive_json()
            assert resp["status"] == "success"
            assert "Lesson successfully merged" in resp["message"]
            
            # Assert file now contains the merged lesson
            content = Path(temp_workspace).joinpath(".agent", "knowledge_base", "lessons_learned.md").read_text(encoding="utf-8")
            assert "Lesson ID: L-20260601-TEST123" in content
            
            # 2. Test pulling lessons securely
            ws.send_json({
                "type": "pull_lessons",
                "receiver_public_key": client_pub
            })
            
            resp_pull = ws.receive_json()
            assert resp_pull["status"] == "success"
            assert resp_pull["type"] == "pull_response"
            assert len(resp_pull["lessons"]) > 0
            
            # Verify and decrypt pulled lesson
            pulled_payload = resp_pull["lessons"][0]
            trusted_keys = {"server-tenant": server_pub}
            decrypted_lesson = client_exchange.decrypt_and_verify_lesson(
                pulled_payload, client_priv, trusted_keys
            )
            
            assert decrypted_lesson["lesson_id"] == "L-20260601-TEST123"
            assert decrypted_lesson["mistake"] == "Rate limit exceeded"
            
            # 3. Test pushing an untrusted tenant payload (should be rejected)
            untrusted_payload = client_exchange.sign_and_encrypt_lesson(
                lesson, server_pub, client_priv, "untrusted-tenant-id"
            )
            ws.send_json({
                "type": "push_lesson",
                "payload": untrusted_payload
            })
            resp_reject = ws.receive_json()
            assert resp_reject["status"] == "error"
            assert "Untrusted or missing sender_id" in resp_reject["message"]
            
    finally:
        api.workspace = original_workspace
        TRUSTED_TENANTS_KEYS.clear()
