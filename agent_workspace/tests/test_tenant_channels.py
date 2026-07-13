import os
import sys
import json
import time
import hmac
import hashlib
import base64
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import WebSocketDisconnect

# Add project root to sys.path
workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)

from api import app, API_KEYS, generate_jwt, verify_jwt, SLACK_SIGNING_SECRET, LINE_CHANNEL_SECRET, collab_manager
from core.discussion_room import ProofOfConsensus
from core.audit_ledger import AuditLedger
from api import SwarmP2PCrypto

@pytest.fixture
def anyio_backend():
    return "asyncio"

@pytest.fixture
def api_client():
    return TestClient(app)

@pytest.fixture(autouse=True)
def auth_test_config(monkeypatch):
    monkeypatch.setenv("LAS_JWT_SECRET", "test-only-secret-for-phase-72-auth-claims")
    API_KEYS.clear()
    API_KEYS.update({
        "key-tenant-a": "tenant_a",
        "key-tenant-b": "tenant_b",
        "key-admin": {"tenant_id": "admin_tenant", "role": "admin", "scope": "admin:read admin:write auth:mint"},
    })
    yield
    API_KEYS.clear()

def test_jwt_generation_and_verification():
    """Verify that JWT helper functions generate and decode valid tokens."""
    payload = {"tenant_id": "tenant_test", "exp": time.time() + 10}
    token = generate_jwt(payload)
    assert isinstance(token, str)
    assert len(token.split('.')) == 3

    decoded = verify_jwt(token)
    assert decoded is not None
    assert decoded["tenant_id"] == "tenant_test"

    # Test expired token
    expired_payload = {"tenant_id": "tenant_test", "exp": time.time() - 10}
    expired_token = generate_jwt(expired_payload)
    assert verify_jwt(expired_token) is None

    # Test tampered token
    parts = token.split('.')
    tampered_parts = [parts[0], parts[1], parts[2] + "tamper"]
    tampered_token = ".".join(tampered_parts)
    assert verify_jwt(tampered_token) is None


def test_jwt_secret_can_be_rotated_with_environment(monkeypatch):
    """Verify JWT signatures honor LAS_JWT_SECRET and reject tokens signed with old secrets."""
    payload = {"tenant_id": "tenant_test", "exp": time.time() + 10}

    monkeypatch.setenv("LAS_JWT_SECRET", "first-secret-with-at-least-32-bytes")
    token = generate_jwt(payload)
    assert verify_jwt(token)["tenant_id"] == "tenant_test"

    monkeypatch.setenv("LAS_JWT_SECRET", "second-secret-with-at-least-32-bytes")
    assert verify_jwt(token) is None

    rotated_token = generate_jwt(payload)
    assert rotated_token != token
    assert verify_jwt(rotated_token)["tenant_id"] == "tenant_test"


def test_auth_token_route(api_client):
    """Test the POST /v1/auth/token endpoint."""
    response = api_client.post("/v1/auth/token", json={"tenant_id": "admin_tenant"}, headers={"x-api-key": "key-admin"})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

    # Decode the returned token
    decoded = verify_jwt(data["access_token"])
    assert decoded is not None
    assert decoded["tenant_id"] == "admin_tenant"

def test_auth_token_requires_authenticated_principal(api_client):
    assert api_client.post("/v1/auth/token", json={"tenant_id": "tenant_a"}).status_code == 401
    assert api_client.post("/v1/auth/token", json={"tenant_id": "arbitrary"}, headers={"x-api-key": "key-tenant-a"}).status_code == 403
    response = api_client.post("/v1/auth/token", json={"tenant_id": "admin_tenant"}, headers={"x-api-key": "key-admin"})
    assert response.status_code == 200
    claims = verify_jwt(response.json()["access_token"])
    assert claims["tenant"] == "admin_tenant"
    assert claims["role"] == "admin"
    assert all(name in claims for name in ("iss", "aud", "sub", "iat", "nbf", "exp", "jti"))

def test_jwt_required_claims_and_secret_fail_closed(monkeypatch):
    token = generate_jwt({"tenant": "tenant_a", "role": "tenant"})
    parts = token.split(".")
    payload = json.loads(base64.urlsafe_b64decode(parts[1] + "=="))
    payload["jti"] = 123
    malformed = generate_jwt(payload)
    assert verify_jwt(malformed) is None
    monkeypatch.delenv("LAS_JWT_SECRET", raising=False)
    assert verify_jwt(token) is None

