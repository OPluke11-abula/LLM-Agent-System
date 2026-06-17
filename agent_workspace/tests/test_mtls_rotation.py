"""
tests/test_mtls_rotation.py - Verification tests for automated self-signed certificate generation and dynamic key rotation.
"""

import pytest
import os
import sys
import asyncio
import hashlib
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

# Ensure agent_workspace is in sys.path
workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)

from core.cert_manager import SwarmCertManager
from core.cross_cloud_gateway import CrossCloudGateway, CROSS_CLOUD_GATEWAY
from api import app

def test_cert_generation_and_fingerprint():
    """Verify that SwarmCertManager generates valid X.509 certs and keys, and computes correct fingerprints."""
    pk, cert, expiry = SwarmCertManager.generate_self_signed_cert("test-swarm-node", validity_seconds=60)
    assert "PRIVATE KEY-----" in pk
    assert "-----BEGIN CERTIFICATE-----" in cert
    assert expiry > datetime.now(timezone.utc)

    fingerprint = SwarmCertManager.get_cert_fingerprint(cert)
    assert len(fingerprint) == 64  # SHA-256 hex length is 64

def test_gateway_rotation_and_grace_period():
    """Verify that CrossCloudGateway shifts cert_sha to prev_cert_sha upon rotation."""
    gateway = CrossCloudGateway()
    initial_sha = gateway.cert_sha
    assert initial_sha is not None
    assert gateway.prev_cert_sha is None

    # Rotate
    gateway.rotate_certificate(validity_seconds=300)
    new_sha = gateway.cert_sha
    assert new_sha != initial_sha
    assert gateway.prev_cert_sha == initial_sha

    # Test handshake validation against current and previous
    payload = "handshake-check"
    sig_current = gateway.generate_signature(new_sha, payload)
    sig_prev = gateway.generate_signature(initial_sha, payload)

    assert gateway.validate_handshake(new_sha, sig_current, payload) is True
    assert gateway.validate_handshake(initial_sha, sig_prev, payload) is True

def test_handshake_revocation():
    """Verify that revoked certs are rejected in validate_handshake."""
    gateway = CrossCloudGateway()
    cert_sha = gateway.cert_sha
    payload = "handshake-check"
    sig = gateway.generate_signature(cert_sha, payload)

    assert gateway.validate_handshake(cert_sha, sig, payload) is True

    # Revoke
    gateway.revoked_certs.add(cert_sha)
    assert gateway.validate_handshake(cert_sha, sig, payload) is False

def test_api_mtls_endpoints():
    """Verify the FastAPI REST endpoints for certificate status, rotation, and revocation."""
    client = TestClient(app)

    # 1. Get status
    resp_status = client.get("/v1/cross-cloud/cert/status")
    assert resp_status.status_code == 200
    data_status = resp_status.json()
    assert data_status["status"] == "success"
    assert "cert_sha" in data_status
    assert "expiration" in data_status
    assert data_status["cert_status"] in ("active", "expiring", "expired")

    # 2. Force rotate
    resp_rotate = client.post("/v1/cross-cloud/cert/rotate")
    assert resp_rotate.status_code == 200
    data_rotate = resp_rotate.json()
    assert data_rotate["status"] == "success"
    assert data_rotate["cert_sha"] != data_status["cert_sha"]

    # 3. Revoke certificate
    old_sha = data_status["cert_sha"]
    resp_revoke = client.post("/v1/cross-cloud/revoke", json={"client_cert_sha": old_sha})
    assert resp_revoke.status_code == 200
    data_revoke = resp_revoke.json()
    assert data_revoke["status"] == "success"
    assert data_revoke["total_revoked_certs"] >= 1


