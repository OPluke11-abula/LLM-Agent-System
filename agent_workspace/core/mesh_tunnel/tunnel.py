"""Cross-Organization Encrypted P2P Mesh Tunnel & NAT Traversal (Phase 111).

Aligned with Universal Coding Agent Development Protocol v3.8.0, Anti-Corruption
Principle #4 (Typed Failures), and Principle #7 (Configuration over Hardcoding).

Provides STUN / DERP Relay NAT traversal simulation, virtual IP overlay management,
and zero-trust encrypted P2P tunnels across heterogeneous cloud and on-premise environments.
"""

from __future__ import annotations

import asyncio
import hashlib
import ipaddress
import logging
import time
import uuid
from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger("MeshNATBridge")


class NATType(str, Enum):
    """Classification of network address translation behavior."""

    FULL_CONE = "FULL_CONE"              # 1-to-1 NAT, easily punchable
    RESTRICTED_CONE = "RESTRICTED_CONE"  # Address/Port restricted cone
    SYMMETRIC = "SYMMETRIC"              # Requires DERP / TURN relay fallback


class TunnelStatus(str, Enum):
    """Lifecycle status of a P2P overlay tunnel session."""

    CONNECTING = "CONNECTING"
    ESTABLISHED = "ESTABLISHED"
    RELAYING = "RELAYING"
    FAILED = "FAILED"
    CLOSED = "CLOSED"


class NATEndpoint(BaseModel):
    """Public and local network coordination endpoint for a mesh node."""

    model_config = ConfigDict(extra="ignore")

    endpoint_id: str = Field(default_factory=lambda: f"ep-{uuid.uuid4().hex[:8]}")
    node_id: str
    organization_id: str
    public_ip: str
    public_port: int
    local_ip: str = "127.0.0.1"
    local_port: int = 8000
    nat_type: NATType = NATType.FULL_CONE
    virtual_ip: str = ""
    public_key: str = ""


class TunnelSession(BaseModel):
    """An active encrypted P2P or relayed overlay session between two endpoints."""

    model_config = ConfigDict(extra="ignore")

    session_id: str = Field(default_factory=lambda: f"tun-{uuid.uuid4().hex[:12]}")
    local_node_id: str
    remote_node_id: str
    local_vip: str
    remote_vip: str
    status: TunnelStatus = TunnelStatus.CONNECTING
    is_relayed: bool = False
    relay_server: Optional[str] = None
    latency_ms: float = 0.0
    bytes_sent: int = 0
    bytes_received: int = 0
    established_at: float = Field(default_factory=time.time)


class MeshNATBridge:
    """Manages cross-org P2P endpoint discovery, NAT hole punching, and DERP relay fallback."""

    def __init__(
        self,
        cluster_vip_subnet: str = "10.244.0.0/16",
        derp_relay_servers: Optional[List[str]] = None,
        handshake_timeout_ms: float = 500.0,
    ) -> None:
        self.subnet = ipaddress.ip_network(cluster_vip_subnet)
        self.ip_pool = self.subnet.hosts()
        self.derp_relay_servers = derp_relay_servers or [
            "derp-global-east.las.internal",
            "derp-global-west.las.internal",
        ]
        self.handshake_timeout_ms = handshake_timeout_ms

        self.registered_endpoints: Dict[str, NATEndpoint] = {}
        self.active_sessions: Dict[str, TunnelSession] = {}
        self._next_vip_index = 2

    def register_endpoint(
        self,
        node_id: str,
        organization_id: str,
        public_ip: str,
        public_port: int,
        nat_type: NATType = NATType.FULL_CONE,
        public_key: Optional[str] = None,
    ) -> NATEndpoint:
        """Registers a node network endpoint and allocates a unique virtual overlay IP."""
        vip = f"10.244.0.{self._next_vip_index}"
        self._next_vip_index += 1

        pk = public_key or hashlib.sha256(f"{node_id}:{vip}".encode()).hexdigest()[:32]
        endpoint = NATEndpoint(
            node_id=node_id,
            organization_id=organization_id,
            public_ip=public_ip,
            public_port=public_port,
            nat_type=nat_type,
            virtual_ip=vip,
            public_key=pk,
        )
        self.registered_endpoints[node_id] = endpoint
        logger.info("Registered endpoint %s for node %s with VIP %s", endpoint.endpoint_id, node_id, vip)
        return endpoint

    def unregister_endpoint(self, node_id: str) -> None:
        """Removes an endpoint and terminates its associated active tunnels."""
        self.registered_endpoints.pop(node_id, None)
        to_close = [
            sid for sid, s in self.active_sessions.items()
            if s.local_node_id == node_id or s.remote_node_id == node_id
        ]
        for sid in to_close:
            self.active_sessions[sid].status = TunnelStatus.CLOSED
            self.active_sessions.pop(sid, None)

    async def establish_tunnel(
        self,
        source_node_id: str,
        target_node_id: str,
    ) -> TunnelSession:
        """Performs NAT traversal and cryptographic handshake to establish an overlay tunnel."""
        start_time = time.perf_counter()

        src_ep = self.registered_endpoints.get(source_node_id)
        dst_ep = self.registered_endpoints.get(target_node_id)

        if not src_ep or not dst_ep:
            raise KeyError(f"Endpoints must both be registered before establishing tunnel: {source_node_id} -> {target_node_id}")

        session_key = f"{source_node_id}<->{target_node_id}"

        # Determine NAT traversal path
        # If either endpoint is SYMMETRIC NAT, direct UDP hole punching fails -> Fallback to DERP Relay
        needs_relay = (src_ep.nat_type == NATType.SYMMETRIC or dst_ep.nat_type == NATType.SYMMETRIC)
        relay_server = self.derp_relay_servers[0] if needs_relay else None

        # Simulate microsecond network handshake latency
        await asyncio.sleep(0.005)
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        if elapsed_ms > self.handshake_timeout_ms:
            session = TunnelSession(
                local_node_id=source_node_id,
                remote_node_id=target_node_id,
                local_vip=src_ep.virtual_ip,
                remote_vip=dst_ep.virtual_ip,
                status=TunnelStatus.FAILED,
                latency_ms=round(elapsed_ms, 2),
            )
            return session

        session = TunnelSession(
            local_node_id=source_node_id,
            remote_node_id=target_node_id,
            local_vip=src_ep.virtual_ip,
            remote_vip=dst_ep.virtual_ip,
            status=TunnelStatus.RELAYING if needs_relay else TunnelStatus.ESTABLISHED,
            is_relayed=needs_relay,
            relay_server=relay_server,
            latency_ms=round(elapsed_ms, 2),
        )

        self.active_sessions[session_key] = session
        logger.info(
            "Established tunnel %s (%s -> %s) status=%s relayed=%s in %.2fms",
            session.session_id,
            source_node_id,
            target_node_id,
            session.status.value,
            session.is_relayed,
            session.latency_ms,
        )
        return session

    def transmit_packet(self, session_key: str, payload_size_bytes: int) -> bool:
        """Simulates transmission of encrypted tunnel frames and updates telemetry counters."""
        session = self.active_sessions.get(session_key)
        if not session or session.status not in (TunnelStatus.ESTABLISHED, TunnelStatus.RELAYING):
            return False

        session.bytes_sent += payload_size_bytes
        session.bytes_received += payload_size_bytes
        return True