def test_secured_endpoints_unauthorized(api_client):
    """Verify that secured endpoints reject requests with missing or invalid credentials."""
    endpoints = [
        ("GET", "/v1/builder/templates"),
        ("POST", "/v1/builder/agents"),
        ("POST", "/v1/builder/test"),
        ("POST", "/v1/sandbox/execute"),
        ("GET", "/v1/billing/saas/invoice"),
        ("GET", "/v1/audit/logs"),
        ("GET", "/v1/audit/verify"),
    ]
    for method, path in endpoints:
        # Missing auth (enforced)
        response = api_client.request(method, path, headers={"x-enforce-auth": "true"})
        assert response.status_code == 401

        # Invalid token (enforced)
        response = api_client.request(method, path, headers={"Authorization": "Bearer invalidtoken", "x-enforce-auth": "true"})
        assert response.status_code == 401

        # Invalid API key (enforced)
        response = api_client.request(method, path, headers={"x-api-key": "invalidkey", "x-enforce-auth": "true"})
        assert response.status_code == 401

def test_secured_endpoints_authorized(api_client):
    """Verify that secured endpoints accept requests with valid API keys or JWT tokens."""
    token = generate_jwt({"tenant_id": "tenant_a", "exp": time.time() + 60})
    headers_jwt = {"Authorization": f"Bearer {token}"}
    headers_key = {"x-api-key": "key-tenant-a"}

    # Mock dynamic imports and logic where necessary
    with patch("core.discussion_room.ProofOfConsensus.is_consensus_approved", return_value=True):
        # 1. Builder templates (GET)
        res1 = api_client.get("/v1/builder/templates", headers=headers_jwt)
        assert res1.status_code == 200

        res2 = api_client.get("/v1/builder/templates", headers=headers_key)
        assert res2.status_code == 200

def test_multi_tenant_audit_isolation(api_client, tmp_path):
    """Verify Tenant A cannot see Tenant B's audit trails."""
    token_a = generate_jwt({"tenant_id": "tenant_a", "exp": time.time() + 60})
    token_b = generate_jwt({"tenant_id": "tenant_b", "exp": time.time() + 60})

    # Clear/mock ledgers so we have a clean test
    with patch("api.workspace", str(tmp_path)), \
         patch("core.discussion_room.ProofOfConsensus.is_consensus_approved", return_value=True):

        payload = {"code_content": "print('hello')", "sandbox_type": "ast"}
        res = api_client.post("/v1/sandbox/execute", json=payload, headers={"Authorization": f"Bearer {token_a}"})
        assert res.status_code == 403

        ledger = AuditLedger(str(tmp_path))
        ledger.record_event("tenant_a_event", {"value": 1}, tenant_id="tenant_a")
        ledger.record_event("tenant_b_event", {"value": 2}, tenant_id="tenant_b")

        # Query audit logs as Tenant A
        res_a = api_client.get("/v1/audit/logs", headers={"Authorization": f"Bearer {token_a}"})
        assert res_a.status_code == 200
        logs_a = res_a.json()["logs"]
        assert len(logs_a) > 0
        for log in logs_a:
            assert log["tenant_id"] == "tenant_a"

        # Query audit logs as Tenant B
        res_b = api_client.get("/v1/audit/logs", headers={"Authorization": f"Bearer {token_b}"})
        assert res_b.status_code == 200
        logs_b = res_b.json()["logs"]
        assert len(logs_b) > 0
        for log in logs_b:
            assert log["tenant_id"] == "tenant_b"

def test_multi_tenant_billing_isolation(api_client, tmp_path):
    """Verify Tenant A cannot view Tenant B's financial summaries/invoice details."""
    token_a = generate_jwt({"tenant_id": "tenant_a", "exp": time.time() + 60})
    token_b = generate_jwt({"tenant_id": "tenant_b", "exp": time.time() + 60})

    with patch("api.workspace", str(tmp_path)):
        # Record some builder console test costs for Tenant A
        agent_payload = {
            "agent_config": {"name": "test-agent", "model": "gemini-2.5-pro"},
            "test_input": "hello"
        }
        res = api_client.post("/v1/builder/test", json=agent_payload, headers={"Authorization": f"Bearer {token_a}"})
        assert res.status_code == 200

        # Verify Tenant A billing invoice shows transactions
        invoice_a = api_client.get("/v1/billing/saas/invoice", headers={"Authorization": f"Bearer {token_a}"}).json()
        assert invoice_a["total_tokens"] > 0
        assert len(invoice_a["transactions"]) > 0

        # Verify Tenant B billing invoice shows ZERO transactions (isolation!)
        invoice_b = api_client.get("/v1/billing/saas/invoice", headers={"Authorization": f"Bearer {token_b}"}).json()
        assert invoice_b["total_tokens"] == 0
        assert len(invoice_b["transactions"]) == 0

