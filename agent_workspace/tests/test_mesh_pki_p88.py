"""Unit and integration test suite for Phase 88 Zero-Trust mTLS Dynamic Node Attestation & PKI Mesh.

Validates:
1. Ephemeral X.509 certificate generation, lifecycle tracking, and expiry calculation.
2. Automated background certificate rotation and threshold trigger.
3. Attestation challenge nonce generation, TTL expiration, and single-use replay protection.
4. Mutual attestation challenge-response handshake between coordinator nodes.
5. Rejection of tampered signatures, spoofed nonces, and invalid certificate fingerprints.
6. Cryptographically signed delegation requests and Zero-Trust enforcement under strict mode.
7. REST API routes (/v1/mesh/pki/cert, /v1/mesh/pki/rotate, /v1/mesh/attest/challenge, /v1/mesh/attest/verify).
8. CLI toolbelt commands (las mesh pki, las mesh rotate, las mesh attest).
"""

from __future__ import annotations

import io
import sys
import time
import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from agent_workspace.api import app
from agent_workspace.cli import main
from agent_workspace.core.cert_manager import SwarmCertManager
from agent_workspace.core.federated_mesh import (
    AttestationChallenge,
    AttestationProof,
    AttestationStatus,
    FederatedDelegationRequest,
    FederatedMeshCoordinator,
    FederatedPeerProfile,
    PeerCapability,
    get_federated_coordinator,
)


