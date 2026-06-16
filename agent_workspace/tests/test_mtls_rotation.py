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
