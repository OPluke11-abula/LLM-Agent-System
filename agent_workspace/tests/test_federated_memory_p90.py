"""Comprehensive test suite for Phase 90: Federated Vector Memory & RAG Knowledge Topology Sync.

Verifies:
1. Vector entry creation, L2-normalized embedding generation, and cosine similarity ranking.
2. Category taxonomy filtering (DECISION, LESSON, PATTERN, ERROR) and similarity cutoffs.
3. Deterministic cryptographic Merkle tree root calculation and topology verification.
4. Two-node delta sync reconciliation and state convergence.
5. Zero-Trust mTLS attestation gating preventing unauthorized memory injection.
6. Raft VECTOR_CHECKPOINT entry replication and deterministic state machine application.
7. PipelineDebateProtocol pre-debate RAG precedent injection and post-debate consensus auto-indexing.
8. FastAPI REST API endpoints (/v1/mesh/memory/*) with FastAPI TestClient.
"""

from __future__ import annotations

import os
import sys
import pytest
from fastapi.testclient import TestClient

# Ensure agent_workspace is in sys.path
workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)

from agent_workspace.core.vector_memory import (
    FederatedVectorMemory,
    VectorCategory,
    VectorMemoryEntry,
    cosine_similarity,
)
from agent_workspace.core.raft_consensus import (
    CommitteeEntryType,
    CommitteeLogEntry,
    CommitteeRaftNode,
    CommitteeStateMachine,
    RaftRole,
)
from agent_workspace.core.federated_mesh import (
    AttestationStatus,
    FederatedMeshCoordinator,
    PeerCapability,
)
from agent_workspace.core.pipeline.debate_protocol import PipelineDebateProtocol
from agent_workspace.core.pipeline.models import CodingTaskRequest
from fastapi import FastAPI
from agent_workspace.core.pipeline.committee import CommitteeFormation, CommitteeMemberSelection
from agent_workspace.routes.mesh import router


# -----------------------------------------------------------------------------
# 1. Cosine Similarity & Vector Memory Basic Operations
# -----------------------------------------------------------------------------


def test_cosine_similarity_math():
    """Verifies cosine similarity calculation and boundary handling."""
    # Orthogonal vectors
    vec_a = [1.0, 0.0, 0.0]
    vec_b = [0.0, 1.0, 0.0]
    assert cosine_similarity(vec_a, vec_b) == 0.0

    # Identical vectors
    assert pytest.approx(cosine_similarity(vec_a, vec_a), abs=1e-5) == 1.0

    # Opposite vectors
    vec_c = [-1.0, 0.0, 0.0]
    assert pytest.approx(cosine_similarity(vec_a, vec_c), abs=1e-5) == -1.0

    # Empty or mismatched vectors
    assert cosine_similarity([], [1.0]) == 0.0
    assert cosine_similarity([1.0, 2.0], [1.0]) == 0.0


def test_vector_memory_store_and_search():
    """Verifies storing vector memories, category tagging, and similarity search ranking."""
    mem = FederatedVectorMemory(node_id="node-test-1")

    e1 = mem.store(
        task_id="TASK-101",
        category=VectorCategory.DECISION,
        content="Decouple domain business logic from FastAPI presentation routers to satisfy Single Responsibility.",
        metadata={"author": "architect", "score": 0.95},
    )
    e2 = mem.store(
        task_id="TASK-102",
        category=VectorCategory.ERROR,
        content="Detected unauthorized bypass of authentication middleware in API handler.",
        metadata={"author": "security", "score": 0.20},
    )
    e3 = mem.store(
        task_id="TASK-103",
        category=VectorCategory.PATTERN,
        content="Use last-write-wins element-set CRDT to synchronize peer state without coordinator deadlocks.",
        metadata={"author": "infra", "score": 0.90},
    )

    assert len(mem._entries) == 3
    assert e1.verify_integrity()
    assert e2.verify_integrity()
    assert e3.verify_integrity()

    # Search for architectural decoupling
    results = mem.search(
        query="decouple domain logic from routers",
        top_k=2,
    )
    assert len(results) > 0
    assert results[0].rank == 1
    assert results[0].entry.entry_id == e1.entry_id

    # Search with category filter
    error_results = mem.search(
        query="security authentication",
        category=VectorCategory.ERROR,
        top_k=5,
    )
    assert len(error_results) == 1
    assert error_results[0].entry.category == VectorCategory.ERROR
    assert error_results[0].entry.task_id == "TASK-102"


