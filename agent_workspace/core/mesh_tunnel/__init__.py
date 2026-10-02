"""Cross-Organization Encrypted P2P Mesh Tunnel & NAT Traversal (Phase 111).

Aligned with Universal Coding Agent Development Protocol v3.8.0.
Provides STUN/DERP NAT traversal, Zero-Knowledge task attestation,
and cross-region multi-cluster Raft consensus.
"""

from __future__ import annotations

from agent_workspace.core.mesh_tunnel.multi_cluster_raft import (
    ClusterRegion,
    FederatedRaftMultiCluster,
    MultiClusterProposalResult,
    RegionalClusterMember,
)
from agent_workspace.core.mesh_tunnel.tunnel import (
    MeshNATBridge,
    NATEndpoint,
    NATType,
    TunnelSession,
    TunnelStatus,
)
from agent_workspace.core.mesh_tunnel.zk_verifier import (
    SecurityLeakageError,
    StateMerkleAttestation,
    ZeroKnowledgeTaskVerifier,
    ZKProofPayload,
)

__all__ = [
    "MeshNATBridge",
    "NATEndpoint",
    "NATType",
    "TunnelSession",
    "TunnelStatus",
    "ZeroKnowledgeTaskVerifier",
    "ZKProofPayload",
    "StateMerkleAttestation",
    "SecurityLeakageError",
    "FederatedRaftMultiCluster",
    "ClusterRegion",
    "RegionalClusterMember",
    "MultiClusterProposalResult",
]
