import os
import sys
import json
import pytest
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocketDisconnect

# Add project root to sys.path
workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)

from api import app, SwarmP2PCrypto
from core.discussion_room import ProofOfConsensus
from conftest import auth_headers


def test_ecdh_aes_gcm_math():
    """Assert ECDH key negotiation results in identical keys and handles AES-GCM-256 encrypt/decrypt correctly."""
    alice = SwarmP2PCrypto()
    bob = SwarmP2PCrypto()
    
    # Exchange public key bytes
    alice_pub = alice.get_public_bytes()
    bob_pub = bob.get_public_bytes()
    
    # Compute shared symmetric keys
    alice_key = alice.compute_shared_key(bob_pub)
    bob_key = bob.compute_shared_key(alice_pub)
    
    assert alice_key == bob_key
    assert len(alice_key) == 32
    
    # Encrypt/Decrypt validation
    secret_text = "Highly confidential swarm discussion data"
    enc = SwarmP2PCrypto.encrypt_message(alice_key, secret_text)
    
    assert enc["encrypted"] == "true"
    assert "ciphertext" in enc
    assert "nonce" in enc
    
    decrypted = SwarmP2PCrypto.decrypt_message(bob_key, enc)
    assert decrypted == secret_text


def test_handshake_rejection_rogue_clients():
    """Assert that connections failing signature checks or missing parameters are rejected."""
    client = TestClient(app, headers=auth_headers())
    session_id = "test-encryption-session"
    
    # 1. Missing query params
    with pytest.raises(Exception):  # TestClient raises WebSocketDisconnect or Starlette error
        with client.websocket_connect(f"/v1/collaboration/{session_id}") as ws:
            ws.receive_json()
            
    # 2. Invalid role or signature
    url_invalid = f"/v1/collaboration/{session_id}?role=ceo&payload_hash=hash123&signature=badsignature"
    with pytest.raises(Exception):
        with client.websocket_connect(url_invalid) as ws:
            ws.receive_json()


def test_successful_secure_handshake_and_exchange():
    """Verify that a node with valid credentials successfully performs ECDH, connects, and sends encrypted frames."""
    import api
    # Register valid consensus hash
    payload_hash = "p2p-test-encryption-payload-hash"
    cert = ProofOfConsensus.create_consensus_certificate(payload_hash, ["ceo", "cto", "dev"])
    ProofOfConsensus.register_consensus(api.workspace, payload_hash, cert)
    
    # Generate signature for CEO role
    sig_ceo = ProofOfConsensus.generate_member_signature("ceo", payload_hash)
    
    client = TestClient(app, headers=auth_headers())
    session_id = "test-encryption-session"
    url = f"/v1/collaboration/{session_id}?role=ceo&payload_hash={payload_hash}&signature={sig_ceo}"
    
    with client.websocket_connect(url) as ws:
        # 1. Receive server hello
        server_hello = ws.receive_json()
        assert server_hello["handshake"] == "server_hello"
        assert "public_key" in server_hello
        
        # 2. Send client hello
        client_crypto = SwarmP2PCrypto()
        ws.send_json({
            "handshake": "client_hello",
            "public_key": client_crypto.get_public_bytes()
        })
        
        # 3. Compute shared session key
        session_key = client_crypto.compute_shared_key(server_hello["public_key"])
        
        # 4. Subscribe over encrypted channel
        sub_action = {"action": "subscribe", "channel": "logs"}
        enc_msg = SwarmP2PCrypto.encrypt_message(session_key, json.dumps(sub_action))
        ws.send_json(enc_msg)
        
        # 5. Read response
        resp_enc = ws.receive_json()
        resp_str = SwarmP2PCrypto.decrypt_message(session_key, resp_enc)
        resp = json.loads(resp_str)
        
        assert resp["status"] == "subscribed"
        assert resp["channel"] == "logs"
