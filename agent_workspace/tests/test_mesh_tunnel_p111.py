"""Unit and integration tests for Cross-Organization P2P Mesh Tunnel & NAT Traversal (Phase 111).

Validates MeshNATBridge STUN/DERP NAT traversal, ZeroKnowledgeTaskVerifier air-gap protection,
FederatedRaftMultiCluster WAN consensus & regional failover, and MeshFactoryDispatcher routing.
"""

import pytest

from agent_workspace.core.factory.models import (
    RefactoringTaskDAG,
    RefactoringTaskNode,
    RefactoringTaskType,
)
from agent_workspace.core.factory.mesh_dispatcher import MeshFactoryDispatcher
from agent_workspace.core.federated_mesh import PeerCapability
from agent_workspace.core.mesh_tunnel import (
    ClusterRegion,
    FederatedRaftMultiCluster,
    MeshNATBridge,
    NATEndpoint,
    NATType,
    MultiClusterProposalResult,
    SecurityLeakageError,
    StateMerkleAttestation,
    TunnelSession,
    TunnelStatus,
    ZeroKnowledgeTaskVerifier,
    ZKProofPayload,
)
from agent_workspace.core.raft_consensus import CommitteeEntryType, RaftRole


# --- Test Fixtures ---

SAMPLE_SOURCE_CODE = """
import os
import sys

class CrossOrgPaymentGateway:
    def process_transaction(self, account_id: str, amount: float) -> bool:
        if amount <= 0:
            return False
        return True

def audit_hash(tx_id: str) -> str:
    return f"tx-audited-{tx_id}"
"""


# --- MeshNATBridge Tests ---

@pytest.mark.asyncio
async def test_mesh_nat_bridge_endpoint_registration():
    """Verify endpoint registration allocates unique virtual IPs in cluster overlay."""
    bridge = MeshNATBridge()
    ep1 = bridge.register_endpoint(
        node_id="node-org-a-1",
        organization_id="org-acme",
        public_ip="203.0.113.10",
        public_port=8443,
        nat_type=NATType.FULL_CONE,
    )
    ep2 = bridge.register_endpoint(
        node_id="node-org-b-1",
        organization_id="org-globex",
        public_ip="198.51.100.25",
        public_port=9443,
        nat_type=NATType.FULL_CONE,
    )

    assert ep1.virtual_ip.startswith("10.244.0.")
    assert ep2.virtual_ip.startswith("10.244.0.")
    assert ep1.virtual_ip != ep2.virtual_ip
    assert ep1.node_id in bridge.registered_endpoints


@pytest.mark.asyncio
async def test_mesh_nat_bridge_direct_p2p_hole_punch():
    """Verify direct P2P hole punch succeeds between Full Cone NAT endpoints (<500ms)."""
    bridge = MeshNATBridge(handshake_timeout_ms=500.0)
    bridge.register_endpoint("node-a", "org-a", "203.0.113.1", 8000, NATType.FULL_CONE)
    bridge.register_endpoint("node-b", "org-b", "198.51.100.2", 8000, NATType.FULL_CONE)

    session = await bridge.establish_tunnel("node-a", "node-b")

    assert session.status == TunnelStatus.ESTABLISHED
    assert session.is_relayed is False
    assert session.latency_ms < 500.0
    assert session.local_vip == "10.244.0.2"
    assert session.remote_vip == "10.244.0.3"

    # Packet transmission telemetry
    sent = bridge.transmit_packet("node-a<->node-b", payload_size_bytes=1024)
    assert sent is True
    assert session.bytes_sent == 1024


@pytest.mark.asyncio
async def test_mesh_nat_bridge_symmetric_nat_derp_relay_fallback():
    """Verify symmetric NAT automatically falls back to DERP Relay tunnel."""
    bridge = MeshNATBridge()
    bridge.register_endpoint("node-sym-a", "org-a", "203.0.113.10", 8000, NATType.SYMMETRIC)
    bridge.register_endpoint("node-cone-b", "org-b", "198.51.100.20", 8000, NATType.FULL_CONE)

    session = await bridge.establish_tunnel("node-sym-a", "node-cone-b")

    assert session.status == TunnelStatus.RELAYING
    assert session.is_relayed is True
    assert session.relay_server is not None
    assert "derp-" in session.relay_server


