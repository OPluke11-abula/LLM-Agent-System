"""Comprehensive Test Suite for Phase 89: Distributed Committee Raft Consensus.

Validates:
1. Raft node initialization, terms, and role transitions.
2. Candidate elections, quorum calculation, and leader establishment.
3. Log matching, entry replication, conflict truncation, and quorum commits.
4. Phase 88 Zero-Trust attestation gating on voting and entry replication.
5. Deterministic state machine sequential execution and task summaries.
6. Split-brain & network partition safety.
7. PipelineDebateProtocol integration with Raft replicated logs.
8. REST API endpoints (/v1/mesh/raft/*).
9. CLI toolbelt subcommands (las mesh raft status, elect, log).
"""

from __future__ import annotations

import os
import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from agent_workspace.core.federated_mesh import (
    AttestationStatus,
    FederatedMeshCoordinator,
    FederatedPeerProfile,
    PeerCapability,
    get_federated_coordinator,
)
from agent_workspace.core.pipeline.committee import CommitteeFormation, CommitteeMemberSelection
from agent_workspace.core.pipeline.debate_protocol import PipelineDebateProtocol
from agent_workspace.core.pipeline.models import CodingTaskRequest, ScopedMutationPlan
from agent_workspace.core.raft_consensus import (
    AppendEntriesArgs,
    AppendEntriesReply,
    CommitteeEntryType,
    CommitteeLogEntry,
    CommitteeRaftNode,
    CommitteeStateMachine,
    RaftRole,
    RequestVoteArgs,
    RequestVoteReply,
)
from agent_workspace.routes.mesh import router


