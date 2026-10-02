# LAS Event Integrity Report: State-to-Event Mapping & Cryptographic Proofs

**Audit Phase**: Phase 4 — State Machine, Event & Recovery Validation  
**Inspection Date**: 2026-09-14  
**Protocol Version**: 3.8.0  
**Authority**: Invariant 0.1 (調研先行 / Anti-Summary Invariant)  
**Deliverable**: Gate 4 — Event Integrity Report

---

## 1. State Change to Event Mapping

Every state transition in LAS generates a strictly typed audit event synchronously recorded in `AuditLedger` ([`agent_workspace/core/audit_ledger.py:42`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/audit_ledger.py#L42)):

$$\text{State Machine Transition} \xrightarrow{\quad \text{Synchronous} \quad} \text{Audit Event} \xrightarrow{\quad \text{SHA-256} \quad} \text{Cryptographic Hash Chain}$$

### 1.1 Complete State-to-Event Audit Table

| Source State | Target State | Event Type | Recorded Payload Content | AuditLedger Stage |
| :--- | :--- | :--- | :--- | :--- |
| `DRAFT` | `PLANNING` | `PLANNING_STARTED` | Mission ID, requirement prompt, actor ID | `PLAN` |
| `PLANNING` | `AWAITING_APPROVAL` | `PLAN_SUBMITTED` | Target files, dependency budget, test strategy | `PLAN` |
| `AWAITING_APPROVAL`| `RUNNING` | `PLAN_APPROVED` | Human approver ID, gate ID, approval timestamp | `PLAN` |
| `RUNNING` | `RUNNING` | `TOOL_EXECUTION` | Tool name, parameters, execution exit code, duration | `CODE` |
| `RUNNING` | `NEEDS_DECISION` | `SCOPE_EXPANSION_REQUESTED`| Requested additional file paths, rationale | `CODE` |
| `NEEDS_DECISION` | `RUNNING` | `SCOPE_EXPANSION_APPROVED` | Human approver ID, updated allowed globs | `CODE` |
| `RUNNING` | `VERIFYING` | `VERIFICATION_LADDER_START`| Test command sequence, working directory | `VERIFY` |
| `VERIFYING` | `REVIEW_READY` | `VERIFICATION_LADDER_PASSED`| List of `VerificationReceipt` records (exit code 0) | `VERIFY` |
| `VERIFYING` | `CI_FAILED` | `VERIFICATION_LADDER_FAILED`| Failed step names, stderr excerpts, return codes | `VERIFY` |
| `REVIEW_READY` | `DRAFT_PR_CREATED` | `DRAFT_PR_PUBLISHED` | Commit SHA, branch name, PR URL, diff stat | `DELIVER` |
| `*` | `FAILED` | `PIPELINE_FAILED` | Error message, traceback, stage of failure | `FAILED` |

---

## 2. Cryptographic Hash Chain & Merkle Root Proofs

### 2.1 Sequential Hash Chain Guarantee

Each event row in `audit_events` stores `(prev_hash, current_hash)` where:

$$\text{current\_hash} = \text{SHA-256}\left( \text{prev\_hash} + \text{timestamp} + \text{json\_payload} \right)$$

- First event in a session uses `prev_hash = "0" * 64`.
- Every subsequent event cryptographically seals the previous event.
- Any manual SQL update, deletion, or out-of-order insertion alters the computed hash and breaks the chain.

### 2.2 Merkle Root Aggregation

`AuditLedger.calculate_merkle_root(session_id)` ([`audit_ledger.py:155`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/audit_ledger.py#L155)) computes a balanced binary Merkle tree over all session hashes:
- Leaf nodes: $\mathcal{L}_i = \text{event}_i.\text{current\_hash}$.
- Parent nodes: $\mathcal{P} = \text{SHA-256}(\mathcal{L}_{2k} + \mathcal{L}_{2k+1})$.
- Merkle Root: Unique 64-character hexadecimal signature representing the exact immutable execution history.

### 2.3 Verification Algorithm & Tamper Detection

`AuditLedger.verify_chain_integrity(session_id)` ([`audit_ledger.py:180`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/audit_ledger.py#L180)):
1. Queries all events for `session_id` ordered by row ID.
2. Recomputes expected SHA-256 for each event from stored fields.
3. Compares expected hash with recorded `current_hash`.
4. Compares `event[i].prev_hash` with `event[i-1].current_hash`.
5. Returns `(True, "OK")` if uncorrupted, or `(False, "Hash chain broken at event X")`.

**Automated Proof**: Tested in [`agent_workspace/tests/test_state_recovery.py::test_audit_ledger_merkle_tree_integrity`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/tests/test_state_recovery.py#L105) (PASS).

---

## 3. Zero Event Loss Guarantee

1. **Transactional SQLite Writes**:
   - `AuditLedger.record_event()` uses explicit `conn.commit()` after every insert.
   - WAL (Write-Ahead Logging) mode ensures immediate on-disk durability.
2. **Crash Resilience**:
   - Even if a Python process terminates abruptly during tool execution, previously committed events remain durable on disk.
   - The hash chain remains intact up to the exact millisecond of the crash.