# --- ZeroKnowledgeTaskVerifier Tests ---

def test_zk_verifier_ast_shape_and_merkle_root():
    """Verify AST shape extraction and deterministic Merkle root calculation."""
    verifier = ZeroKnowledgeTaskVerifier(organization_id="org-defense")
    shape = verifier.extract_ast_shape(SAMPLE_SOURCE_CODE)

    assert "CrossOrgPaymentGateway" in shape["classes"]
    assert any("process_transaction" in f for f in shape["functions"])
    assert any("audit_hash" in f for f in shape["functions"])

    root1 = verifier.compute_merkle_root(SAMPLE_SOURCE_CODE)
    root2 = verifier.compute_merkle_root(SAMPLE_SOURCE_CODE)
    assert root1 == root2
    assert len(root1) == 64  # SHA-256


def test_zk_verifier_create_task_proof_redaction():
    """Verify ZK proof redacts raw code statements while retaining structural proof."""
    verifier = ZeroKnowledgeTaskVerifier(organization_id="org-defense")
    proof = verifier.create_task_proof(task_id="task-zk-001", code_content=SAMPLE_SOURCE_CODE)

    assert isinstance(proof, ZKProofPayload)
    assert proof.airgap_verified is True
    assert len(proof.merkle_root) == 64
    assert len(proof.ast_shape_hash) == 64

    # The proof must NOT leak source code
    proof_dict = proof.model_dump()
    assert verifier.verify_no_unauthorized_leakage(proof_dict) is True


def test_zk_verifier_detects_unauthorized_code_leakage():
    """Verify Anti-Leak Invariant: SecurityLeakageError raised when raw code is smuggled."""
    verifier = ZeroKnowledgeTaskVerifier()
    leaked_payload = {
        "proof_id": "test",
        "leaked_raw_code": "def stolen_function(): return secret_key",
    }
    with pytest.raises(SecurityLeakageError) as exc_info:
        verifier.verify_no_unauthorized_leakage(leaked_payload)
    assert "violates zero-knowledge policy" in str(exc_info.value)


def test_zk_verifier_attestation_signature_validation():
    """Verify execution attestation generation and cryptographic validation."""
    verifier = ZeroKnowledgeTaskVerifier(organization_id="org-alpha")
    proof = verifier.create_task_proof("task-zk-002", SAMPLE_SOURCE_CODE)

    attestation = verifier.generate_execution_attestation(
        proof=proof,
        executor_node_id="node-worker-beta",
        output_result_str='{"tests_passed": 12, "regressions": 0}',
        exit_code=0,
    )

    assert isinstance(attestation, StateMerkleAttestation)
    assert attestation.passed is True
    assert verifier.verify_execution_attestation(proof, attestation) is True

    # Tampered attestation fails verification
    tampered_attestation = attestation.model_copy()
    tampered_attestation.output_state_hash = "tampered_fake_hash"
    assert verifier.verify_execution_attestation(proof, tampered_attestation) is False


# --- FederatedRaftMultiCluster Tests ---

@pytest.mark.asyncio
async def test_multi_cluster_raft_cross_region_election():
    """Verify cross-cluster Raft leader election gathers votes across regions."""
    federation = FederatedRaftMultiCluster()
    federation.register_regional_node("node-us-1", ClusterRegion.US_EAST, "org-east", "10.244.0.10", latency_weight_ms=5.0)
    federation.register_regional_node("node-eu-1", ClusterRegion.EU_CENTRAL, "org-west", "10.244.0.20", latency_weight_ms=10.0)
    federation.register_regional_node("node-ap-1", ClusterRegion.AP_EAST, "org-asia", "10.244.0.30", latency_weight_ms=15.0)

    elected = await federation.elect_cross_cluster_leader("node-us-1")
    assert elected is True
    assert federation.current_cross_cluster_leader == "node-us-1"
    assert federation.nodes["node-us-1"].role == RaftRole.LEADER