def test_slack_signature_verification(api_client):
    """Verify Slack webhook signature validation and replay protection."""
    # Test valid challenge request
    timestamp = str(int(time.time()))
    body = json.dumps({"type": "url_verification", "challenge": "slack_test_challenge"}).encode('utf-8')
    sig_basestring = f"v0:{timestamp}:".encode('utf-8') + body
    signature = "v0=" + hmac.new(SLACK_SIGNING_SECRET.encode('utf-8'), sig_basestring, hashlib.sha256).hexdigest()

    headers = {
        "x-slack-request-timestamp": timestamp,
        "x-slack-signature": signature,
        "Content-Type": "application/json"
    }
    response = api_client.post("/v1/channels/slack/webhook", content=body, headers=headers)
    assert response.status_code == 200
    assert response.json()["challenge"] == "slack_test_challenge"

    # Test replay attack (old timestamp)
    old_timestamp = str(int(time.time()) - 400)
    sig_basestring_old = f"v0:{old_timestamp}:".encode('utf-8') + body
    sig_old = "v0=" + hmac.new(SLACK_SIGNING_SECRET.encode('utf-8'), sig_basestring_old, hashlib.sha256).hexdigest()
    headers_old = {
        "x-slack-request-timestamp": old_timestamp,
        "x-slack-signature": sig_old,
        "Content-Type": "application/json"
    }
    response_old = api_client.post("/v1/channels/slack/webhook", content=body, headers=headers_old)
    assert response_old.status_code == 403

    # Test invalid signature
    headers_invalid = {
        "x-slack-request-timestamp": timestamp,
        "x-slack-signature": "v0=invalidsig",
        "Content-Type": "application/json"
    }
    response_invalid = api_client.post("/v1/channels/slack/webhook", content=body, headers=headers_invalid)
    assert response_invalid.status_code == 403

