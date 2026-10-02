"""
LAS Multi-Worker Cluster Demonstration Engine (Phase 91).
Aligned with ADR-005, ADR-006, and Protocol v3.8.0.

Orchestrates an end-to-end, reproducible 3-node federated cluster demonstration:
  1. Setup 3 nodes (Leader/Cockpit, Reasoning Worker, Test Runner) with Zero-Trust mTLS attestation.
  2. Elect Raft consensus leader with verified quorum (3/3).
  3. Replicate federated vector memory and verify O(1) Merkle root convergence.
  4. Inject Chaos network partition isolating the leader.
  5. Demonstrate split-brain resilience: majority partition (2/3) elects new leader.
  6. Heal partition: old leader steps down upon receiving higher-term heartbeat.
  7. Run autonomous self-healing loop with diagnostic recovery and verify auto-rollback.
"""

from __future__ import annotations

import logging
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from agent_workspace.core.chaos import ChaosFaultType, MeshChaosManager
from agent_workspace.core.federated_mesh import (
    AttestationStatus,
    FederatedMeshCoordinator,
    PeerCapability,
)
from agent_workspace.core.pipeline.models import (
    RollbackReceipt,
    ScopedMutationPlan,
    SelfHealingAttemptReceipt,
    VerificationReceipt,
    VerificationStatus,
    WorktreeSessionConfig,
)
from agent_workspace.core.pipeline.self_healing import PipelineSelfHealingEngine
from agent_workspace.core.raft_consensus import (
    CommitteeEntryType,
    CommitteeRaftNode,
    RaftRole,
)
from agent_workspace.core.vector_memory import VectorCategory

logger = logging.getLogger("MultiWorkerClusterDemo")


