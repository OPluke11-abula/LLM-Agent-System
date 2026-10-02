---
tags:
  - architecture/leaf
  - security/audit
  - merkle/zk
  - layer/l5
type: module_leaf
layer: L5-Security-Sandbox-and-Merkle
module: agent_workspace.core.audit_ledger
file_path: agent_workspace/core/audit_ledger.py
sync_status: verified
---

# Module: AuditLedger (Cryptographic Audit Ledger & Consensus Daemon)

## 1. Three-Line Architectural Annotation
- **Responsibility**: Tamper-evident, append-only cryptographic event ledger maintaining SHA256 block hash chains, Merkle inclusion proofs, and Zero-Knowledge (ZK) integrity proofs.
- **Invariant**: Every recorded event must link to the prior event's hash (prev_hash); any modification to historical rows invalidates the entire hash chain verification.
- **Data Flow**: Receives events from [[core-router]], [[core-policy-gate]], and [[core-discussion-room]], persists records to SQLite, and synchronizes across nodes via AuditConsensusDaemon.

---

## 2. Source Code & Symbol Mapping

**Source Location**: [audit_ledger.py](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/audit_ledger.py) (681 lines)

### Symbol Table

| Symbol | Kind | Line Range | Description |
| :--- | :--- | :--- | :--- |
| AuditLedger | class | L19-L419 | Primary ledger managing hash chain integrity, Merkle trees, and certificate revocations. |
| `_init_db` | def | L43-L76 | Initializes SQLite schema for events, Merkle trees, and certificate revocation lists. |
| `record_event` | def | L78-L108 | Appends a new event with timestamp, payload hash, and computed chained SHA256 hash. |
| `verify_chain_integrity` | def | L110-L157 | Iterates through historical blocks verifying cryptographic continuity of hash pointers. |
| `get_logs` / `get_logs_after` | def | L159-L206 | Queries event records with optional pagination and timestamp watermarks. |
| `generate_merkle_proof` | def | L224-L291 | Constructs Merkle tree over a block of events and returns inclusion proof for an event ID. |
| `verify_merkle_proof` | def | L294-L314 | Verifies Merkle inclusion proof against a verified root hash. |
| `generate_zk_proof` | def | L316-L356 | Generates non-interactive zero-knowledge proof of ledger integrity without exposing event contents. |
| `verify_zk_proof` | def | L359-L373 | Verifies ZK validity proof. |
| `revoke_certificate` / `reinstate` | def | L375-L398 | Manages mTLS certificate revocation status for quarantined nodes. |
| AuditConsensusDaemon | class | L425-L681 | Background peer-to-peer consensus daemon syncing audit state across the swarm. |
| `broadcast_status` | def | L480-L493 | Emits local ledger head hash to gossip network for peer verification. |
| `process_ping` / `process_response` | def | L512-L681 | Handles gossip reconciliation and consensus voting for ledger synchronization. |

---

## 3. Cryptographic Chain & Merkle Tree Topology

`mermaid
graph TD
    subgraph HashChain[Append-Only SHA256 Hash Chain]
        E1[Event 001<br/>prev: 00000000] --> E2[Event 002<br/>prev: hash(E1)]
        E2 --> E3[Event 003<br/>prev: hash(E2)]
        E3 --> E4[Event 004<br/>prev: hash(E3)]
    end

    subgraph MerkleProof[Merkle Tree Aggregation]
        H1[Hash E1] --> H12[Hash 1-2]
        H2[Hash E2] --> H12
        H3[Hash E3] --> H34[Hash 3-4]
        H4[Hash E4] --> H34
        H12 --> Root[Merkle Root Hash]
        H34 --> Root
    end
`

---

## 4. Operational Invariants & Anti-Corruption Guardrails
1. **Append-Only Immutability**: Historical records in audit_events cannot be updated or deleted; any attempt triggers immediate database constraint violations.
2. **Chain Verification on Startup**: The ledger verifies the full chain hash on initialization; corrupted chains trigger system lockdown.
3. **Quarantine Propagation**: A revoked certificate is propagated across peers within 2 gossip intervals.

---

## 5. Verification & Test Evidence
- **Test Suites**:
  - [	est_sandbox_audit.py](file:///d:/GitHub/LLM-Agent-System/agent_workspace/tests/test_sandbox_audit.py)
  - [	est_zk_ledger.py](file:///d:/GitHub/LLM-Agent-System/agent_workspace/tests/test_zk_ledger.py)
  - [	est_mtls_rotation.py](file:///d:/GitHub/LLM-Agent-System/agent_workspace/tests/test_mtls_rotation.py)
- **Execution Receipt**: Bytecode validated via compileall exit code 0.

---

## 6. Topological Linkage
- **Upstream Layer**: [[L5-Security-Sandbox-and-Merkle]]
- **Control Plane**: [[10 7-Layer System Architecture & Control Plane Topology]]
- **Quality Ledger**: [[50 Verification Matrix & Quality Receipt Ledger]]
- **Collaborating Modules**:
  - [[core-policy-gate]]
  - [[core-sandbox]]
  - [[core-discussion-room]]