class TestMeshPKIP88(unittest.TestCase):
    """Test suite for Phase 88 Zero-Trust mTLS Dynamic Node Attestation & Mutual TLS PKI Mesh."""

    def setUp(self) -> None:
        self.cert_manager = SwarmCertManager()
        self.coordinator_a = FederatedMeshCoordinator(
            node_id="node-leader-a",
            role="architect",
            host="127.0.0.1",
            port=8000,
            capabilities=[PeerCapability.COCKPIT_LEADER, PeerCapability.REASONING_ENGINE],
            strict_attestation=False,
        )
        self.coordinator_b = FederatedMeshCoordinator(
            node_id="node-worker-b",
            role="worker",
            host="127.0.0.1",
            port=8001,
            capabilities=[PeerCapability.TEST_RUNNER],
            strict_attestation=False,
        )

    def test_cert_manager_x509_lifecycle_and_expiry(self) -> None:
        """Validates X.509 certificate generation, validity verification, and expiry tracking."""
        cert_pem, key_pem = self.cert_manager.generate_agent_cert(
            common_name="node-test-01",
            validity_seconds=3600,
        )
        self.assertIn("BEGIN CERTIFICATE", cert_pem)
        self.assertIn("PRIVATE KEY", key_pem)

        # Validity check
        self.assertTrue(self.cert_manager.is_cert_valid(cert_pem))

        # Expiry check
        expiry = self.cert_manager.get_cert_expiry(cert_pem)
        self.assertIsNotNone(expiry)

        # Rotation threshold: with 3600s validity, 300s threshold should not trigger
        self.assertFalse(self.cert_manager.should_rotate_cert(cert_pem, threshold_seconds=300))
        # But with 7200s threshold, it should trigger
        self.assertTrue(self.cert_manager.should_rotate_cert(cert_pem, threshold_seconds=7200))

    def test_coordinator_cert_rotation_and_auto_rotate(self) -> None:
        """Validates coordinator manual rotation and auto-rotate threshold checking."""
        initial_fp = self.coordinator_a.profile.cert_fingerprint
        self.assertIsNotNone(initial_fp)

        # Rotate cert with new validity
        new_fp = self.coordinator_a.rotate_cert(validity_seconds=1800)
        self.assertNotEqual(new_fp, initial_fp)
        self.assertEqual(self.coordinator_a.profile.node_id, "node-leader-a")
        self.assertTrue(self.cert_manager.is_cert_valid(self.coordinator_a.profile.cert_pem))

        # Test check_and_auto_rotate_cert
        # Threshold of 1 second should not trigger rotation since validity is 1800s
        rotated = self.coordinator_a.check_and_auto_rotate_cert(threshold_seconds=1)
        self.assertFalse(rotated)

        # Threshold of 5000 seconds should trigger auto-rotation
        rotated = self.coordinator_a.check_and_auto_rotate_cert(threshold_seconds=5000)
        self.assertTrue(rotated)

    def test_attestation_challenge_lifecycle_and_replay_protection(self) -> None:
        """Validates challenge generation, entropy, and single-use replay prevention."""
        challenge = self.coordinator_a.generate_attestation_challenge(
            target_node_id="node-worker-b",
            ttl_seconds=60,
        )
        self.assertEqual(challenge.target_node_id, "node-worker-b")
        self.assertEqual(challenge.issuer_node_id, "node-leader-a")
        self.assertGreaterEqual(len(challenge.nonce), 32)
        self.assertFalse(challenge.is_expired())

        # Challenge should be recorded in active_challenges
        self.assertIn(challenge.challenge_id, self.coordinator_a.active_challenges)

        # Generating proof and verifying should consume the challenge
        proof = self.coordinator_b.create_attestation_proof(
            challenge_id=challenge.challenge_id,
            nonce=challenge.nonce,
        )
        success, msg = self.coordinator_a.verify_attestation_proof(proof)
        self.assertTrue(success, f"Verification failed: {msg}")

        # Replay attempt with the same challenge_id must fail
        replay_success, replay_msg = self.coordinator_a.verify_attestation_proof(proof)
        self.assertFalse(replay_success)
        self.assertIn("not found or already used", replay_msg)

    def test_attestation_challenge_ttl_expiration(self) -> None:
        """Validates that expired challenges are rejected."""
        # Create challenge with 0 second TTL
        challenge = self.coordinator_a.generate_attestation_challenge(
            target_node_id="node-worker-b",
            ttl_seconds=0,
        )
        time.sleep(0.05)
        self.assertTrue(challenge.is_expired())

        proof = self.coordinator_b.create_attestation_proof(
            challenge_id=challenge.challenge_id,
            nonce=challenge.nonce,
        )
        success, msg = self.coordinator_a.verify_attestation_proof(proof)
        self.assertFalse(success)
        self.assertIn("expired", msg)

    def test_mutual_attestation_handshake(self) -> None:
        """Validates full mutual attestation challenge-response flow between two nodes."""
        # 1. Register node B in node A as PENDING
        peer_b_profile = self.coordinator_b.profile
        self.coordinator_a.register_peer(peer_b_profile)
        self.assertEqual(
            self.coordinator_a.peers["node-worker-b"].attestation_status,
            AttestationStatus.PENDING,
        )

        # 2. Node A issues challenge to Node B
        challenge = self.coordinator_a.generate_attestation_challenge("node-worker-b", ttl_seconds=30)

        # 3. Node B solves challenge by signing nonce
        proof = self.coordinator_b.create_attestation_proof(
            challenge_id=challenge.challenge_id,
            nonce=challenge.nonce,
        )
        self.assertEqual(proof.origin_node_id, "node-worker-b")
        self.assertEqual(proof.cert_fingerprint, self.coordinator_b.profile.cert_fingerprint)

        # 4. Node A verifies proof
        success, msg = self.coordinator_a.verify_attestation_proof(proof)
        self.assertTrue(success, msg)

        # Node B in Node A's registry should now be VERIFIED
        self.assertEqual(
            self.coordinator_a.peers["node-worker-b"].attestation_status,
            AttestationStatus.VERIFIED,
        )
        self.assertIsNotNone(self.coordinator_a.peers["node-worker-b"].attestation_timestamp)

    def test_attestation_rejection_on_tampering(self) -> None:
        """Validates that tampered signatures, spoofed nonces, or mismatched fingerprints are rejected."""
        challenge = self.coordinator_a.generate_attestation_challenge("node-worker-b", ttl_seconds=60)
        valid_proof = self.coordinator_b.create_attestation_proof(
            challenge_id=challenge.challenge_id,
            nonce=challenge.nonce,
        )

        # 1. Tampered signature
        tampered_sig_proof = AttestationProof(
            challenge_id=valid_proof.challenge_id,
            origin_node_id=valid_proof.origin_node_id,
            cert_pem=valid_proof.cert_pem,
            cert_fingerprint=valid_proof.cert_fingerprint,
            signed_nonce="deadbeef" * 8,
        )
        success, msg = self.coordinator_a.verify_attestation_proof(tampered_sig_proof)
        self.assertFalse(success)
        self.assertIn("Invalid attestation signature", msg)

        # 2. Fingerprint mismatch
        challenge2 = self.coordinator_a.generate_attestation_challenge("node-worker-b", ttl_seconds=60)
        valid_proof2 = self.coordinator_b.create_attestation_proof(
            challenge_id=challenge2.challenge_id,
            nonce=challenge2.nonce,
        )
        tampered_fp_proof = AttestationProof(
            challenge_id=valid_proof2.challenge_id,
            origin_node_id=valid_proof2.origin_node_id,
            cert_pem=valid_proof2.cert_pem,
            cert_fingerprint="0000000000000000000000000000000000000000000000000000000000000000",
            signed_nonce=valid_proof2.signed_nonce,
        )
        success, msg = self.coordinator_a.verify_attestation_proof(tampered_fp_proof)
        self.assertFalse(success)
        self.assertIn("fingerprint mismatch", msg.lower())

    def test_signed_delegation_request_and_zero_trust(self) -> None:
        """Validates that delegation requests are signed and verified with Zero-Trust enforcement."""
        req = FederatedDelegationRequest(
            task_id="TASK-P88-001",
            delegation_type="test_verification",
            origin_node_id="node-leader-a",
            role="architect",
            payload={"action": "run_test_ladder", "suite": "p88"},
        )

        # Sign request
        signed_req = self.coordinator_a.sign_delegation_request(req)
        self.assertIsNotNone(signed_req.sender_signature)
        self.assertEqual(signed_req.sender_cert_fingerprint, self.coordinator_a.profile.cert_fingerprint)

        # Node B verifies request
        # First register Node A in Node B and attest
        self.coordinator_b.register_peer(self.coordinator_a.profile)
        chal = self.coordinator_b.generate_attestation_challenge("node-leader-a")
        proof = self.coordinator_a.create_attestation_proof(chal.challenge_id, chal.nonce)
        self.coordinator_b.verify_attestation_proof(proof)

        ok, msg = self.coordinator_b.verify_delegation_request(signed_req)
        self.assertTrue(ok, msg)

        # Tampered payload fails verification
        tampered_req = signed_req.model_copy(update={"payload": {"action": "malicious_exploit"}})
        ok_tampered, msg_tampered = self.coordinator_b.verify_delegation_request(tampered_req)
        self.assertFalse(ok_tampered)
        self.assertIn("signature verification failed", msg_tampered)

        # Strict attestation enforcement: if peer is unverified, reject
        strict_coordinator = FederatedMeshCoordinator(
            node_id="node-strict",
            role="worker",
            strict_attestation=True,
        )
        # Register Node A without attestation
        strict_coordinator.register_peer(self.coordinator_a.profile)
        ok_strict, msg_strict = strict_coordinator.verify_delegation_request(signed_req)
        self.assertFalse(ok_strict)
        self.assertIn("failed zero-trust attestation check", msg_strict)

    def test_fastapi_mesh_pki_routes(self) -> None:
        """Validates FastAPI REST endpoints for PKI and attestation."""
        client = TestClient(app)

        # 1. GET /v1/mesh/pki/cert
        res = client.get("/v1/mesh/pki/cert")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("node_id", data)
        self.assertIn("cert_pem", data)
        self.assertIn("cert_fingerprint", data)
        self.assertIn("expires_at", data)
        self.assertEqual(data["status"], "ACTIVE")

        # 2. POST /v1/mesh/pki/rotate
        res_rot = client.post("/v1/mesh/pki/rotate", json={"validity_seconds": 1800})
        self.assertEqual(res_rot.status_code, 200)
        rot_data = res_rot.json()
        self.assertIn("cert_fingerprint", rot_data)
        self.assertEqual(rot_data["status"], "ACTIVE")

        # 3. POST /v1/mesh/attest/challenge
        res_chal = client.post("/v1/mesh/attest/challenge", json={"target_node_id": "test-node", "ttl_seconds": 60})
        self.assertEqual(res_chal.status_code, 200)
        chal_data = res_chal.json()
        self.assertIn("challenge_id", chal_data)
        self.assertIn("nonce", chal_data)
        self.assertEqual(chal_data["target_node_id"], "test-node")

        # 4. POST /v1/mesh/attest/verify (using coordinator proof)
        coord = get_federated_coordinator()
        proof = coord.create_attestation_proof(chal_data["challenge_id"], chal_data["nonce"])
        res_ver = client.post(
            "/v1/mesh/attest/verify",
            json=proof.model_dump(),
        )
        self.assertEqual(res_ver.status_code, 200)
        ver_data = res_ver.json()
        self.assertTrue(ver_data["success"])

        # 5. GET /v1/mesh/status with PKI fields
        res_status = client.get("/v1/mesh/status")
        self.assertEqual(res_status.status_code, 200)
        status_data = res_status.json()
        self.assertEqual(status_data["pki_status"], "ACTIVE")
        self.assertIn("cert_fingerprint", status_data)
        self.assertGreater(status_data["cert_expires_in_sec"], 0)

    def test_cli_mesh_pki_commands(self) -> None:
        """Validates CLI subcommands: las mesh pki, las mesh rotate, las mesh attest."""
        # 1. las mesh pki
        stdout_capture = io.StringIO()
        with patch.object(sys, "argv", ["las", "mesh", "pki"]), patch("sys.stdout", stdout_capture):
            main()
        output = stdout_capture.getvalue()
        self.assertIn("Zero-Trust mTLS PKI Identity", output)
        self.assertIn("Fingerprint", output)

        # 2. las mesh rotate
        stdout_capture = io.StringIO()
        with patch.object(sys, "argv", ["las", "mesh", "rotate", "--validity", "2400"]), patch("sys.stdout", stdout_capture):
            main()
        output = stdout_capture.getvalue()
        self.assertIn("Zero-Trust PKI Certificate Rotated Successfully", output)
        self.assertIn("New Fingerprint", output)

        # 3. las mesh attest
        stdout_capture = io.StringIO()
        with patch.object(sys, "argv", ["las", "mesh", "attest", "127.0.0.1:8000"]), patch("sys.stdout", stdout_capture):
            main()
        output = stdout_capture.getvalue()
        self.assertIn("Zero-Trust Mutual Attestation Handshake", output)
        self.assertIn("Status          : VERIFIED", output)