class ClusterDemoStepReceipt(BaseModel):
    """Receipt for an individual phase within the cluster demo."""
    model_config = ConfigDict(extra="forbid")

    step_name: str
    status: str  # PASS, FAIL
    duration_ms: float
    details: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ClusterDemoReceipt(BaseModel):
    """Overall execution receipt of the multi-worker cluster demonstration."""
    model_config = ConfigDict(extra="forbid")

    demo_id: str
    nodes_participating: List[str]
    total_steps: int
    passed_steps: int
    success: bool
    duration_total_ms: float
    step_receipts: List[ClusterDemoStepReceipt]
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class MultiWorkerCluster:
    """
    Simulates a 3-node decentralized federated mesh in-process with real
    cryptographic mTLS certificates, Raft consensus, vector memory, and chaos faults.
    """

    def __init__(self):
        self.chaos_manager = MeshChaosManager.get_instance()
        self.chaos_manager.clear_all_faults()

        # Node 1: Leader / Cockpit Coordinator
        self.node1 = FederatedMeshCoordinator(
            node_id="cluster-node-1",
            role="cockpit_leader",
            host="127.0.0.1",
            port=8000,
            strict_attestation=True,
        )

        # Node 2: Reasoning Specialist Worker
        self.node2 = FederatedMeshCoordinator(
            node_id="cluster-node-2",
            role="reasoning_worker",
            host="127.0.0.1",
            port=8001,
            strict_attestation=True,
        )

        # Node 3: Test Verification Runner Worker
        self.node3 = FederatedMeshCoordinator(
            node_id="cluster-node-3",
            role="test_runner",
            host="127.0.0.1",
            port=8002,
            strict_attestation=True,
        )

        self.nodes = {
            "cluster-node-1": self.node1,
            "cluster-node-2": self.node2,
            "cluster-node-3": self.node3,
        }

        # Wire direct in-process RPC dispatchers between nodes
        self._wire_raft_rpc_dispatchers()

    def _wire_raft_rpc_dispatchers(self) -> None:
        """Sets up in-process RPC message routing for Raft consensus."""
        for src_id, src_coord in self.nodes.items():
            raft_node = src_coord.raft_node

            def make_dispatcher(source_coord):
                def dispatcher(target_peer_id: str, method: str, payload: dict) -> dict:
                    target_coord = self.nodes.get(target_peer_id)
                    if not target_coord:
                        raise RuntimeError(f"Peer {target_peer_id} not found in cluster")

                    if method == "request_vote":
                        from agent_workspace.core.raft_consensus import RequestVoteArgs
                        args = RequestVoteArgs(**payload)
                        reply = target_coord.handle_raft_vote(args)
                        return reply.model_dump()
                    elif method == "append_entries":
                        from agent_workspace.core.raft_consensus import AppendEntriesArgs
                        args = AppendEntriesArgs(**payload)
                        reply = target_coord.handle_raft_append_entries(args)
                        return reply.model_dump()
                    else:
                        raise ValueError(f"Unknown RPC method: {method}")

                return dispatcher

            raft_node.rpc_dispatcher = make_dispatcher(src_coord)

    def run_full_demo(self) -> ClusterDemoReceipt:
        """Executes the complete 6-stage battle-tested cluster demonstration."""
        demo_id = f"demo-{int(time.time())}"
        step_receipts: List[ClusterDemoStepReceipt] = []
        start_all = time.perf_counter()

        try:
            # -------------------------------------------------------------
            # Stage 1: Mutual Zero-Trust mTLS Attestation Handshake
            # -------------------------------------------------------------
            s1_start = time.perf_counter()
            # Register peer profiles with X.509 public certificates
            for src_id, src_coord in self.nodes.items():
                for dst_id, dst_coord in self.nodes.items():
                    if src_id != dst_id:
                        src_coord.register_peer(
                            node_id=dst_coord.node_id,
                            role=dst_coord.role,
                            host=dst_coord.host,
                            port=dst_coord.port,
                            cert_pem=dst_coord.cert_pem,
                            attestation_status=AttestationStatus.PENDING,
                        )

            # Perform cryptographic challenge-response attestation handshakes
            for src_id, src_coord in self.nodes.items():
                for dst_id, dst_coord in self.nodes.items():
                    if src_id != dst_id:
                        chal = src_coord.generate_attestation_challenge(dst_coord.node_id)
                        proof = dst_coord.create_attestation_proof(chal)
                        ok, msg = src_coord.verify_attestation_proof(proof)
                        assert ok, f"Attestation failed from {dst_id} to {src_id}: {msg}"

            s1_duration = round((time.perf_counter() - s1_start) * 1000, 2)
            step_receipts.append(
                ClusterDemoStepReceipt(
                    step_name="1. Zero-Trust mTLS Mutual Attestation",
                    status="PASS",
                    duration_ms=s1_duration,
                    details={"attested_nodes_count": len(self.nodes)},
                )
            )

            # -------------------------------------------------------------
            # Stage 2: Raft Leader Election with Quorum
            # -------------------------------------------------------------
            s2_start = time.perf_counter()
            elected = self.node1.start_raft_election()
            assert elected, "Node 1 failed to win leader election"
            assert self.node1.raft_node.role == RaftRole.LEADER
            assert self.node2.raft_node.role == RaftRole.FOLLOWER
            assert self.node3.raft_node.role == RaftRole.FOLLOWER
            assert self.node1.raft_node.current_term == 1

            s2_duration = round((time.perf_counter() - s2_start) * 1000, 2)
            step_receipts.append(
                ClusterDemoStepReceipt(
                    step_name="2. Raft Consensus Leader Election",
                    status="PASS",
                    duration_ms=s2_duration,
                    details={
                        "leader": self.node1.node_id,
                        "term": self.node1.raft_node.current_term,
                        "quorum_size": self.node1.raft_node.get_quorum_size(),
                    },
                )
            )

            # -------------------------------------------------------------
            # Stage 3: Vector Memory Indexing & Merkle Delta Sync
            # -------------------------------------------------------------
            s3_start = time.perf_counter()
            self.node1.store_vector_memory(
                content="Architecture Rule: Domain logic must be framework-agnostic (Anti-Corruption Principle #2)",
                category="DECISION",
                task_id="TASK-P91-DEMO",
                metadata={"module": "core", "impact": "high"},
            )
            self.node1.store_vector_memory(
                content="Security Lesson: Strictly enforce late-request-wins race elimination on all IPC gates",
                category="LESSON",
                task_id="TASK-P91-DEMO",
                metadata={"module": "auth", "impact": "critical"},
            )

            # Sync entries from Node 1 to Node 2 and Node 3
            entries_payload = self.node1.vector_memory.export_entries()
            res2 = self.node2.sync_vector_memory(self.node1.node_id, entries_payload)
            res3 = self.node3.sync_vector_memory(self.node1.node_id, entries_payload)
            assert res2.get("status") == "synced"
            assert res3.get("status") == "synced"

            # Check Merkle root convergence across all 3 nodes
            root1 = self.node1.vector_memory.compute_merkle_root()
            root2 = self.node2.vector_memory.compute_merkle_root()
            root3 = self.node3.vector_memory.compute_merkle_root()
            assert root1 == root2 == root3, f"Merkle divergence: {root1} != {root2} != {root3}"

            s3_duration = round((time.perf_counter() - s3_start) * 1000, 2)
            step_receipts.append(
                ClusterDemoStepReceipt(
                    step_name="3. Federated Vector Memory Merkle Sync",
                    status="PASS",
                    duration_ms=s3_duration,
                    details={
                        "entries_count": len(self.node1.vector_memory._entries),
                        "converged_merkle_root": root1,
                    },
                )
            )

            # -------------------------------------------------------------
            # Stage 4: Chaos Network Partition (Isolating Node 1)
            # -------------------------------------------------------------
            s4_start = time.perf_counter()
            partition_rule_ids = self.chaos_manager.create_partition(
                partition_a=["cluster-node-1"],
                partition_b=["cluster-node-2", "cluster-node-3"],
                duration_seconds=60,
                description="Split-brain test: isolate Node 1 from {Node 2, Node 3}",
            )

            # Node 1 attempts to propose an entry, but replication to Node 2/3 fails due to partition
            ok, entry, msg = self.node1.propose_committee_entry(
                entry_type=CommitteeEntryType.SPEECH_TURN,
                payload={"speaker": "architect", "text": "Isolated leader attempt"},
            )
            # Quorum must NOT be achieved for isolated leader
            assert not ok, "Isolated leader unexpectedly achieved quorum commit!"

            s4_duration = round((time.perf_counter() - s4_start) * 1000, 2)
            step_receipts.append(
                ClusterDemoStepReceipt(
                    step_name="4. Chaos Network Partition Isolation",
                    status="PASS",
                    duration_ms=s4_duration,
                    details={
                        "isolated_node": "cluster-node-1",
                        "partition_rules": partition_rule_ids,
                        "uncommitted_isolated_attempt_reason": msg,
                    },
                )
            )

            # -------------------------------------------------------------
            # Stage 5: Majority Quorum Failover (Node 2 Elected Leader)
            # -------------------------------------------------------------
            s5_start = time.perf_counter()
            # Node 2 initiates election in majority partition {Node 2, Node 3}
            n2_won = self.node2.start_raft_election()
            assert n2_won, "Node 2 failed to win election in majority partition"
            assert self.node2.raft_node.role == RaftRole.LEADER
            assert self.node2.raft_node.current_term == 2
            # Node 3 voted for Node 2
            assert self.node3.raft_node.voted_for == "cluster-node-2"

            # Node 2 proposes an entry and commits it across {Node 2, Node 3} (Quorum 2/3)
            ok2, entry2, msg2 = self.node2.propose_committee_entry(
                entry_type=CommitteeEntryType.SPEECH_TURN,
                payload={"speaker": "reasoning_worker", "text": "Majority partition commit"},
            )
            assert ok2, f"Majority partition failed to commit entry: {msg2}"

            s5_duration = round((time.perf_counter() - s5_start) * 1000, 2)
            step_receipts.append(
                ClusterDemoStepReceipt(
                    step_name="5. Majority Partition Raft Leader Failover",
                    status="PASS",
                    duration_ms=s5_duration,
                    details={
                        "new_leader": self.node2.node_id,
                        "new_term": self.node2.raft_node.current_term,
                        "committed_entry_index": entry2.index,
                    },
                )
            )

            # -------------------------------------------------------------
            # Stage 6: Partition Healed & Old Leader Step-Down
            # -------------------------------------------------------------
            s6_start = time.perf_counter()
            self.chaos_manager.clear_all_faults()

            # New leader (Node 2) sends heartbeat / AppendEntries to recovered Node 1
            reply_from_node1 = self.node2.raft_node._send_append_entries(
                "cluster-node-1",
                from_args := __import__("agent_workspace.core.raft_consensus", fromlist=["AppendEntriesArgs"]).AppendEntriesArgs(
                    term=self.node2.raft_node.current_term,
                    leader_id=self.node2.node_id,
                    prev_log_index=self.node2.raft_node.last_log_index - 1,
                    prev_log_term=self.node2.raft_node.log[-2].term,
                    entries=[self.node2.raft_node.log[-1]],
                    leader_commit=self.node2.raft_node.commit_index,
                )
            )
            assert reply_from_node1 is not None and reply_from_node1.success
            # Verify Node 1 stepped down and adopted Node 2's term
            assert self.node1.raft_node.role == RaftRole.FOLLOWER
            assert self.node1.raft_node.current_term == 2
            assert self.node1.raft_node.leader_id == "cluster-node-2"

            s6_duration = round((time.perf_counter() - s6_start) * 1000, 2)
            step_receipts.append(
                ClusterDemoStepReceipt(
                    step_name="6. Partition Resolution & Leader Step-Down",
                    status="PASS",
                    duration_ms=s6_duration,
                    details={
                        "active_leader": self.node2.node_id,
                        "resumed_nodes": list(self.nodes.keys()),
                    },
                )
            )

            # -------------------------------------------------------------
            # Stage 7: Autonomous Self-Healing & Auto-Rollback Verification
            # -------------------------------------------------------------
            s7_start = time.perf_counter()
            with tempfile.TemporaryDirectory(prefix="las_demo_wt_") as tmp_wt_dir:
                # Initialize an isolated mock git worktree
                subprocess.run(["git", "init"], cwd=tmp_wt_dir, capture_output=True, check=True)
                subprocess.run(["git", "config", "user.name", "DemoCluster"], cwd=tmp_wt_dir, capture_output=True, check=True)
                subprocess.run(["git", "config", "user.email", "demo@las.mesh"], cwd=tmp_wt_dir, capture_output=True, check=True)
                dummy_file = Path(tmp_wt_dir) / "auth.py"
                dummy_file.write_text("# Initial auth implementation\n", encoding="utf-8")
                subprocess.run(["git", "add", "."], cwd=tmp_wt_dir, capture_output=True, check=True)
                subprocess.run(["git", "commit", "-m", "Initial baseline commit"], cwd=tmp_wt_dir, capture_output=True, check=True)
                base_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=tmp_wt_dir, capture_output=True, text=True, check=True).stdout.strip()

                # Simulate dirty mutation & untracked artifacts to verify rollback
                dummy_file.write_text("# Broken mutation causing failure\n", encoding="utf-8")
                (Path(tmp_wt_dir) / "untracked_leak.tmp").write_text("untracked leak", encoding="utf-8")

                fake_session = WorktreeSessionConfig(
                    session_id="wt_demo_test",
                    worktree_path=tmp_wt_dir,
                    branch_name="feat/demo-rollback",
                    base_commit=base_sha,
                    is_isolated=True,
                )
                healing_engine = PipelineSelfHealingEngine(
                    vector_memory=self.node2.vector_memory,
                )

                # Simulate a failed receipt
                fake_failed_receipt = VerificationReceipt(
                    step_name="Step 1: pytest test_auth.py",
                    command="pytest test_auth.py",
                    exit_code=1,
                    status=VerificationStatus.FAIL,
                    stdout_snippet="AssertionError: token_leak detected",
                    stderr_snippet="Traceback: line 42",
                    duration_ms=120,
                )

                # Run attempt_self_healing
                healing_attempt = healing_engine.attempt_self_healing(
                    task_id="TASK-DEMO-HEAL",
                    worktree_session=fake_session,
                    plan=ScopedMutationPlan(
                        task_id="TASK-DEMO-HEAL",
                        plan_summary="Demo self-healing plan",
                        assigned_role="DOMAIN_LOGIC_AGENT",
                        target_files=["src/auth.py"],
                        structural_diff_preview="--- a/src/auth.py\n+++ b/src/auth.py\n",
                        test_strategy=["echo 'test'"],
                    ),
                    failed_receipts=[fake_failed_receipt],
                    attempt_index=1,
                )
                assert healing_attempt.attempt_index == 1
                assert len(healing_attempt.diagnostic_evidence) > 0

                # Execute auto-rollback and verify pristine status
                rollback_receipt = healing_engine.execute_auto_rollback(
                    task_id="TASK-DEMO-HEAL",
                    worktree_session=fake_session,
                    teardown_worktree=False,
                )
                assert rollback_receipt.restoration_status == "PRISTINE_ROLLBACK"
                assert rollback_receipt.canonical_clean is True
                assert "untracked_leak.tmp" in rollback_receipt.untracked_files_purged

                s7_duration = round((time.perf_counter() - s7_start) * 1000, 2)
                step_receipts.append(
                    ClusterDemoStepReceipt(
                        step_name="7. Autonomous Self-Healing & Auto-Rollback Engine",
                        status="PASS",
                        duration_ms=s7_duration,
                        details={
                            "diagnostics_extracted": healing_attempt.diagnostic_evidence,
                            "precedents_found": len(healing_attempt.memory_precedents_used),
                            "rollback_status": rollback_receipt.restoration_status,
                            "untracked_purged": rollback_receipt.untracked_files_purged,
                        },
                    )
                )

            duration_total = round((time.perf_counter() - start_all) * 1000, 2)
            return ClusterDemoReceipt(
                demo_id=demo_id,
                nodes_participating=list(self.nodes.keys()),
                total_steps=len(step_receipts),
                passed_steps=len([s for s in step_receipts if s.status == "PASS"]),
                success=True,
                duration_total_ms=duration_total,
                step_receipts=step_receipts,
            )

        finally:
            self.chaos_manager.clear_all_faults()