def test_asymmetric_signing_and_verification():
    """Verify asymmetric signing with RSA private key and verification with certificate PEM."""
    pk, cert, _ = SwarmCertManager.generate_self_signed_cert("asymmetric-test", validity_seconds=60)
    payload = "secure-payload-data"
    
    # Sign payload
    signature_hex = SwarmCertManager.sign_payload(pk, payload)
    assert len(signature_hex) > 0
    
    # Verify valid signature
    assert SwarmCertManager.verify_signature(cert, signature_hex, payload) is True
    
    # Verify invalid payload fails
    assert SwarmCertManager.verify_signature(cert, signature_hex, "different-payload") is False
    
    # Verify bad signature fails
    assert SwarmCertManager.verify_signature(cert, "abcd" * 64, payload) is False


def test_sqlite_crl_persistence_across_gateway():
    """Verify SQLite-backed CRL read/write cycles, ensuring revoked certs persist across restarts."""
    gateway = CrossCloudGateway()
    mock_sha = hashlib.sha256(b"mock-certificate-pem").hexdigest()
    
    # Revoke cert SHA via ledger
    gateway.audit_ledger.revoke_certificate(mock_sha)
    assert gateway.audit_ledger.is_certificate_revoked(mock_sha) is True
    
    # Load CRL in a brand new gateway instance and check if it gets cached
    new_gateway = CrossCloudGateway()
    assert mock_sha in new_gateway.revoked_certs
    
    # Reinstate cert SHA via ledger
    new_gateway.audit_ledger.reinstate_certificate(mock_sha)
    assert new_gateway.audit_ledger.is_certificate_revoked(mock_sha) is False
    
    # New gateway reloaded shouldn't have it
    another_gateway = CrossCloudGateway()
    assert mock_sha not in another_gateway.revoked_certs


def test_handshake_validation_asymmetric_and_revoked():
    """Verify handshake validation using PEM certificate, valid signature, and check revocation rejects."""
    gateway = CrossCloudGateway()
    pk, cert, _ = SwarmCertManager.generate_self_signed_cert("handshake-asym-test", validity_seconds=60)
    cert_sha = SwarmCertManager.get_cert_fingerprint(cert)
    
    payload = "handshake-challenge-payload"
    signature = SwarmCertManager.sign_payload(pk, payload)
    
    # Handshake with valid PEM certificate
    assert gateway.validate_handshake(cert, signature, payload) is True
    
    # Handshake with valid cert, but certificate is revoked
    gateway.audit_ledger.revoke_certificate(cert_sha)
    # Refresh cache
    gateway.revoked_certs.add(cert_sha)
    
    assert gateway.validate_handshake(cert, signature, payload) is False
    
    # Reinstate
    gateway.audit_ledger.reinstate_certificate(cert_sha)
    gateway.revoked_certs.discard(cert_sha)
    assert gateway.validate_handshake(cert, signature, payload) is True


def test_api_reinstate_endpoint():
    """Verify the API endpoints for listing and reinstating revoked certificates."""
    client = TestClient(app)
    mock_sha = hashlib.sha256(b"api-reinstate-test-cert").hexdigest()
    
    # 1. Revoke it
    resp = client.post("/v1/cross-cloud/revoke", json={"client_cert_sha": mock_sha})
    assert resp.status_code == 200
    
    # 2. Verify it's in the revoked list
    resp_list = client.get("/v1/cross-cloud/revoked")
    assert resp_list.status_code == 200
    data_list = resp_list.json()
    assert data_list["status"] == "success"
    shas = [c["cert_sha"] for c in data_list["revoked_certificates"]]
    assert mock_sha in shas
    
    # 3. Reinstate it
    resp_reinstate = client.post("/v1/cross-cloud/reinstate", json={"client_cert_sha": mock_sha})
    assert resp_reinstate.status_code == 200
    data_reinstate = resp_reinstate.json()
    assert data_reinstate["status"] == "success"
    assert data_reinstate["client_cert_sha"] == mock_sha
    
    # 4. Verify it's no longer in the revoked list
    resp_list_after = client.get("/v1/cross-cloud/revoked")
    assert resp_list_after.status_code == 200
    shas_after = [c["cert_sha"] for c in resp_list_after.json()["revoked_certificates"]]
    assert mock_sha not in shas_after