def test_line_signature_verification(api_client):
    """Verify LINE webhook signature validation."""
    body = json.dumps({"events": []}).encode('utf-8')
    hash_val = hmac.new(LINE_CHANNEL_SECRET.encode('utf-8'), body, hashlib.sha256).digest()
    signature = base64.b64encode(hash_val).decode('utf-8')

    headers = {
        "x-line-signature": signature,
        "Content-Type": "application/json"
    }
    response = api_client.post("/v1/channels/line/webhook", content=body, headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "accepted"

    # Test invalid signature
    headers_invalid = {
        "x-line-signature": "invalid_sig",
        "Content-Type": "application/json"
    }
    response_invalid = api_client.post("/v1/channels/line/webhook", content=body, headers=headers_invalid)
    assert response_invalid.status_code == 403

def test_websocket_tenant_isolation(api_client):
    """Verify that clients on different tenants connected to the same session do not receive each other's messages."""
    import api
    payload_hash = "ws-isolation-test-hash"
    cert = ProofOfConsensus.create_consensus_certificate(payload_hash, ["ceo", "cto", "dev"])
    ProofOfConsensus.register_consensus(api.workspace, payload_hash, cert)

    sig_ceo = ProofOfConsensus.generate_member_signature("ceo", payload_hash)
    sig_dev = ProofOfConsensus.generate_member_signature("dev", payload_hash)

    session_id = "test-tenant-ws-session"
    token_a = generate_jwt({"tenant_id": "tenant_a", "exp": time.time() + 60})
    token_b = generate_jwt({"tenant_id": "tenant_b", "exp": time.time() + 60})

    url_tenant_a1 = f"/v1/collaboration/{session_id}?role=ceo&payload_hash={payload_hash}&signature={sig_ceo}"
    url_tenant_b = f"/v1/collaboration/{session_id}?role=dev&payload_hash={payload_hash}&signature={sig_dev}"
    url_tenant_a2 = f"/v1/collaboration/{session_id}?role=dev&payload_hash={payload_hash}&signature={sig_dev}"
    url_unauth = f"/v1/collaboration/{session_id}?role=ceo&payload_hash={payload_hash}&signature={sig_ceo}&token=invalidtoken&enforce_auth=true"

    # 1. Unauthenticated socket connection must close with 4001 when client receives a frame
    with api_client.websocket_connect(url_unauth) as ws:
        with pytest.raises(WebSocketDisconnect) as excinfo:
            ws.receive_json()
        assert excinfo.value.code == 4001

    # 2. Establish connections for Tenant A (ceo), Tenant B (dev), and Tenant A (dev)
    with api_client.websocket_connect(url_tenant_a1, headers={"Authorization": f"Bearer {token_a}"}) as ws_a1, \
         api_client.websocket_connect(url_tenant_b, headers={"Authorization": f"Bearer {token_b}"}) as ws_b, \
         api_client.websocket_connect(url_tenant_a2, headers={"Authorization": f"Bearer {token_a}"}) as ws_a2:

        # ECDH Handshake for ws_a1
        hello_a1 = ws_a1.receive_json()
        crypto_a1 = SwarmP2PCrypto()
        ws_a1.send_json({"handshake": "client_hello", "public_key": crypto_a1.get_public_bytes()})
        key_a1 = crypto_a1.compute_shared_key(hello_a1["public_key"])

        # ECDH Handshake for ws_b
        hello_b = ws_b.receive_json()
        crypto_b = SwarmP2PCrypto()
        ws_b.send_json({"handshake": "client_hello", "public_key": crypto_b.get_public_bytes()})
        key_b = crypto_b.compute_shared_key(hello_b["public_key"])

        # ECDH Handshake for ws_a2
        hello_a2 = ws_a2.receive_json()
        crypto_a2 = SwarmP2PCrypto()
        ws_a2.send_json({"handshake": "client_hello", "public_key": crypto_a2.get_public_bytes()})
        key_a2 = crypto_a2.compute_shared_key(hello_a2["public_key"])

        # Subscribe ws_a1 and ws_b and ws_a2 to 'logs' channel
        sub_msg = {"action": "subscribe", "channel": "logs"}
        ws_a1.send_json(SwarmP2PCrypto.encrypt_message(key_a1, json.dumps(sub_msg)))
        ws_a1.receive_json() # consume ack

        ws_b.send_json(SwarmP2PCrypto.encrypt_message(key_b, json.dumps(sub_msg)))
        ws_b.receive_json() # consume ack

        ws_a2.send_json(SwarmP2PCrypto.encrypt_message(key_a2, json.dumps(sub_msg)))
        ws_a2.receive_json() # consume ack

        # ws_a1 publishes to 'logs' channel
        pub_payload = {"msg": "A1 Broadcast"}
        pub_msg = {"action": "publish", "channel": "logs", "payload": pub_payload}
        ws_a1.send_json(SwarmP2PCrypto.encrypt_message(key_a1, json.dumps(pub_msg)))
        ws_a1.receive_json() # consume pub confirm

        # ws_a2 (same tenant) must receive it
        rec_a2_enc = ws_a2.receive_json()
        rec_a2 = json.loads(SwarmP2PCrypto.decrypt_message(key_a2, rec_a2_enc))
        assert rec_a2["payload"]["msg"] == "A1 Broadcast"

        # ws_b (different tenant, same session_id) must NOT receive it
        # We verify that Tenant B can send and receive its own messages without receiving A's message
        pub_msg_b = {"action": "publish", "channel": "logs", "payload": {"msg": "B Broadcast"}}
        ws_b.send_json(SwarmP2PCrypto.encrypt_message(key_b, json.dumps(pub_msg_b)))

        # ws_b expects two incoming messages: pub confirm and B Broadcast
        msg1_enc = ws_b.receive_json()
        msg2_enc = ws_b.receive_json()
        msg1 = json.loads(SwarmP2PCrypto.decrypt_message(key_b, msg1_enc))
        msg2 = json.loads(SwarmP2PCrypto.decrypt_message(key_b, msg2_enc))

        if "status" in msg1:
            resp_confirm = msg1
            broadcast_msg = msg2
        else:
            resp_confirm = msg2
            broadcast_msg = msg1

        assert resp_confirm["status"] == "published"
        assert broadcast_msg["payload"]["msg"] == "B Broadcast"
