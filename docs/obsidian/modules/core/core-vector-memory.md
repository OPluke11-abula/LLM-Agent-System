---
tags:
  - architecture/core
  - module/mesh/vector-memory
  - module/rag/knowledge-topology
  - layer/l2
  - layer/l3
  - protocol/v3-8-0
type: core_module
layer: L3-Autonomous-Workflow-and-Verification
sync_status: verified
---

# Core Module: Federated Vector Memory & RAG Knowledge Topology (`core-vector-memory`)

> **Parent Layer**: [[L2-Protocol-and-Contract-Gateways]], [[L3-Autonomous-Workflow-and-Verification]], [[core-federated-mesh]], [[core-raft-consensus]], [[core-pipeline-committee]]
> **Source Directory**: `agent_workspace/core/`, `agent_workspace/routes/`
> **Primary Source Files**:
> - [`vector_memory.py`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/vector_memory.py) (`FederatedVectorMemory`, `VectorCategory`, `VectorMemoryEntry`, `VectorSearchResult`, `cosine_similarity`)
> - [`embeddings.py`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/embeddings.py) (`generate_mock_embedding` with word-token semantic affinity, `EmbeddingGenerator`)
> - [`raft_consensus.py`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/raft_consensus.py) (`CommitteeEntryType.VECTOR_CHECKPOINT`, `CommitteeStateMachine` vector checkpoint tracking)
> - [`federated_mesh.py`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/federated_mesh.py) (`FederatedMeshCoordinator` vector memory coordination, zero-trust attestation gating on peer sync, delta-reconciliation)
> - [`debate_protocol.py`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/pipeline/debate_protocol.py) (`PipelineDebateProtocol` pre-debate RAG precedent retrieval, post-debate experience auto-indexing)
> - [`routes/mesh.py`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/routes/mesh.py) (REST `/v1/mesh/memory/stats`, `/v1/mesh/memory/entries`, `/v1/mesh/memory/query`, `/v1/mesh/memory/store`, `/v1/mesh/memory/sync`)
> - [`cli.py`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/cli.py) (`las mesh memory stats`, `las mesh memory query "<prompt>"`, `las mesh memory sync`)
> - [`viewer/src/components/FederatedMeshView.tsx`](file:///d:/GitHub/LLM-Agent-System/viewer/src/components/FederatedMeshView.tsx) (Federated Vector Memory Bento Card, Cosine Search Bar, Replicated Knowledge Ledger)
> **Associated Tests**:
> - [`test_federated_memory_p90.py`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/tests/test_federated_memory_p90.py) (Phase 90 test suite: 8/8 PASS)
> **ADR Reference**: [[60 Architectural Decision Records (ADR) Graph#ADR-005|ADR-005: Stop-and-Wait Gate]], [[60 Architectural Decision Records (ADR) Graph#ADR-006|ADR-006: Autonomous Strategy Integration]]

---

## 1. Module Overview & Problem Statement

`core/vector_memory.py` implements **Phase 90: Federated Vector Memory & RAG Knowledge Topology Sync (聯邦向量記憶體與分散式經驗庫拓撲同步)**.

In prior phases (Phase 87 ~ Phase 89), distributed mesh nodes established P2P routing, mTLS PKI Zero-Trust attestation, and Raft quorum consensus. However, agents deliberated in isolation regarding past mistakes, recurring architectural pitfalls, and historical consensus scorecards. When one node learned that a particular multi-module mutation violates Extreme Single Responsibility, other nodes had no decentralized knowledge mechanism to recall this insight before beginning their own debate rounds.

Phase 90 introduces a decentralized, cryptographically verifiable vector memory subsystem:
1. **Thread-Safe Vector Store & Cosine Similarity Search**: Indexes `VectorMemoryEntry` instances categorized across `DECISION`, `LESSON`, `PATTERN`, `ERROR`, and `CODE_SNIPPET`, with normalized cosine similarity ranking and score threshold pruning.
2. **Deterministic Cryptographic Merkle Root**: Builds a pairwise-hashed Merkle tree over sorted leaf hashes (`content_hash`), providing $O(1)$ topology comparison between nodes to immediately detect knowledge divergence.
3. **Bilateral Delta Synchronization**: Manifest exchange identifies missing entries between nodes, performing idempotent merges with last-write-wins conflict resolution.
4. **Zero-Trust Attestation Gating**: Incoming memory synchronization is strictly barred unless the remote peer is verified (`AttestationStatus.VERIFIED`) under Phase 88 PKI.
5. **Raft Consensus Integration**: When leader nodes commit experiences or sync deltas, a `VECTOR_CHECKPOINT` log entry is replicated across the cluster, ensuring deterministic knowledge convergence across all non-faulty nodes.
6. **Debate RAG Experience Injection**: Before deliberation, `PipelineDebateProtocol` queries vector memory for historical lessons relevant to `requirement_prompt`, injecting them into committee reasoning turns. Upon consensus verdict, the outcome is auto-indexed into the topology.

```mermaid
graph TD
    classDef memory fill:#1e293b,stroke:#a855f7,stroke-width:2px,color:#f8fafc;
    classDef debate fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#f8fafc;
    classDef raft fill:#1e293b,stroke:#34d399,stroke-width:2px,color:#f8fafc;

    VM["FederatedVectorMemory<br/>- Cosine Similarity Search<br/>- Merkle Root Verification"]:::memory
    DP["PipelineDebateProtocol<br/>- Pre-Debate RAG Injection<br/>- Post-Debate Auto-Indexing"]:::debate
    RC["CommitteeRaftNode<br/>- VECTOR_CHECKPOINT Replicated Log"]:::raft

    DP -->|1. Search Precedents (RAG)| VM
    VM -->>|2. Relevant Lessons| DP
    DP -->|3. Deliberate & Synthesize Verdict| DP
    DP -->|4. Store Consensus Experience| VM
    DP -->|5. Propose Replicated Checkpoint| RC
    RC -->|6. Apply to State Machine| VM
```

---

## 2. Key Data Models & Algorithms

### 2.1 VectorMemoryEntry
```python
class VectorMemoryEntry(BaseModel):
    entry_id: str
    task_id: str
    category: VectorCategory  # DECISION, LESSON, PATTERN, ERROR, CODE_SNIPPET
    content: str
    metadata: Dict[str, Any]
    embedding: List[float]
    content_hash: str
    author_node_id: str
    timestamp: float
```
- **Integrity**: `content_hash` is computed deterministically via `SHA-256` over canonical `{entry_id}:{task_id}:{category}:{author_node_id}:{content}:{metadata}`.

### 2.2 Merkle Tree Topology Calculation
All leaf hashes are sorted lexicographically, then pairwise hashed up to a single root:
$$\text{Root} = \text{MerkleTree}(\text{sorted}(\{H(\text{entry}_i)\}))$$
If two nodes have identical entries, their Merkle roots will match exactly.

### 2.3 Cosine Similarity
$$\text{sim}(q, e) = \frac{q \cdot e}{\|q\| \|e\|}$$
Because embeddings are L2-normalized upon creation, this simplifies to an efficient dot product clamped to $[-1.0, 1.0]$.

---

## 3. Verification & Test Evidence

Verified by [`test_federated_memory_p90.py`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/tests/test_federated_memory_p90.py):
- `test_cosine_similarity_math`: PASS
- `test_vector_memory_store_and_search`: PASS
- `test_vector_memory_merkle_root_determinism`: PASS
- `test_two_node_delta_reconciliation`: PASS
- `test_zero_trust_attestation_gating_vector_sync`: PASS
- `test_raft_vector_checkpoint_commit`: PASS
- `test_debate_protocol_vector_memory_rag_and_indexing`: PASS
- `test_fastapi_mesh_memory_endpoints`: PASS