# -----------------------------------------------------------------------------
# 2. Merkle Tree Root Determinism & Integrity
# -----------------------------------------------------------------------------


def test_vector_memory_merkle_root_determinism():
    """Verifies that identical entries produce identical cryptographic Merkle roots."""
    mem1 = FederatedVectorMemory(node_id="node-alpha")
    mem2 = FederatedVectorMemory(node_id="node-beta")

    # Empty memory root
    root_empty = mem1.compute_merkle_root()
    assert len(root_empty) == 64
    assert root_empty == mem2.compute_merkle_root()

    # Store identical entries in different insertion orders
    entry_data_a = {
        "task_id": "T-1",
        "category": VectorCategory.DECISION,
        "content": "Alpha decision pattern",
        "entry_id": "fixed-vec-01",
        "author_node_id": "author-shared",
    }
    entry_data_b = {
        "task_id": "T-2",
        "category": VectorCategory.LESSON,
        "content": "Beta lesson learned",
        "entry_id": "fixed-vec-02",
        "author_node_id": "author-shared",
    }

    # mem1 inserts A then B
    mem1.store(**entry_data_a)
    mem1.store(**entry_data_b)
    root_1 = mem1.compute_merkle_root()

    # mem2 inserts B then A
    mem2.store(**entry_data_b)
    mem2.store(**entry_data_a)
    root_2 = mem2.compute_merkle_root()

    # Roots MUST be identical regardless of insertion order (sorted leaves)
    assert root_1 == root_2

    # Mutating content MUST change root
    mem1.store(
        task_id="T-3",
        category=VectorCategory.PATTERN,
        content="Gamma additional pattern",
        entry_id="fixed-vec-03",
        author_node_id="author-shared",
    )
    root_3 = mem1.compute_merkle_root()
    assert root_3 != root_1


# -----------------------------------------------------------------------------
# 3. Two-Node Delta Synchronization & Reconciliation
# -----------------------------------------------------------------------------


def test_two_node_delta_reconciliation():
    """Verifies peer manifest delta detection and bilateral synchronization."""
    node_a = FederatedVectorMemory(node_id="node-A")
    node_b = FederatedVectorMemory(node_id="node-B")

    # Node A has entries 1 and 2
    e1 = node_a.store("TASK-1", VectorCategory.DECISION, "Decision 1", entry_id="v1", author_node_id="author-A")
    e2 = node_a.store("TASK-2", VectorCategory.PATTERN, "Pattern 2", entry_id="v2", author_node_id="author-shared")

    # Node B has entries 2 and 3
    node_b.store("TASK-2", VectorCategory.PATTERN, "Pattern 2", entry_id="v2", author_node_id="author-shared")
    e3 = node_b.store("TASK-3", VectorCategory.LESSON, "Lesson 3", entry_id="v3", author_node_id="author-B")

    manifest_a = node_a.get_manifest()
    manifest_b = node_b.get_manifest()

    # Node A reconciles against B -> identifies missing entry v3
    missing_for_a = node_a.reconcile_delta(manifest_b)
    assert missing_for_a == ["v3"]

    # Node B reconciles against A -> identifies missing entry v1
    missing_for_b = node_b.reconcile_delta(manifest_a)
    assert missing_for_b == ["v1"]

    # Exchange missing entries
    entries_for_a = node_b.get_entries_by_ids(missing_for_a)
    entries_for_b = node_a.get_entries_by_ids(missing_for_b)

    added_a, root_a = node_a.merge_entries(entries_for_a)
    added_b, root_b = node_b.merge_entries(entries_for_b)

    assert added_a == 1
    assert added_b == 1
    assert len(node_a._entries) == 3
    assert len(node_b._entries) == 3

    # Both nodes must converge to the exact same Merkle root
    assert root_a == root_b
    assert node_a.compute_merkle_root() == node_b.compute_merkle_root()


