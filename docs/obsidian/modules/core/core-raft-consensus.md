---
tags:
  - architecture/core
  - module/mesh/raft
  - module/consensus/state-machine
  - layer/l2
  - layer/l3
  - protocol/v3-8-0
type: core_module
layer: L3-Autonomous-Workflow-and-Verification
sync_status: verified
---

# Core Module: Distributed Committee Raft Consensus (`core-raft-consensus`)

> **Parent Layer**: [[L2-Protocol-and-Contract-Gateways]], [[L3-Autonomous-Workflow-and-Verification]], [[core-federated-mesh]], [[core-mesh-pki]], [[core-pipeline-committee]]
> **Source Directory**: `agent_workspace/core/`, `agent_workspace/routes/`
> **Primary Source Files**:
> - [`raft_consensus.py`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/raft_consensus.py) (`CommitteeRaftNode`, `CommitteeStateMachine`, `CommitteeLogEntry`, `CommitteeEntryType`, `RaftRole`, `RequestVoteArgs`, `RequestVoteReply`, `AppendEntriesArgs`, `AppendEntriesReply`)
> - [`federated_mesh.py`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/federated_mesh.py) (`FederatedMeshCoordinator` Raft node embedding, zero-trust attestation verification for voting and replication, proposal submission)
> - [`debate_protocol.py`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/pipeline/debate_protocol.py) (`PipelineDebateProtocol` logging debate speech turns and consensus scorecards to the replicated Raft log)
> - [`routes/mesh.py`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/routes/mesh.py) (REST `/v1/mesh/raft/status`, `/v1/mesh/raft/log`, `/v1/mesh/raft/elect`, `/v1/mesh/raft/vote`, `/v1/mesh/raft/append_entries`, `/v1/mesh/raft/propose`)
> - [`cli.py`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/cli.py) (`las mesh raft status`, `las mesh raft elect`, `las mesh raft log [--limit N]`)
> - [`viewer/src/components/FederatedMeshView.tsx`](file:///d:/GitHub/LLM-Agent-System/viewer/src/components/FederatedMeshView.tsx) (Raft Bento Status Card, Quorum Metrics, Trigger Election Button, and Replicated Debate Ledger table)
> **Associated Tests**:
> - [`test_committee_raft_p89.py`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/tests/test_committee_raft_p89.py) (Phase 89 test suite: 9/9 PASS)
> **ADR Reference**: [[60 Architectural Decision Records (ADR) Graph#ADR-005|ADR-005: Stop-and-Wait Gate]], [[60 Architectural Decision Records (ADR) Graph#ADR-006|ADR-006: Autonomous Strategy Integration]]

---

## 1. Module Overview & Problem Statement

`core/raft_consensus.py` implements **Phase 89: Distributed Committee Raft Consensus & Replicated State Machine (分散式委員會 Raft 共識狀態機與辯論日誌複製)**.

In prior phases (Phase 85 ~ Phase 88), multi-agent committee debate deliberation and consensus scorecards were orchestrated from a single leader node (`COCKPIT_LEADER`), offloading speech turns to worker nodes. However, in true distributed autonomous agent networks, relying on a single leader creates a single point of failure (SPOF) and vulnerability to network partitions or rogue peer manipulation.

Phase 89 introduces a Byzantine-hardened, fault-tolerant Raft consensus state machine:
1. **Dynamic Leader Election**: Nodes transition across `FOLLOWER`, `CANDIDATE`, and `LEADER` with randomized election leases and term progression.
2. **Phase 88 Zero-Trust Attestation Integration**: Only nodes with verified cryptographic attestation (`attestation_status == AttestationStatus.VERIFIED`) are permitted to cast votes, become leaders, or count toward the quorum.
3. **Quorum Commit Guarantee**: Any proposed log entry (such as specialist speech turns, security critique scores, consensus scorecards, and patch Merkle roots) must be acknowledged by a strict quorum of verified nodes ($\lfloor N/2 \rfloor + 1$) before being committed.
4. **Deterministic State Machine**: Committed entries are sequentially applied to `CommitteeStateMachine`, guaranteeing that all non-faulty nodes reach identical internal states and consensus conclusions.
5. **Conflict Resolution & Split-Brain Prevention**: Log matching invariants ensure that conflicting speculative entries from partitioned or deposed leaders are truncated upon reconnection.

```mermaid
graph TD
    classDef leader fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#f8fafc;
    classDef follower fill:#1e293b,stroke:#a855f7,stroke-width:2px,color:#f8fafc;
    classDef sm fill:#1e293b,stroke:#34d399,stroke-width:2px,color:#f8fafc;

    L["Node A (LEADER)<br/>Term: 2 | Commit: 5"]:::leader
    F1["Node B (FOLLOWER)<br/>Term: 2 | Commit: 5"]:::follower
    F2["Node C (FOLLOWER)<br/>Term: 2 | Commit: 5"]:::follower

    SM["CommitteeStateMachine<br/>- Task Debates<br/>- Scorecards<br/>- Committed Patch Roots"]:::sm

    L -->|1. Propose Speech Turn / Verdict| L
    L -->|2. AppendEntries RPC| F1
    L -->|2. AppendEntries RPC| F2
    F1 -->>|3. Ack Success| L
    F2 -->>|3. Ack Success| L
    L -->|4. Quorum Achieved (3/3) -> Commit| SM
    F1 -->|Apply Committed| SM
    F2 -->|Apply Committed| SM
```

---

## 2. Core Architectural Components

### 2.1 CommitteeLogEntry & Cryptographic Signing
Every entry in the replicated log is modeled as:
- `index`: 1-based monotonically increasing log position.
- `term`: Raft term when received by the leader.
- `entry_type`: Semantic discriminator (`PROPOSE_TASK`, `SPEECH_TURN`, `CRITIQUE_SCORE`, `CONSENSUS_VERDICT`, `PATCH_COMMIT`).
- `author_node_id`: Peer ID of the originating agent.
- `payload`: Structured JSON metadata.
- `signature`: SHA-256 HMAC/digital signature ensuring payload immutability.

### 2.2 Replicated State Machine (`CommitteeStateMachine`)
Maintains the authoritative in-memory state:
- `debates`: Task ID mapped to sequence of speech turns.
- `verdicts`: Task ID mapped to final synthesized consensus scorecards (`CONSENSUS_APPROVED` / `REJECTED_NEEDS_REVISION`).
- `committed_patches`: Task ID mapped to verified git patch Merkle roots.
- `task_statuses`: High-level lifecycle state (`PROPOSED` $\to$ `APPROVED` / `REJECTED` $\to$ `PATCH_COMMITTED`).

### 2.3 Raft Consensus RPC Contracts
- `RequestVoteArgs` & `RequestVoteReply`: Candidate election with log up-to-date validation (`last_log_term` and `last_log_index`).
- `AppendEntriesArgs` & `AppendEntriesReply`: Heartbeat exchange, log replication, conflict truncation at `prev_log_index`, and commit index synchronization.

---

## 3. Integration with Pipeline & Zero-Trust Mesh

1. **`FederatedMeshCoordinator` Integration**:
   - Coordinator embeds `CommitteeRaftNode` initialized with dynamic peer providers and Phase 88 attestation checks.
   - Provides high-level endpoints for election triggers, proposal dispatch, and status telemetry.
2. **`PipelineDebateProtocol` Integration**:
   - When `request.use_raft_consensus` is enabled, deliberation turns and the final `CommitteeConsensusScorecard` are submitted directly to the Raft cluster.
   - `CommitteeDebateRecord` records `raft_log_index` and `raft_term` as cryptographic proof of consensus.
3. **Developer Cockpit & Toolbelt**:
   - `FederatedMeshView.tsx`: Displays Raft role badge, term, commit index, and the real-time replicated ledger timeline with commit verification badges.
   - CLI: `las mesh raft status`, `las mesh raft elect`, and `las mesh raft log` provide immediate operator visibility.

---

## 4. Verification Receipts

- **Phase 89 Dedicated Suite**: `test_committee_raft_p89.py` (9/9 tests PASS).
- **Full Pipeline Regression Matrix**: 12/12 suites PASS (81/81 tests).
- **Frontend Production Build**: Vite build clean (0 errors).
- **Anti-Corruption Principles**: Zero host pollution, typed failures only, deterministic state machine replication.