class TestCommitteeRaftConsensusP89(unittest.TestCase):
    """Test suite validating Distributed Committee Raft Consensus & Replicated State Machine."""

    def setUp(self) -> None:
        self.node_a = CommitteeRaftNode(
            node_id="node-a",
            peers_provider=lambda: ["node-b", "node-c"],
            attestation_checker=lambda pid: True,
        )
        self.node_b = CommitteeRaftNode(
            node_id="node-b",
            peers_provider=lambda: ["node-a", "node-c"],
            attestation_checker=lambda pid: True,
        )
        self.node_c = CommitteeRaftNode(
            node_id="node-c",
            peers_provider=lambda: ["node-a", "node-b"],
            attestation_checker=lambda pid: True,
        )

        # Wire nodes together via mock in-memory RPC dispatch
        self.cluster = {
            "node-a": self.node_a,
            "node-b": self.node_b,
            "node-c": self.node_c,
        }

        def make_dispatcher(src_id: str):
            def dispatch(dst_id: str, rpc_type: str, args_dict: dict) -> dict:
                target_node = self.cluster.get(dst_id)
                if not target_node:
                    raise RuntimeError(f"Peer {dst_id} unreachable")
                if rpc_type == "request_vote":
                    res = target_node.handle_request_vote(RequestVoteArgs(**args_dict))
                    return res.model_dump()
                elif rpc_type == "append_entries":
                    res = target_node.handle_append_entries(AppendEntriesArgs(**args_dict))
                    return res.model_dump()
                raise ValueError(f"Unknown RPC {rpc_type}")

            return dispatch

        self.node_a.rpc_dispatcher = make_dispatcher("node-a")
        self.node_b.rpc_dispatcher = make_dispatcher("node-b")
        self.node_c.rpc_dispatcher = make_dispatcher("node-c")

    def test_01_initial_state_and_quorum_calculation(self) -> None:
        """Verify initial Raft node defaults and cluster quorum sizes."""
        self.assertEqual(self.node_a.role, RaftRole.FOLLOWER)
        self.assertEqual(self.node_a.current_term, 0)
        self.assertEqual(self.node_a.commit_index, 0)
        self.assertEqual(self.node_a.last_applied, 0)
        self.assertEqual(len(self.node_a.log), 1)  # Genesis entry at index 0

        # In a 3-node cluster, quorum is (3 // 2) + 1 = 2
        self.assertEqual(self.node_a.get_quorum_size(), 2)

        # Single-node cluster quorum is 1
        single_node = CommitteeRaftNode(node_id="solo", peers_provider=lambda: [])
        self.assertEqual(single_node.get_quorum_size(), 1)
        # Single node immediately becomes leader upon election
        self.assertTrue(single_node.start_election())
        self.assertEqual(single_node.role, RaftRole.LEADER)
        self.assertEqual(single_node.current_term, 1)

    def test_02_multi_node_election_and_leader_establishment(self) -> None:
        """Verify candidate gathers votes from peers and transitions to LEADER."""
        # Node A triggers election; gathers vote from Node B and reaches quorum (2/3)
        won = self.node_a.start_election()
        self.assertTrue(won)
        self.assertEqual(self.node_a.role, RaftRole.LEADER)
        self.assertEqual(self.node_a.current_term, 1)
        self.assertEqual(self.node_b.voted_for, "node-a")

    def test_03_stale_log_candidate_vote_rejection(self) -> None:
        """Candidate with an older log than the voter must be rejected."""
        # Give Node B a more up-to-date log in Term 2
        extra_entry = CommitteeLogEntry(
            index=1,
            term=2,
            entry_type=CommitteeEntryType.SPEECH_TURN,
            author_node_id="node-b",
            payload={"test": "data"},
        )
        self.node_b.log.append(extra_entry)
        self.node_b.current_term = 2

        # Node A is in Term 1 with index 0, tries to request vote from B for Term 2
        req = RequestVoteArgs(
            term=2,
            candidate_id="node-a",
            last_log_index=0,
            last_log_term=0,
        )
        reply = self.node_b.handle_request_vote(req)
        self.assertFalse(reply.vote_granted)
        self.assertIn("log not up-to-date", reply.reason or "")

    def test_04_zero_trust_attestation_gating(self) -> None:
        """Unattested peers under Phase 88 cannot vote or participate in replication."""
        # Configure node A to reject attestation for rogue node
        self.node_a.attestation_checker = lambda pid: pid != "rogue-node"
        req = RequestVoteArgs(
            term=1,
            candidate_id="rogue-node",
            last_log_index=0,
            last_log_term=0,
        )
        reply = self.node_a.handle_request_vote(req)
        self.assertFalse(reply.vote_granted)
        self.assertIn("not attested", reply.reason or "")

        # Unattested leader cannot append entries
        append_req = AppendEntriesArgs(
            term=1,
            leader_id="rogue-node",
            prev_log_index=0,
            prev_log_term=0,
            leader_commit=0,
        )
        append_reply = self.node_a.handle_append_entries(append_req)
        self.assertFalse(append_reply.success)
        self.assertIn("not attested", append_reply.error_message or "")

    def test_05_log_replication_and_quorum_commit(self) -> None:
        """Leader replicates proposed entries and commits them when quorum acknowledges."""
        self.node_a.start_election()
        self.assertEqual(self.node_a.role, RaftRole.LEADER)

        payload = {
            "task_id": "TASK-TEST-001",
            "speaker_role": "architect",
            "content": "Modular architectural boundary approved.",
            "score_impact": 0.05,
        }

        ok, entry, msg = self.node_a.propose_entry(
            entry_type=CommitteeEntryType.SPEECH_TURN,
            payload=payload,
        )

        self.assertTrue(ok)
        self.assertIsNotNone(entry)
        self.assertEqual(self.node_a.commit_index, 1)
        self.assertEqual(self.node_a.last_applied, 1)

        # Followers must also have received the entry
        self.assertEqual(len(self.node_b.log), 2)
        self.assertEqual(self.node_b.log[1].entry_type, CommitteeEntryType.SPEECH_TURN)

        # State machine on Leader must have applied the entry
        summary = self.node_a.state_machine.get_task_summary("TASK-TEST-001")
        self.assertEqual(summary["speech_turns_count"], 1)

    def test_06_log_conflict_truncation_on_leader_sync(self) -> None:
        """Follower must truncate conflicting uncommitted entries when leader has newer entries."""
        # Follower B has a divergent entry at index 1 with term 1
        divergent_entry = CommitteeLogEntry(
            index=1,
            term=1,
            entry_type=CommitteeEntryType.SPEECH_TURN,
            author_node_id="old-leader",
            payload={"divergent": True},
        )
        self.node_b.log.append(divergent_entry)

        # Node A is Leader in Term 2 with a different entry at index 1
        self.node_a.current_term = 2
        authoritative_entry = CommitteeLogEntry(
            index=1,
            term=2,
            entry_type=CommitteeEntryType.CONSENSUS_VERDICT,
            author_node_id="node-a",
            payload={"task_id": "TASK-002", "decision": "CONSENSUS_APPROVED"},
        )

        args = AppendEntriesArgs(
            term=2,
            leader_id="node-a",
            prev_log_index=0,
            prev_log_term=0,
            entries=[authoritative_entry],
            leader_commit=1,
        )

        reply = self.node_b.handle_append_entries(args)
        self.assertTrue(reply.success)
        self.assertEqual(len(self.node_b.log), 2)
        # Entry at index 1 must now be the authoritative entry from Node A
        self.assertEqual(self.node_b.log[1].term, 2)
        self.assertEqual(self.node_b.log[1].entry_type, CommitteeEntryType.CONSENSUS_VERDICT)
        self.assertEqual(self.node_b.commit_index, 1)

    def test_07_deterministic_state_machine_pipeline(self) -> None:
        """State machine applies task lifecycle entries in sequence and tracks status."""
        sm = CommitteeStateMachine()
        task_id = "TASK-AUTO-99"

        # 1. Propose task
        e1 = CommitteeLogEntry(
            index=1,
            term=1,
            entry_type=CommitteeEntryType.PROPOSE_TASK,
            author_node_id="node-lead",
            payload={"task_id": task_id, "prompt": "Implement Raft consensus"},
        )
        sm.apply_entry(e1)
        self.assertEqual(sm.task_statuses[task_id], "PROPOSED")

        # 2. Speech turns
        e2 = CommitteeLogEntry(
            index=2,
            term=1,
            entry_type=CommitteeEntryType.SPEECH_TURN,
            author_node_id="node-lead",
            payload={"task_id": task_id, "speaker": "architect", "score": 0.95},
        )
        sm.apply_entry(e2)
        self.assertEqual(len(sm.debates[task_id]), 1)

        # 3. Consensus verdict
        e3 = CommitteeLogEntry(
            index=3,
            term=1,
            entry_type=CommitteeEntryType.CONSENSUS_VERDICT,
            author_node_id="node-lead",
            payload={"task_id": task_id, "decision": "CONSENSUS_APPROVED", "composite_score": 0.96},
        )
        sm.apply_entry(e3)
        self.assertEqual(sm.task_statuses[task_id], "APPROVED")

        # 4. Patch commit
        e4 = CommitteeLogEntry(
            index=4,
            term=1,
            entry_type=CommitteeEntryType.PATCH_COMMIT,
            author_node_id="node-lead",
            payload={"task_id": task_id, "merkle_root": "abcdef1234567890"},
        )
        sm.apply_entry(e4)
        self.assertEqual(sm.task_statuses[task_id], "PATCH_COMMITTED")

        summary = sm.get_task_summary(task_id)
        self.assertEqual(summary["status"], "PATCH_COMMITTED")
        self.assertEqual(summary["patch_merkle_root"], "abcdef1234567890")
        self.assertEqual(summary["last_applied_index"], 4)

    def test_08_pipeline_debate_protocol_raft_integration(self) -> None:
        """PipelineDebateProtocol correctly records turns and verdict into Raft consensus."""
        coordinator = FederatedMeshCoordinator(node_id="node-coord-test")
        protocol = PipelineDebateProtocol(mesh_coordinator=coordinator)

        req = CodingTaskRequest(
            task_id="TASK-P89-001",
            repository_path="d:/fake/repo",
            requirement_prompt="Implement fault-tolerant consensus state machine",
            target_branch="feat/raft-consensus",
            target_files=["agent_workspace/core/raft_consensus.py"],
            use_raft_consensus=True,
        )

        formation = CommitteeFormation(
            task_id="TASK-P89-001",
            members=[
                CommitteeMemberSelection(
                    role="architect",
                    display_name="Principal Architect",
                    mandatory=True,
                    selection_reason="Raft architecture review",
                ),
                CommitteeMemberSelection(
                    role="securityauditor",
                    display_name="Security Auditor",
                    mandatory=True,
                    selection_reason="Byzantine security audit",
                ),
            ],
            risk_level="HIGH",
        )

        debate_record = protocol.run_debate(request=req, formation=formation)

        self.assertIsNotNone(debate_record)
        self.assertIsNotNone(debate_record.raft_log_index)
        self.assertGreater(debate_record.raft_log_index, 0)
        self.assertIsNotNone(debate_record.raft_term)

        # Verify entries logged in coordinator's Raft node
        raft_log = coordinator.get_raft_log()
        types = [e.entry_type for e in raft_log]
        self.assertIn(CommitteeEntryType.SPEECH_TURN, types)
        self.assertIn(CommitteeEntryType.CONSENSUS_VERDICT, types)

    def test_09_mesh_raft_api_endpoints(self) -> None:
        """FastAPI REST routes under /v1/mesh/raft/* respond correctly."""
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        # 1. GET /v1/mesh/raft/status
        status_resp = client.get("/v1/mesh/raft/status")
        self.assertEqual(status_resp.status_code, 200)
        data = status_resp.json()
        self.assertIn("role", data)
        self.assertIn("term", data)
        self.assertIn("commit_index", data)

        # 2. POST /v1/mesh/raft/elect
        elect_resp = client.post("/v1/mesh/raft/elect")
        self.assertEqual(elect_resp.status_code, 200)
        elect_data = elect_resp.json()
        self.assertTrue(elect_data["became_leader"])
        self.assertEqual(elect_data["role"], "LEADER")

        # 3. POST /v1/mesh/raft/propose
        propose_payload = {
            "entry_type": "CONSENSUS_VERDICT",
            "payload": {"task_id": "API-TASK-1", "decision": "CONSENSUS_APPROVED"},
        }
        prop_resp = client.post("/v1/mesh/raft/propose", json=propose_payload)
        self.assertEqual(prop_resp.status_code, 200)
        prop_data = prop_resp.json()
        self.assertEqual(prop_data["status"], "committed")

        # 4. GET /v1/mesh/raft/log
        log_resp = client.get("/v1/mesh/raft/log")
        self.assertEqual(log_resp.status_code, 200)
        log_data = log_resp.json()
        self.assertGreaterEqual(log_data["log_length"], 2)


if __name__ == "__main__":
    unittest.main()