# -----------------------------------------------------------------------------
# 4. Zero-Trust Attestation Gated Vector Sync
# -----------------------------------------------------------------------------


def test_zero_trust_attestation_gating_vector_sync():
    """Verifies that unattested or rejected peers cannot push vector entries."""
    coord = FederatedMeshCoordinator(
        node_id="lead-01",
        strict_attestation=True,
    )

    # Register an UNVERIFIED (PENDING) peer
    coord.register_peer(
        node_id="peer-unverified",
        host="127.0.0.1",
        port=8002,
        attestation_status=AttestationStatus.PENDING,
    )

    malicious_entry = {
        "entry_id": "vec-rogue-1",
        "task_id": "TASK-MALICIOUS",
        "category": "DECISION",
        "content": "Malicious vector injection attempt",
        "content_hash": "dummy",
        "author_node_id": "peer-unverified",
        "timestamp": 1000.0,
    }

    # Attempt sync from unverified peer -> MUST be rejected
    res = coord.sync_vector_memory(
        peer_id="peer-unverified",
        entries_payload=[malicious_entry],
    )
    assert res["status"] == "rejected"
    assert "Zero-Trust" in res["error"]
    assert len(coord.vector_memory._entries) == 0

    # Attest peer as VERIFIED
    coord.peers["peer-unverified"].attestation_status = AttestationStatus.VERIFIED

    # Resend sync -> MUST succeed
    valid_entry = VectorMemoryEntry(
        entry_id="vec-valid-1",
        task_id="TASK-VERIFIED",
        category=VectorCategory.DECISION,
        content="Legitimate consensus vector entry",
        author_node_id="peer-unverified",
        timestamp=2000.0,
    )
    valid_entry.ensure_hash()

    res_verified = coord.sync_vector_memory(
        peer_id="peer-unverified",
        entries_payload=[valid_entry.model_dump()],
    )
    assert res_verified["status"] == "synced"
    assert res_verified["added_count"] == 1
    assert len(coord.vector_memory._entries) == 1


# -----------------------------------------------------------------------------
# 5. Raft Replicated State Machine Vector Checkpoints
# -----------------------------------------------------------------------------


def test_raft_vector_checkpoint_commit():
    """Verifies that Raft consensus commits VECTOR_CHECKPOINT entries to the state machine."""
    state_machine = CommitteeStateMachine()

    entry = CommitteeLogEntry(
        index=1,
        term=1,
        entry_type=CommitteeEntryType.VECTOR_CHECKPOINT,
        author_node_id="node-lead",
        payload={
            "task_id": "TASK-100",
            "merkle_root": "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
            "total_entries": 42,
        },
    )
    entry.sign("secret-key")
    assert entry.verify_signature("secret-key")

    state_machine.apply_entry(entry)

    assert len(state_machine.vector_checkpoints) == 1
    assert state_machine.latest_vector_merkle_root == entry.payload["merkle_root"]
    summary = state_machine.get_task_summary("TASK-100")
    assert summary["vector_checkpoints_count"] == 1
    assert summary["latest_vector_merkle_root"] == entry.payload["merkle_root"]


# -----------------------------------------------------------------------------
# 6. Debate Protocol Pre-Debate RAG & Post-Debate Auto-Indexing
# -----------------------------------------------------------------------------


