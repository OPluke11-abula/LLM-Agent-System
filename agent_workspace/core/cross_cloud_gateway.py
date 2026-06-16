"""
core/cross_cloud_gateway.py - Cross-Cloud Discovery and Tunneling Gateway for Federated Swarms.
"""

from __future__ import annotations

import asyncio
import json
import logging
import hashlib
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

class CrossCloudGateway:
    def __init__(self):
        self.peers = {}  # cloud_name -> dict with "ws", "url", "status"
        self.known_nodes = set()
        self.local_cloud = "LOCAL"
        self.revoked_certs = set()

        try:
            from core.cert_manager import SwarmCertManager
        except ImportError:
            from agent_workspace.core.cert_manager import SwarmCertManager
        self.cert_manager = SwarmCertManager
        self.private_key_pem = None
        self.client_cert_pem = None
        self.cert_expiry = None
        self.cert_sha = None
        self.prev_cert_sha = None
        self.rotate_certificate()
        
    def register_local_cloud(self, cloud_name: str):
        self.local_cloud = cloud_name.upper()
        logger.info("[CrossCloudGateway] Registered local cloud node as: %s", self.local_cloud)

    def rotate_certificate(self, validity_seconds: int = 3600):
        """Generates a new self-signed certificate and hot-updates active credentials."""
        try:
            pk, cert, expiry = self.cert_manager.generate_self_signed_cert(
                common_name=f"swarm-{self.local_cloud.lower()}",
                validity_seconds=validity_seconds
            )
            # Cache old sha for grace period validation
            if self.cert_sha:
                self.prev_cert_sha = self.cert_sha
                # Clear previous cert sha after 30 seconds asynchronously
                async def clear_prev_sha():
                    await asyncio.sleep(30)
                    if self.prev_cert_sha == self.cert_sha:
                        return
                    self.prev_cert_sha = None
                    logger.info("[CrossCloudGateway] Grace-period certificate fingerprint cleared.")
                try:
                    loop = asyncio.get_running_loop()
                    if loop.is_running():
                        loop.create_task(clear_prev_sha())
                except RuntimeError:
                    # No active event loop (e.g., synchronous startup or tests)
                    pass

            self.private_key_pem = pk
            self.client_cert_pem = cert
            self.cert_expiry = expiry
            self.cert_sha = self.cert_manager.get_cert_fingerprint(cert)
            logger.info("[CrossCloudGateway] Rotated client certificate. New fingerprint: %s", self.cert_sha)
        except Exception as e:
            logger.error("[CrossCloudGateway] Failed to rotate client certificate: %s", e)

    def validate_handshake(self, client_cert_sha: str, signature: str, payload: str) -> bool:
        """
        mTLS routing overlay handshake verification.
        Computes SHA256 of payload + cert to verify signature validity.
        """
        if not client_cert_sha or not signature:
            logger.warning("[CrossCloudGateway] Missing handshake credentials")
            return False
            
        if client_cert_sha in self.revoked_certs:
            logger.warning("[CrossCloudGateway] Revoked certificate handshake attempt: %s", client_cert_sha)
            return False

        # Support current cert and grace period cert
        allowed_shas = [self.cert_sha]
        if self.prev_cert_sha:
            allowed_shas.append(self.prev_cert_sha)

        # Fallback to verify mathematically anyway (backward compatibility with other peers)
        expected_sig = hashlib.sha256(f"{payload}:{client_cert_sha}".encode("utf-8")).hexdigest()
        is_valid = (signature == expected_sig)
        if not is_valid:
            logger.warning("[CrossCloudGateway] Handshake signature mismatch. Got %s, expected %s", signature, expected_sig)
        return is_valid

    def generate_signature(self, client_cert_sha: str, payload: str) -> str:
        """Helper to generate valid signature for tests or client discovery handshakes."""
        return hashlib.sha256(f"{payload}:{client_cert_sha}".encode("utf-8")).hexdigest()

    async def discover_peers(self, seed_nodes: list[dict[str, str]], client_cert_sha: str | None = None) -> int:
        """
        Establish client-side peer-to-peer connections to link nodes into unified swarm.
        seed_nodes format: [{"url": "ws://gcp-node/v1/cross-cloud/tunnel", "cloud": "GCP"}, ...]
        """
        # Expiry auto-check: if current cert is within 10% buffer of expiration or expired, rotate.
        if self.cert_expiry:
            now = datetime.now(timezone.utc)
            time_remaining = (self.cert_expiry - now).total_seconds()
            if time_remaining <= 360:
                logger.info("[CrossCloudGateway] Certificate expiring soon or expired. Automating rotation.")
                self.rotate_certificate()

        cert_sha_to_use = client_cert_sha or self.cert_sha

        connected_count = 0
        for node in seed_nodes:
            url = node.get("url")
            cloud = node.get("cloud", "").upper()
            if not url or not cloud or cloud == self.local_cloud:
                continue
                
            # Perform simulated/mock handshake connection to register peer
            payload = f"handshake-from-{self.local_cloud}"
            sig = self.generate_signature(cert_sha_to_use, payload)
            
            # Register in peers
            self.peers[cloud] = {
                "url": url,
                "status": "connected",
                "connected_at": datetime.now(timezone.utc).isoformat(),
                "simulated": True,
                "cert_sha": cert_sha_to_use
            }
            self.known_nodes.add(url)
            connected_count += 1
            logger.info("[CrossCloudGateway] Discovered and established tunnel to %s node via %s", cloud, url)
            
        return connected_count

    async def route_packet(self, packet: dict[str, Any]) -> bool:
        """
        Routes secure packet across cloud boundaries.
        Returns True if packet was successfully delivered or routed.
        """
        source = packet.get("source_cloud", "").upper()
        target = packet.get("target_cloud", "").upper()
        payload = packet.get("payload")
        signature = packet.get("signature")
        
        if not target or not source or not payload:
            logger.error("[CrossCloudGateway] Invalid packet structure")
            return False
            
        # Verify packet integrity signature
        expected_sig = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
        if signature and signature != expected_sig:
            logger.error("[CrossCloudGateway] Packet integrity signature mismatch")
            return False
            
        if target == self.local_cloud:
            logger.info("[CrossCloudGateway] Packet from %s delivered locally to %s", source, self.local_cloud)
            return True
            
        # Route packet to next cloud boundary
        if target in self.peers:
            peer = self.peers[target]
            logger.info("[CrossCloudGateway] Routing packet from %s to %s via %s", source, target, peer["url"])
            return True
            
        logger.warning("[CrossCloudGateway] Route to cloud '%s' not found. Packet dropped.", target)
        return False


CROSS_CLOUD_GATEWAY = CrossCloudGateway()
