"""Comprehensive Test Suite for Phase 91: Chaos Fault Injection, Autonomous Self-Healing & Cluster Demo.

Validates:
1. MeshChaosManager rule creation, expiration, and traffic evaluation.
2. Network partition, latency spike, and node isolation injection helpers.
3. Raft RPC interception and split-brain election under network partitions.
4. Partition healing and old leader step-down upon receiving higher-term heartbeat.
5. Self-healing diagnostic symptom extraction and vector memory precedent lookup.
6. Auto-rollback engine restoring worktree cleanliness in isolated worktree.
7. Auto-rollback safety guard protecting primary repository against destructive reset/clean.
8. MultiWorkerCluster end-to-end 7-stage demonstration execution.
9. FastAPI REST endpoints for /v1/mesh/chaos/* and /v1/mesh/cluster/demo.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from agent_workspace.core.chaos import (
    ChaosFaultRule,
    ChaosFaultType,
    MeshChaosManager,
)
from agent_workspace.core.cluster_demo import (
    ClusterDemoReceipt,
    MultiWorkerCluster,
)
from agent_workspace.core.federated_mesh import (
    FederatedMeshCoordinator,
    PeerCapability,
)
from agent_workspace.core.pipeline.models import (
    CodingPipelineResult,
    CodingTaskRequest,
    PipelineStage,
    RollbackReceipt,
    ScopedMutationPlan,
    SelfHealingAttemptReceipt,
    VerificationReceipt,
    VerificationStatus,
    WorktreeSessionConfig,
)
from agent_workspace.core.pipeline.self_healing import PipelineSelfHealingEngine
from agent_workspace.core.raft_consensus import (
    AppendEntriesArgs,
    CommitteeEntryType,
    CommitteeRaftNode,
    RaftRole,
)
from agent_workspace.core.vector_memory import (
    FederatedVectorMemory,
    VectorCategory,
)
from agent_workspace.routes.mesh import router


class TestChaosSelfHealingP91(unittest.TestCase):
    """Test suite for Phase 91 Federated Chaos, Self-Healing, and Cluster Demo."""

    def setUp(self) -> None:
        self.chaos_mgr = MeshChaosManager.get_instance()
        self.chaos_mgr.clear_all_faults()

    def tearDown(self) -> None:
        self.chaos_mgr.clear_all_faults()

    # ---------------------------------------------------------------------
    # 1. Chaos Manager Rule Lifecycle & Traffic Evaluation
    # ---------------------------------------------------------------------
    def test_chaos_manager_rule_lifecycle(self) -> None:
        rule = self.chaos_mgr.inject_fault(
            fault_type=ChaosFaultType.LATENCY_SPIKE,
            source_node_ids=["node-1"],
            target_node_ids=["node-2"],
            latency_ms=150.0,
            duration_seconds=30.0,
        )
        self.assertIsNotNone(rule.rule_id)
        self.assertEqual(rule.fault_type, ChaosFaultType.LATENCY_SPIKE)
        self.assertEqual(rule.latency_ms, 150.0)

        active = self.chaos_mgr.list_active_faults()
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0].rule_id, rule.rule_id)

        # Expiration check
        self.assertFalse(rule.is_expired(current_time=time.time()))
        self.assertTrue(rule.is_expired(current_time=time.time() + 100.0))

        # Clear individual fault
        cleared = self.chaos_mgr.clear_fault(rule.rule_id)
        self.assertTrue(cleared)
        self.assertEqual(len(self.chaos_mgr.list_active_faults()), 0)

    def test_chaos_traffic_evaluation(self) -> None:
        # Ingress drop between node-1 and node-2
        self.chaos_mgr.inject_fault(
            fault_type=ChaosFaultType.PACKET_DROP,
            source_node_ids=["node-1"],
            target_node_ids=["node-2"],
            probability=1.0,
        )

        is_drop, delay_drop, _ = self.chaos_mgr.evaluate_traffic("node-1", "node-2")
        self.assertTrue(is_drop)

        # Traffic from node-1 to node-3 should be nominal
        is_pass, delay_pass, _ = self.chaos_mgr.evaluate_traffic("node-1", "node-3")
        self.assertFalse(is_pass)
        self.assertEqual(delay_pass, 0.0)

        # Latency spike
        self.chaos_mgr.inject_fault(
            fault_type=ChaosFaultType.LATENCY_SPIKE,
            source_node_ids=["node-1"],
            target_node_ids=["node-3"],
            latency_ms=250.0,
            probability=1.0,
        )
        is_lat, delay_lat, _ = self.chaos_mgr.evaluate_traffic("node-1", "node-3")
        self.assertFalse(is_lat)
        self.assertEqual(delay_lat, 250.0)

    def test_chaos_partition_and_isolation_helpers(self) -> None:
        rules = self.chaos_mgr.create_partition(["node-a", "node-b"], ["node-c", "node-d"], duration_seconds=60.0)
        self.assertEqual(len(rules), 2)
        active = self.chaos_mgr.list_active_faults()
        self.assertEqual(len(active), 2)

        # Traffic across partition is dropped
        is_cross, _, _ = self.chaos_mgr.evaluate_traffic("node-a", "node-c")
        self.assertTrue(is_cross)
        is_cross2, _, _ = self.chaos_mgr.evaluate_traffic("node-d", "node-b")
        self.assertTrue(is_cross2)
        # Traffic within partition A is nominal
        is_intra, _, _ = self.chaos_mgr.evaluate_traffic("node-a", "node-b")
        self.assertFalse(is_intra)

        # Node isolation
        self.chaos_mgr.clear_all_faults()
        iso_rule_id = self.chaos_mgr.isolate_node("node-isolated", duration_seconds=60.0)
        self.assertTrue(iso_rule_id.startswith("chaos-"))
        is_iso1, _, _ = self.chaos_mgr.evaluate_traffic("node-isolated", "any-peer")
        self.assertTrue(is_iso1)
        is_iso2, _, _ = self.chaos_mgr.evaluate_traffic("any-peer", "node-isolated")
        self.assertTrue(is_iso2)

    # ---------------------------------------------------------------------
    # 2. Raft RPC Interception & Split-Brain Network Partition
    # ---------------------------------------------------------------------
    def test_raft_rpc_chaos_interception(self) -> None:
        raft_a = CommitteeRaftNode("node-a", peers_provider=lambda: ["node-b"], chaos_manager=self.chaos_mgr)
        raft_b = CommitteeRaftNode("node-b", peers_provider=lambda: ["node-a"], chaos_manager=self.chaos_mgr)

        # Wire direct RPC
        raft_a.rpc_dispatcher = lambda p, m, data: raft_b.handle_append_entries(AppendEntriesArgs(**data)).model_dump()

        # Nominal AppendEntries
        reply = raft_a._send_append_entries(
            "node-b",
            AppendEntriesArgs(term=1, leader_id="node-a", prev_log_index=0, prev_log_term=0, entries=[], leader_commit=0),
        )
        self.assertIsNotNone(reply)
        self.assertTrue(reply.success)

        # Inject packet drop
        self.chaos_mgr.inject_fault(
            fault_type=ChaosFaultType.PACKET_DROP,
            source_node_ids=["node-a"],
            target_node_ids=["node-b"],
            probability=1.0,
        )
        # Should be dropped by chaos interceptor
        reply_blocked = raft_a._send_append_entries(
            "node-b",
            AppendEntriesArgs(term=1, leader_id="node-a", prev_log_index=0, prev_log_term=0, entries=[], leader_commit=0),
        )
        self.assertIsNone(reply_blocked)

    def test_raft_split_brain_election_and_partition_heal(self) -> None:
        """3-node cluster: Node 1 leader; partition isolates Node 1; {Node 2, Node 3} elects Node 2; heal steps down Node 1."""
        node1 = CommitteeRaftNode("n1", peers_provider=lambda: ["n2", "n3"], chaos_manager=self.chaos_mgr)
        node2 = CommitteeRaftNode("n2", peers_provider=lambda: ["n1", "n3"], chaos_manager=self.chaos_mgr)
        node3 = CommitteeRaftNode("n3", peers_provider=lambda: ["n1", "n2"], chaos_manager=self.chaos_mgr)
        nodes = {"n1": node1, "n2": node2, "n3": node3}

        # Wire RPC
        for nid, rnode in nodes.items():
            def make_dispatcher(src_id):
                def dispatcher(target_peer, method, payload):
                    target = nodes.get(target_peer)
                    if method == "request_vote":
                        from agent_workspace.core.raft_consensus import RequestVoteArgs
                        return target.handle_request_vote(RequestVoteArgs(**payload)).model_dump()
                    elif method == "append_entries":
                        return target.handle_append_entries(AppendEntriesArgs(**payload)).model_dump()
                    raise ValueError(method)
                return dispatcher
            rnode.rpc_dispatcher = make_dispatcher(nid)

        # Step 1: Node 1 elects itself
        won1 = node1.start_election()
        self.assertTrue(won1)
        self.assertEqual(node1.role, RaftRole.LEADER)
        self.assertEqual(node1.current_term, 1)

        # Step 2: Inject partition isolating Node 1: {n1} vs {n2, n3}
        self.chaos_mgr.create_partition(["n1"], ["n2", "n3"])

        # Node 1 fails to commit without quorum
        ok1, _, _ = node1.propose_entry(CommitteeEntryType.SPEECH_TURN, {"text": "uncommitted"}, "n1")
        self.assertFalse(ok1)

        # Majority partition {n2, n3} elects Node 2
        won2 = node2.start_election()
        self.assertTrue(won2)
        self.assertEqual(node2.role, RaftRole.LEADER)
        self.assertEqual(node2.current_term, 2)

        # Node 2 commits entry in majority partition
        ok2, entry2, _ = node2.propose_entry(CommitteeEntryType.SPEECH_TURN, {"text": "majority commit"}, "n2")
        self.assertTrue(ok2)
        self.assertGreaterEqual(node2.commit_index, entry2.index)

        # Step 3: Heal partition
        self.chaos_mgr.clear_all_faults()

        # Node 2 sends heartbeat to Node 1
        hb_reply = node2._send_append_entries(
            "n1",
            AppendEntriesArgs(
                term=node2.current_term,
                leader_id=node2.node_id,
                prev_log_index=node2.last_log_index - 1,
                prev_log_term=node2.log[-2].term if len(node2.log) > 1 else 0,
                entries=[node2.log[-1]],
                leader_commit=node2.commit_index,
            ),
        )
        self.assertIsNotNone(hb_reply)
        self.assertTrue(hb_reply.success)

        # Verify Node 1 stepped down and adopted Node 2's term
        self.assertEqual(node1.role, RaftRole.FOLLOWER)
        self.assertEqual(node1.current_term, 2)
        self.assertEqual(node1.leader_id, "n2")

    # ---------------------------------------------------------------------
    # 3. Self-Healing Diagnostics & Precedent Lookup
    # ---------------------------------------------------------------------
    def test_self_healing_diagnostic_extraction(self) -> None:
        vmem = FederatedVectorMemory("test-heal-node")
        vmem.store(
            task_id="TASK-PREV-01",
            category=VectorCategory.DECISION,
            content="Always sanitize token headers in auth handler to prevent header token leaks in unit test assertions",
            metadata={"tags": ["auth", "token_leak", "security"]},
        )

        healing_engine = PipelineSelfHealingEngine(vector_memory=vmem)
        fake_failed_receipt = VerificationReceipt(
            step_name="pytest test_auth.py",
            command="pytest test_auth.py",
            exit_code=1,
            status=VerificationStatus.FAIL,
            stdout_snippet="FAILED test_auth.py::test_login - AssertionError: token_leak detected",
            stderr_snippet="Traceback (most recent call last):\nAssertionError: token_leak detected at auth.py:42",
            duration_ms=85,
        )

        fake_session = WorktreeSessionConfig(
            session_id="session-test",
            worktree_path=os.getcwd(),
            branch_name="feat/test",
            base_commit="HEAD",
            is_isolated=True,
        )

        attempt = healing_engine.attempt_self_healing(
            task_id="TASK-NEW-02",
            worktree_session=fake_session,
            plan=ScopedMutationPlan(
                task_id="TASK-NEW-02",
                plan_summary="Update auth token parsing",
                assigned_role="DOMAIN_LOGIC_AGENT",
                target_files=["src/auth.py"],
                structural_diff_preview="--- a/auth.py\n+++ b/auth.py",
                test_strategy=["pytest test_auth.py"],
            ),
            failed_receipts=[fake_failed_receipt],
            attempt_index=1,
        )

        self.assertEqual(attempt.attempt_index, 1)
        self.assertTrue(any("AssertionError" in diag for diag in attempt.diagnostic_evidence))
        self.assertTrue(len(attempt.corrective_action) > 0)

    # ---------------------------------------------------------------------
    # 4. Auto-Rollback Engine: Isolated Worktree vs Primary Repo Guard
    # ---------------------------------------------------------------------
    def test_auto_rollback_in_isolated_temp_worktree(self) -> None:
        with tempfile.TemporaryDirectory(prefix="las_test_rollback_") as tmp_dir:
            # Init mock git worktree
            subprocess.run(["git", "init"], cwd=tmp_dir, capture_output=True, check=True)
            subprocess.run(["git", "config", "user.name", "Tester"], cwd=tmp_dir, capture_output=True, check=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_dir, capture_output=True, check=True)
            base_file = Path(tmp_dir) / "baseline.txt"
            base_file.write_text("v1.0 baseline", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=tmp_dir, capture_output=True, check=True)
            subprocess.run(["git", "commit", "-m", "Baseline commit"], cwd=tmp_dir, capture_output=True, check=True)
            base_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=tmp_dir, capture_output=True, text=True, check=True).stdout.strip()

            # Pollute worktree with modified file and untracked file
            base_file.write_text("v2.0 corrupted", encoding="utf-8")
            untracked = Path(tmp_dir) / "temp_leak.tmp"
            untracked.write_text("untracked leak", encoding="utf-8")

            session = WorktreeSessionConfig(
                session_id="session-isolated",
                worktree_path=tmp_dir,
                branch_name="feat/rollback-test",
                base_commit=base_sha,
                is_isolated=True,
            )

            engine = PipelineSelfHealingEngine()
            receipt = engine.execute_auto_rollback(
                task_id="TASK-ROLLBACK-TEST",
                worktree_session=session,
                teardown_worktree=False,
            )

            self.assertEqual(receipt.restoration_status, "PRISTINE_ROLLBACK")
            self.assertTrue(receipt.canonical_clean)
            self.assertIn("temp_leak.tmp", receipt.untracked_files_purged)
            self.assertEqual(base_file.read_text(encoding="utf-8"), "v1.0 baseline")
            self.assertFalse(untracked.exists())

    def test_auto_rollback_primary_repo_safety_guard(self) -> None:
        """Verifies that execute_auto_rollback refuses to touch the main repository root."""
        repo_root = str(Path(".").resolve())
        session = WorktreeSessionConfig(
            session_id="session-root-danger",
            worktree_path=repo_root,
            branch_name="main",
            base_commit="HEAD",
            is_isolated=False,
        )

        engine = PipelineSelfHealingEngine()
        receipt = engine.execute_auto_rollback(
            task_id="TASK-DANGER-TEST",
            worktree_session=session,
            teardown_worktree=False,
        )

        self.assertEqual(receipt.restoration_status, "PRIMARY_REPO_PROTECTED")
        self.assertFalse(receipt.canonical_clean)
        self.assertEqual(len(receipt.untracked_files_purged), 0)

    def test_async_self_healing_and_rollback(self) -> None:
        """Verifies asynchronous wrappers for self-healing iteration and rollback."""
        async def _run():
            with tempfile.TemporaryDirectory(prefix="las_test_async_healing_") as tmp_dir:
                subprocess.run(["git", "init"], cwd=tmp_dir, capture_output=True, check=True)
                subprocess.run(["git", "config", "user.name", "Tester"], cwd=tmp_dir, capture_output=True, check=True)
                subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_dir, capture_output=True, check=True)
                base_file = Path(tmp_dir) / "baseline.txt"
                base_file.write_text("v1.0 baseline", encoding="utf-8")
                subprocess.run(["git", "add", "."], cwd=tmp_dir, capture_output=True, check=True)
                subprocess.run(["git", "commit", "-m", "Init"], cwd=tmp_dir, capture_output=True, check=True)
                base_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=tmp_dir, capture_output=True, text=True, check=True).stdout.strip()

                # Pollute worktree
                base_file.write_text("v2.0 corrupted", encoding="utf-8")
                untracked = Path(tmp_dir) / "async_leak.tmp"
                untracked.write_text("leak", encoding="utf-8")

                session = WorktreeSessionConfig(
                    session_id="session-async-healing",
                    worktree_path=tmp_dir,
                    branch_name="feat/async-healing",
                    base_commit=base_sha,
                    is_isolated=True,
                )

                engine = PipelineSelfHealingEngine()

                # Test async rollback
                receipt = await engine.execute_auto_rollback_async(
                    task_id="TASK-ASYNC-ROLLBACK",
                    worktree_session=session,
                    teardown_worktree=False,
                )
                self.assertEqual(receipt.restoration_status, "PRISTINE_ROLLBACK")
                self.assertTrue(receipt.canonical_clean)
                self.assertIn("async_leak.tmp", receipt.untracked_files_purged)
                self.assertFalse(untracked.exists())

                # Test async self-healing attempt
                fake_failed_receipt = VerificationReceipt(
                    step_name="pytest test_async.py",
                    command="pytest test_async.py",
                    status=VerificationStatus.FAIL,
                    exit_code=1,
                    stderr_snippet="AssertionError: 1 != 2",
                    duration_ms=50.0,
                )
                attempt = await engine.attempt_self_healing_async(
                    task_id="TASK-ASYNC-HEAL",
                    worktree_session=session,
                    plan=ScopedMutationPlan(
                        task_id="TASK-ASYNC-HEAL",
                        plan_summary="Async healing patch",
                        assigned_role="DOMAIN_LOGIC_AGENT",
                        target_files=["src/async.py"],
                        test_strategy=["pytest test_async.py"],
                    ),
                    failed_receipts=[fake_failed_receipt],
                    attempt_index=1,
                )
                self.assertEqual(attempt.attempt_index, 1)
                self.assertTrue(any("AssertionError" in diag for diag in attempt.diagnostic_evidence))

        asyncio.run(_run())

    # ---------------------------------------------------------------------
    # 5. MultiWorkerCluster End-to-End Demonstration
    # ---------------------------------------------------------------------
    def test_multi_worker_cluster_full_demo(self) -> None:
        cluster = MultiWorkerCluster()
        receipt = cluster.run_full_demo()

        self.assertIsInstance(receipt, ClusterDemoReceipt)
        self.assertTrue(receipt.success)
        self.assertEqual(receipt.total_steps, 7)
        self.assertEqual(receipt.passed_steps, 7)
        self.assertGreater(receipt.duration_total_ms, 0.0)
        self.assertEqual(len(receipt.step_receipts), 7)
        for s in receipt.step_receipts:
            self.assertEqual(s.status, "PASS")

    # ---------------------------------------------------------------------
    # 6. REST API Endpoints for Chaos & Cluster Demo
    # ---------------------------------------------------------------------
    def test_mesh_routes_chaos_and_cluster(self) -> None:
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        # GET active faults
        r_get = client.get("/v1/mesh/chaos/faults")
        self.assertEqual(r_get.status_code, 200)
        data_get = r_get.json()
        self.assertIn("faults", data_get)

        # POST inject fault
        r_inject = client.post(
            "/v1/mesh/chaos/inject",
            json={
                "fault_type": "LATENCY_SPIKE",
                "source_node_ids": ["client-test-1"],
                "target_node_ids": ["client-test-2"],
                "latency_ms": 300.0,
                "duration_seconds": 45.0,
                "description": "API Test Spike",
            },
        )
        self.assertEqual(r_inject.status_code, 200)
        data_inj = r_inject.json()
        self.assertEqual(data_inj["status"], "injected")
        rule_id = data_inj["rule"]["rule_id"]

        # POST clear specific fault
        r_clear = client.post("/v1/mesh/chaos/clear", json={"rule_id": rule_id})
        self.assertEqual(r_clear.status_code, 200)
        self.assertEqual(r_clear.json()["status"], "cleared")

        # POST run cluster demo
        r_demo = client.post("/v1/mesh/cluster/demo")
        self.assertEqual(r_demo.status_code, 200)
        demo_data = r_demo.json()
        self.assertTrue(demo_data["success"])
        self.assertEqual(demo_data["passed_steps"], 7)


if __name__ == "__main__":
    unittest.main()