@pytest.mark.asyncio
async def test_multi_cluster_raft_cross_region_log_replication():
    """Verify log replication across multi-region clusters advances commit index."""
    federation = FederatedRaftMultiCluster()
    federation.register_regional_node("node-us-1", ClusterRegion.US_EAST, "org-us", "10.244.0.10")
    federation.register_regional_node("node-eu-1", ClusterRegion.EU_CENTRAL, "org-eu", "10.244.0.20")
    federation.register_regional_node("node-ap-1", ClusterRegion.AP_EAST, "org-ap", "10.244.0.30")

    result = await federation.replicate_cross_region_entry(
        entry_type=CommitteeEntryType.PATCH_COMMIT,
        payload={"task_id": "cross-org-task-01", "merkle_root": "0" * 64},
    )

    assert isinstance(result, MultiClusterProposalResult)
    assert result.success is True
    assert result.log_index >= 1
    assert len(result.regions_committed) >= 2
    assert result.nodes_acknowledged == 3

    # All nodes must have committed the new log entry
    for node in federation.nodes.values():
        assert node.commit_index == result.log_index
        assert len(node.log) > 1


@pytest.mark.asyncio
async def test_multi_cluster_raft_regional_partition_failover():
    """Verify disaster recovery: regional partition triggers failover to surviving region."""
    federation = FederatedRaftMultiCluster()
    federation.register_regional_node("node-us-1", ClusterRegion.US_EAST, "org-us", "10.244.0.10")
    federation.register_regional_node("node-eu-1", ClusterRegion.EU_CENTRAL, "org-eu", "10.244.0.20")
    federation.register_regional_node("node-ap-1", ClusterRegion.AP_EAST, "org-ap", "10.244.0.30")

    # Initial leader is in US_EAST
    await federation.elect_cross_cluster_leader("node-us-1")
    assert federation.current_cross_cluster_leader == "node-us-1"

    # US_EAST experiences fiber cut / disaster partition
    new_leader = await federation.handle_regional_partition(ClusterRegion.US_EAST)

    assert new_leader is not None
    assert new_leader != "node-us-1"
    assert federation.members[new_leader].region in (ClusterRegion.EU_CENTRAL, ClusterRegion.AP_EAST)
    assert federation.nodes[new_leader].role == RaftRole.LEADER


# --- MeshFactoryDispatcher Integration Tests ---

def test_mesh_dispatcher_routes_cross_org_federation():
    """Verify MeshFactoryDispatcher assigns CROSS_ORG_FEDERATION to CROSS_ORG_GATEWAY."""
    dispatcher = MeshFactoryDispatcher()

    # Verify node-cross-org-gateway is in peer registry
    assert "node-cross-org-gateway" in dispatcher.peers
    assert PeerCapability.CROSS_ORG_GATEWAY.value in dispatcher.peers["node-cross-org-gateway"]

    dag = RefactoringTaskDAG(goal="Cross-Org Delegation Test")
    t1 = RefactoringTaskNode(
        node_id="task-cross-org-1",
        title="Cross-Org Zero-Knowledge Task Sync",
        task_type=RefactoringTaskType.CROSS_ORG_FEDERATION,
        target_files=["tunnel.py"],
        mutable_scope=["tunnel.py"],
    )
    dag.add_node(t1)

    plan = dispatcher.create_dispatch_plan(dag)
    assert len(plan.assignments) == 1

    assignment = plan.assignments[0]
    assert assignment.required_capability == PeerCapability.CROSS_ORG_GATEWAY.value
    assert assignment.assigned_peer_id == "node-cross-org-gateway"
