"""Unit and integration test suite for Distributed P2P Mesh & Federated Worktree Clustering (Phase 87).

Validates:
1. PeerCapability and FederatedPeerProfile serialization and load balancing.
2. FederatedPatchBundle creation, cryptographic hashing, and Merkle integrity verification.
3. FederatedMeshCoordinator peer registration and optimal peer selection.
4. Remote debate speech turn delegation to REASONING_ENGINE peers.
5. Remote verification ladder delegation to TEST_RUNNER peers.
6. PipelineDebateProtocol integration with mesh coordinator.
7. FastAPI REST endpoints (/v1/mesh/status, /v1/mesh/peers, /v1/mesh/join, /v1/mesh/delegate/turn).
8. Graceful degradation to local execution when remote peers are disconnected.
"""

from __future__ import annotations

import asyncio
import hashlib
import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from agent_workspace.api import app
from agent_workspace.core.federated_mesh import (
    FederatedDelegationRequest,
    FederatedDelegationResponse,
    FederatedMeshCoordinator,
    FederatedPatchBundle,
    FederatedPeerProfile,
    PeerCapability,
    get_federated_coordinator,
)
from agent_workspace.core.pipeline.committee import CommitteeCoordinator
from agent_workspace.core.pipeline.debate_protocol import PipelineDebateProtocol
from agent_workspace.core.pipeline.models import CodingTaskRequest, PipelineStage