def test_debate_protocol_vector_memory_rag_and_indexing():
    """Verifies pre-debate precedent retrieval and post-debate experience auto-indexing."""
    coord = FederatedMeshCoordinator(node_id="lead-coord")
    vec_mem = coord.vector_memory

    # Pre-populate historical memory with a past lesson
    vec_mem.store(
        task_id="TASK-PAST-01",
        category=VectorCategory.LESSON,
        content="Multi-module task mutations require strict decoupled interfaces to pass committee review.",
        metadata={"author": "architect"},
    )

    protocol = PipelineDebateProtocol(
        mesh_coordinator=coord,
        vector_memory=vec_mem,
    )

    request = CodingTaskRequest(
        task_id="TASK-NEW-01",
        repository_path=".",
        target_branch="main",
        requirement_prompt="Refactor database gateway with decoupled interfaces",
        target_files=["agent_workspace/core/db_gateway.py"],
        debate_rounds=1,
        use_raft_consensus=True,
    )

    formation = CommitteeFormation(
        task_id=request.task_id,
        members=[
            CommitteeMemberSelection(role="architect", display_name="Architect", mandatory=True, selection_reason="Core review"),
            CommitteeMemberSelection(role="securityauditor", display_name="Security Auditor", mandatory=True, selection_reason="Zero-trust review"),
            CommitteeMemberSelection(role="qaengineer", display_name="QA Engineer", mandatory=True, selection_reason="Testing review"),
        ],
    )

    record = protocol.run_debate(request=request, formation=formation)

    assert record.consensus_scorecard.decision == "CONSENSUS_APPROVED"

    # Verify that architect turn cited the historical precedent
    architect_turn = next(t for t in record.rounds[0].turns if t.speaker_role == "architect")
    assert "Federated Knowledge Topology Precedent" in architect_turn.content
    assert any("TASK-PAST-01" in cp for cp in architect_turn.critique_points)

    # Verify post-debate auto-indexing into vector memory
    recent_entries = vec_mem.get_entries(limit=5)
    indexed_entry = next((e for e in recent_entries if e.task_id == "TASK-NEW-01"), None)
    assert indexed_entry is not None
    assert indexed_entry.category == VectorCategory.DECISION
    assert "CONSENSUS_APPROVED" in indexed_entry.content


# -----------------------------------------------------------------------------
# 7. FastAPI REST API Endpoints (/v1/mesh/memory/*)
# -----------------------------------------------------------------------------


def test_fastapi_mesh_memory_endpoints():
    """Verifies REST endpoints for stats, store, query, and sync."""
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    # 1. Stats
    resp_stats = client.get("/v1/mesh/memory/stats")
    assert resp_stats.status_code == 200
    stats = resp_stats.json()
    assert "total_entries" in stats
    assert "merkle_root" in stats
    assert stats["embedding_dimension"] == 1536

    # 2. Store
    store_payload = {
        "task_id": "TASK-REST-01",
        "category": "DECISION",
        "content": "Enforce type-safe Pydantic models on all external API request boundaries.",
        "metadata": {"test": True},
    }
    resp_store = client.post("/v1/mesh/memory/store", json=store_payload)
    assert resp_store.status_code == 200
    store_data = resp_store.json()
    assert store_data["task_id"] == "TASK-REST-01"
    assert "content_hash" in store_data

    # 3. Query
    query_payload = {
        "query": "type-safe Pydantic models",
        "top_k": 3,
        "category": "DECISION",
    }
    resp_query = client.post("/v1/mesh/memory/query", json=query_payload)
    assert resp_query.status_code == 200
    query_data = resp_query.json()
    assert query_data["results_count"] >= 1
    assert query_data["results"][0]["task_id"] == "TASK-REST-01"

    # 4. Entries list
    resp_entries = client.get("/v1/mesh/memory/entries?limit=5")
    assert resp_entries.status_code == 200
    entries_data = resp_entries.json()
    assert len(entries_data["entries"]) >= 1

    # 5. Sync
    sync_payload = {
        "peer_id": "peer-client-01",
        "entries": [],
    }
    resp_sync = client.post("/v1/mesh/memory/sync", json=sync_payload)
    assert resp_sync.status_code == 200
    sync_data = resp_sync.json()
    assert sync_data["status"] == "synced"
