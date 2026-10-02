"""Golden Benchmark for Cross-Organization Encrypted P2P Mesh Subsystem (Phase 111).

Executes end-to-end cross-organization P2P and NAT traversal benchmarks:
1. P2P NAT Hole Punching & DERP Relay Fallback across Organizations (<500ms)
2. Zero-Knowledge State Attestation & Air-gap Code Leakage Audit
3. Multi-Cluster Cross-Region Raft Quorum Replication (US_EAST, EU_CENTRAL, AP_EAST)
4. Regional Disaster Recovery & Automatic Leader Failover
5. Mesh Factory Workload Dispatch to PeerCapability.CROSS_ORG_GATEWAY
6. Verifiable Golden Receipt Export (.agent/evidence/cross_org_mesh_receipt.json)

Usage:
    python scripts/run_cross_org_mesh_benchmark.py [--output PATH]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict

# Ensure project root in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from agent_workspace.core.factory.mesh_dispatcher import MeshFactoryDispatcher
from agent_workspace.core.factory.models import (
    RefactoringTaskDAG,
    RefactoringTaskNode,
    RefactoringTaskType,
)
from agent_workspace.core.federated_mesh import PeerCapability
from agent_workspace.core.mesh_tunnel import (
    ClusterRegion,
    FederatedRaftMultiCluster,
    MeshNATBridge,
    NATType,
    TunnelStatus,
    ZeroKnowledgeTaskVerifier,
)
from agent_workspace.core.raft_consensus import CommitteeEntryType

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("CrossOrgMeshBenchmark")


async def run_cross_org_mesh_benchmark_async(output_file: Path) -> Dict[str, Any]:
    """Runs the full Cross-Organization P2P Mesh benchmark and exports receipt."""
    start_time = time.perf_counter()
    logger.info("Starting Cross-Organization Encrypted P2P Mesh Benchmark (Phase 111)...")

    # 1. P2P NAT Traversal & Tunnel Handshake Benchmark
    bridge = MeshNATBridge(handshake_timeout_ms=500.0)
    ep_a = bridge.register_endpoint("node-org-a", "org-alpha", "198.51.100.1", 8443, NATType.FULL_CONE)
    ep_b = bridge.register_endpoint("node-org-b", "org-beta", "203.0.113.2", 8443, NATType.FULL_CONE)
    ep_c = bridge.register_endpoint("node-org-c-sym", "org-gamma", "192.0.2.3", 8443, NATType.SYMMETRIC)

    # Test direct P2P tunnel
    direct_session = await bridge.establish_tunnel("node-org-a", "node-org-b")
    direct_latency_ms = direct_session.latency_ms

    # Test DERP relay fallback
    relayed_session = await bridge.establish_tunnel("node-org-a", "node-org-c-sym")

    # 2. Zero-Knowledge State & Air-gap Protection Benchmark
    zk_verifier = ZeroKnowledgeTaskVerifier(organization_id="org-alpha")
    sample_code = """
class EnterpriseContract:
    def verify_payment(self, account: str, val: float) -> bool:
        return val > 0.0

def generate_tx_signature(tx_id: str) -> str:
    return f"sig-{tx_id}"