class TestFederatedMeshP87(unittest.TestCase):
    """Test suite for Phase 87 Distributed P2P Mesh Subsystem."""

    def setUp(self):
        self.coordinator = FederatedMeshCoordinator(
            node_id="node-test-coord",
            role="architect",
            host="127.0.0.1",
            port=8000,
            capabilities=[PeerCapability.COCKPIT_LEADER, PeerCapability.REASONING_ENGINE],
        )

    def test_peer_capability_and_profile_serialization(self):
        """Validates PeerCapability enum and FederatedPeerProfile serialization."""
        profile = FederatedPeerProfile(
            node_id="peer-gpu-worker-1",
            role="worker",
            host="192.168.1.150",
            port=8000,
            capabilities=[PeerCapability.REASONING_ENGINE, PeerCapability.TEST_RUNNER],
            status="connected",
            latency_ms=18.5,
            load_score=0.35,
        )

        data = profile.model_dump()
        self.assertEqual(data["node_id"], "peer-gpu-worker-1")
        self.assertEqual(data["role"], "worker")
        self.assertIn("REASONING_ENGINE", data["capabilities"])
        self.assertIn("TEST_RUNNER", data["capabilities"])
        self.assertEqual(data["latency_ms"], 18.5)

        reconstructed = FederatedPeerProfile.model_validate(data)
        self.assertEqual(reconstructed.node_id, profile.node_id)
        self.assertEqual(len(reconstructed.capabilities), 2)

    def test_federated_patch_bundle_integrity_verification(self):
        """Tests that FederatedPatchBundle verifies unified diff and file Merkle root."""
        patch_text = "--- a/main.py\n+++ b/main.py\n@@ -1 +1 @@\n-old\n+new\n"
        files = ["main.py", "core/engine.py"]

        # Compute valid root
        hasher = hashlib.sha256()
        hasher.update(patch_text.encode("utf-8"))
        for f in sorted(files):
            hasher.update(f.encode("utf-8"))
        expected_root = hasher.hexdigest()

        bundle = FederatedPatchBundle(
            task_id="TASK-TEST-001",
            base_commit="HEAD~1",
            target_branch="feat/test-patch",
            patch_content=patch_text,
            files_affected=files,
            merkle_root=expected_root,
            author_node_id="node-author-42",
        )

        self.assertTrue(bundle.verify_integrity())

        # Tampered content must fail integrity verification
        tampered_bundle = FederatedPatchBundle(
            task_id="TASK-TEST-001",
            base_commit="HEAD~1",
            target_branch="feat/test-patch",
            patch_content=patch_text + "# injection\n",
            files_affected=files,
            merkle_root=expected_root,
            author_node_id="node-author-42",
        )
        self.assertFalse(tampered_bundle.verify_integrity())

    def test_coordinator_peer_registration_and_selection(self):
        """Tests peer registration and latency/load-balanced peer selection."""
        # Register 2 reasoning peers with different latency and load
        self.coordinator.register_peer(
            node_id="peer-gpu-heavy",
            role="worker",
            host="10.0.0.1",
            port=8001,
            capabilities=[PeerCapability.REASONING_ENGINE],
            latency_ms=80.0,
            load_score=0.8,
        )

        self.coordinator.register_peer(
            node_id="peer-gpu-fast",
            role="worker",
            host="10.0.0.2",
            port=8002,
            capabilities=[PeerCapability.REASONING_ENGINE],
            latency_ms=12.0,
            load_score=0.1,
        )

        # Register a test runner peer
        self.coordinator.register_peer(
            node_id="peer-test-runner",
            role="qa",
            host="10.0.0.3",
            port=8003,
            capabilities=[PeerCapability.TEST_RUNNER],
            latency_ms=15.0,
            load_score=0.2,
        )

        # Query REASONING_ENGINE -> should pick fast peer
        best_reasoning = self.coordinator.select_best_peer(PeerCapability.REASONING_ENGINE)
        self.assertIsNotNone(best_reasoning)
        self.assertEqual(best_reasoning.node_id, "peer-gpu-fast")

        # Query TEST_RUNNER -> should pick test runner peer
        best_test = self.coordinator.select_best_peer(PeerCapability.TEST_RUNNER)
        self.assertIsNotNone(best_test)
        self.assertEqual(best_test.node_id, "peer-test-runner")

        # Query SANDBOX_MUTATION -> none registered -> returns None
        best_sandbox = self.coordinator.select_best_peer(PeerCapability.SANDBOX_MUTATION)
        self.assertIsNone(best_sandbox)

    def test_delegated_debate_speech_turn(self):
        """Tests asynchronous debate speech turn delegation to a remote peer."""
        self.coordinator.register_peer(
            node_id="peer-remote-reasoner",
            role="worker",
            host="192.168.1.200",
            port=8000,
            capabilities=[PeerCapability.REASONING_ENGINE],
            latency_ms=15.0,
            load_score=0.1,
        )

        speech = asyncio.run(
            self.coordinator.delegate_debate_speech(
                task_id="TASK-P87-001",
                role="architect",
                plan_summary="Refactor mesh networking",
                risk_profile={"risk_level": "medium"},
                thinking_budget=4096,
            )
        )

        self.assertIsNotNone(speech)
        self.assertEqual(speech.agent_role, "architect")
        self.assertIn("peer-remote-reasoner", speech.speech_content.lower())
        self.assertGreater(speech.reasoning_tokens, 0)
        self.assertIsNotNone(speech.reasoning_content)

    def test_delegated_test_verification_ladder(self):
        """Tests remote verification ladder delegation to a TEST_RUNNER peer."""
        self.coordinator.register_peer(
            node_id="peer-ci-worker",
            role="qa",
            host="192.168.1.201",
            port=8000,
            capabilities=[PeerCapability.TEST_RUNNER],
            latency_ms=25.0,
            load_score=0.15,
        )

        res = asyncio.run(
            self.coordinator.delegate_test_verification(
                task_id="TASK-P87-002",
                test_commands=["pytest tests/test_core.py", "git diff --check"],
            )
        )

        self.assertIsNotNone(res)
        self.assertTrue(res["all_passed"])
        self.assertEqual(len(res["ladder_results"]), 2)

    def test_pipeline_debate_protocol_with_mesh(self):
        """Tests that PipelineDebateProtocol integrates with mesh coordinator."""
        self.coordinator.register_peer(
            node_id="peer-mesh-architect",
            role="worker",
            host="127.0.0.1",
            port=8005,
            capabilities=[PeerCapability.REASONING_ENGINE],
            latency_ms=8.5,
            load_score=0.05,
        )

        debate_protocol = PipelineDebateProtocol(mesh_coordinator=self.coordinator)
        committee_coord = CommitteeCoordinator()

        request = CodingTaskRequest(
            task_id="TASK-P87-MESH-01",
            repository_path="d:/GitHub/LLM-Agent-System",
            requirement_prompt="Add decentralized peer discovery heartbeat",
            target_branch="feat/mesh-heartbeat",
            use_mesh=True,
            enable_committee=True,
            debate_rounds=1,
            committee_roles=["architect", "qaengineer"],
        )

        formation = committee_coord.evaluate_committee(request)
        debate_record = debate_protocol.run_debate(request, formation)

        self.assertIsNotNone(debate_record)
        self.assertEqual(len(debate_record.rounds), 1)
        turns = debate_record.rounds[0].turns
        self.assertGreaterEqual(len(turns), 2)

        # Verify that mesh review content is present
        arch_turn = next((t for t in turns if "architect" in t.speaker_role.lower()), None)
        self.assertIsNotNone(arch_turn)
        self.assertIn("Federated Mesh Review", arch_turn.content)

    def test_mesh_fastapi_rest_endpoints(self):
        """Tests FastAPI REST endpoints in /v1/mesh."""
        client = TestClient(app)

        # GET /v1/mesh/status
        res_status = client.get("/v1/mesh/status")
        self.assertEqual(res_status.status_code, 200)
        data_status = res_status.json()
        self.assertIn("local_node", data_status)
        self.assertIn("cluster_health", data_status)

        # POST /v1/mesh/join
        res_join = client.post(
            "/v1/mesh/join",
            json={
                "seed_address": "192.168.1.188:8000",
                "role": "worker",
                "capabilities": ["REASONING_ENGINE", "TEST_RUNNER"],
            },
        )
        self.assertEqual(res_join.status_code, 200)
        data_join = res_join.json()
        self.assertEqual(data_join["host"], "192.168.1.188")
        self.assertEqual(data_join["port"], 8000)

        # GET /v1/mesh/peers
        res_peers = client.get("/v1/mesh/peers")
        self.assertEqual(res_peers.status_code, 200)
        peers_list = res_peers.json()
        self.assertGreaterEqual(len(peers_list), 1)

        # POST /v1/mesh/delegate/turn
        res_turn = client.post(
            "/v1/mesh/delegate/turn",
            json={
                "delegation_type": "committee_turn",
                "origin_node_id": "node-test-client",
                "task_id": "TASK-REST-01",
                "role": "architect",
                "payload": {"plan_summary": "Test REST debate turn", "thinking_budget": 2048},
            },
        )
        self.assertEqual(res_turn.status_code, 200)
        data_turn = res_turn.json()
        self.assertEqual(data_turn["status"], "success")
        self.assertIn("speech_content", data_turn["result"])

    def test_graceful_local_degradation(self):
        """Ensures that when no peers are registered or online, coordinator degrades cleanly."""
        empty_coordinator = FederatedMeshCoordinator(
            node_id="node-empty-mesh",
            role="architect",
            host="127.0.0.1",
            port=8000,
            capabilities=[PeerCapability.COCKPIT_LEADER],
        )

        # select_best_peer should return None without error
        peer = empty_coordinator.select_best_peer(PeerCapability.REASONING_ENGINE)
        self.assertIsNone(peer)

        # delegate_debate_speech should return None, signaling local fallback
        speech = asyncio.run(
            empty_coordinator.delegate_debate_speech(
                task_id="TASK-EMPTY-01",
                role="architect",
                plan_summary="Test fallback",
                risk_profile={},
            )
        )
        self.assertIsNone(speech)

        # delegate_test_verification should return None, signaling local test execution
        ladder = asyncio.run(
            empty_coordinator.delegate_test_verification(
                task_id="TASK-EMPTY-02",
                test_commands=["pytest"],
            )
        )
        self.assertIsNone(ladder)


if __name__ == "__main__":
    unittest.main()