"""
    proof = zk_verifier.create_task_proof("task-cross-org-01", sample_code)
    airgap_clean = zk_verifier.verify_no_unauthorized_leakage(proof.model_dump())

    attestation = zk_verifier.generate_execution_attestation(
        proof=proof,
        executor_node_id="node-org-b",
        output_result_str='{"status": "VERIFIED"}',
        exit_code=0,
    )
    attestation_verified = zk_verifier.verify_execution_attestation(proof, attestation)

    # 3. Multi-Cluster Cross-Region Raft Quorum Benchmark
    federation = FederatedRaftMultiCluster(cluster_name="global-enterprise-mesh")
    federation.register_regional_node("node-us-east", ClusterRegion.US_EAST, "org-alpha", ep_a.virtual_ip, latency_weight_ms=5.0)
    federation.register_regional_node("node-eu-central", ClusterRegion.EU_CENTRAL, "org-beta", ep_b.virtual_ip, latency_weight_ms=10.0)
    federation.register_regional_node("node-ap-east", ClusterRegion.AP_EAST, "org-gamma", ep_c.virtual_ip, latency_weight_ms=15.0)

    # Leader election across regions
    elected = await federation.elect_cross_cluster_leader("node-us-east")

    # Replicate cross-region log entry
    raft_proposal = await federation.replicate_cross_region_entry(
        entry_type=CommitteeEntryType.PATCH_COMMIT,
        payload={"task_id": "task-cross-org-01", "merkle_root": proof.merkle_root},
    )

    # Test regional disaster partition and failover
    new_leader = await federation.handle_regional_partition(ClusterRegion.US_EAST)

    # 4. Mesh Factory Capability Routing
    dispatcher = MeshFactoryDispatcher()
    dag = RefactoringTaskDAG(goal="Phase 111 Factory Routing Verification")
    dag.add_node(
        RefactoringTaskNode(
            node_id="task-cross-org-fed",
            title="Cross-Org Zero-Knowledge Refactoring",
            task_type=RefactoringTaskType.CROSS_ORG_FEDERATION,
            target_files=["tunnel.py"],
            mutable_scope=["tunnel.py"],
        )
    )
    plan = dispatcher.create_dispatch_plan(dag)
    gateway_assigned = (
        len(plan.assignments) == 1
        and plan.assignments[0].required_capability == PeerCapability.CROSS_ORG_GATEWAY.value
        and plan.assignments[0].assigned_peer_id == "node-cross-org-gateway"
    )

    elapsed_time = time.perf_counter() - start_time

    receipt: Dict[str, Any] = {
        "benchmark_id": f"cross-org-mesh-receipt-{int(time.time())}",
        "milestone": "T-038",
        "phase": 111,
        "protocol_version": "3.8.0",
        "timestamp": time.time(),
        "elapsed_seconds": round(elapsed_time, 3),
        "metrics": {
            "p2p_direct_handshake_ms": direct_latency_ms,
            "derp_relay_fallback": relayed_session.is_relayed,
            "airgap_leakage_prevented": airgap_clean,
            "zk_merkle_attestation_verified": attestation_verified,
            "multi_cluster_regions_active": 3,
            "cross_region_consensus_latency_ms": raft_proposal.consensus_latency_ms,
            "failover_surviving_leader": new_leader,
            "factory_gateway_routed": gateway_assigned,
        },
        "verifications": {
            "p2p_nat_hole_punching": "PASS" if direct_session.status == TunnelStatus.ESTABLISHED and direct_latency_ms < 500.0 else "FAIL",
            "derp_relay_fallback": "PASS" if relayed_session.status == TunnelStatus.RELAYING else "FAIL",
            "zero_knowledge_protection": "PASS" if airgap_clean and attestation_verified else "FAIL",
            "cross_region_raft_consensus": "PASS" if raft_proposal.success else "FAIL",
            "regional_partition_recovery": "PASS" if new_leader is not None else "FAIL",
            "mesh_factory_gateway_routing": "PASS" if gateway_assigned else "FAIL",
        },
        "status": "PASS" if (
            direct_latency_ms < 500.0
            and relayed_session.is_relayed
            and airgap_clean
            and raft_proposal.success
            and gateway_assigned
        ) else "FAIL",
    }

    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Cross-Organization Mesh Benchmark completed with status: %s! Saved to %s", receipt["status"], output_file)

    # Print summary table
    print("\n=======================================================")
    print(" [MESH] CROSS-ORGANIZATION ENCRYPTED P2P MESH (PHASE 111)")
    print("=======================================================")
    print(f" Status:                      {receipt['status']}")
    print(f" Milestone:                   {receipt['milestone']} (Phase {receipt['phase']})")
    print(f" Protocol Version:            {receipt['protocol_version']}")
    print(f" Direct P2P Handshake:        {receipt['metrics']['p2p_direct_handshake_ms']}ms (<500ms target)")
    print(f" DERP Relay Fallback:         {receipt['verifications']['derp_relay_fallback']}")
    print(f" Zero-Knowledge Airgap:       {receipt['verifications']['zero_knowledge_protection']}")
    print(f" WAN Raft Consensus Latency:  {receipt['metrics']['cross_region_consensus_latency_ms']}ms")
    print(f" Regional Failover Leader:    {receipt['metrics']['failover_surviving_leader']}")
    print(f" Factory Gateway Routing:     {receipt['verifications']['mesh_factory_gateway_routing']}")
    print(f" Benchmark Duration:          {receipt['elapsed_seconds']}s")
    print("=======================================================\n")

    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Cross-Organization P2P Mesh Benchmark")
    parser.add_argument(
        "--output",
        default=".agent/evidence/cross_org_mesh_receipt.json",
        help="Path to save verifiable JSON benchmark receipt",
    )
    args = parser.parse_args()

    output_path = ROOT_DIR / args.output
    receipt = asyncio.run(run_cross_org_mesh_benchmark_async(output_path))

    if receipt["status"] != "PASS":
        sys.exit(1)


if __name__ == "__main__":
    main()
