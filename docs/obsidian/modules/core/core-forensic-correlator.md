---
tags:
  - architecture/leaf
  - security/forensics
  - audit/correlator
  - layer/l5
type: module_leaf
layer: L5-Security-Sandbox-and-Merkle
module: agent_workspace.core.forensic_correlator
file_path: agent_workspace/core/forensic_correlator.py
sync_status: verified
---

# Module: ForensicCorrelator (Dual-Stream Forensic Correlator)

## 1. Three-Line Architectural Annotation
- **Responsibility**: Unifies and cryptographically correlates two complementary ledgers: [[core-audit-ledger]] (Merkle-chained compliance audit trail) and [[core-sandbox|RuntimeEventsLedger]] (execution plane lifecycle telemetry).
- **Invariant**: Cross-stream session integrity is valid (`is_tamper_free = true`) if and only if both the compliance audit hash chain and the runtime event hash chain verify 100% continuously without breaks.
- **Data Flow**: Consumes events from `audit_ledger.db` and `runtime_events.db`, normalizes them into chronologically ordered `ForensicEventItem` timelines, and emits verifiable `ForensicSessionTimeline` receipts into `.agent/evidence/`.

---

## 2. Source Code & Symbol Mapping

**Source Location**: [forensic_correlator.py](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/forensic_correlator.py) (169 lines)

### Symbol Table

| Symbol | Kind | Line Range | Description |
| :--- | :--- | :--- | :--- |
| ForensicEventItem | class | L26-L39 | Normalized event record spanning compliance audit and runtime execution streams. |
| ForensicSessionTimeline | class | L41-L57 | Complete tamper-evident forensic timeline and cryptographic receipt for an agent session. |
| ForensicCorrelator | class | L59-L168 | Core correlation engine reconciling AuditLedger and RuntimeEventsLedger. |
| `__init__` | def | L62-L65 | Initializes instances of AuditLedger and RuntimeEventsLedger scoped to target workspace. |
| `correlate_session` | def | L67-L153 | Verifies dual hash chains, filters session records, and merges them into sorted timeline. |
| `export_forensic_receipt` | def | L155-L168 | Serializes verified session timeline to JSON receipt on disk (`.agent/evidence/forensic_{session_id}.json`). |

---

## 3. Dual-Stream Forensic Correlation Topology

```mermaid
graph TD
    subgraph AuditStream["Compliance Audit Stream (audit_ledger.db)"]
        A1[Audit Entry 1] --> A2[Audit Entry 2]
        A2 --> A3[Audit Entry 3]
        A_Root[Audit Merkle Root]
    end

    subgraph RuntimeStream["Runtime Execution Stream (runtime_events.db)"]
        R1[Lifecycle Step 1] --> R2[Lifecycle Step 2]
        R2 --> R3[Lifecycle Step 3]
        R_Root[Runtime Merkle Root]
    end

    A2 -. Session Correlated .-> FC[ForensicCorrelator]
    R2 -. Session Correlated .-> FC

    FC --> Timeline[Chronologically Ordered ForensicEventItem[]]
    FC --> Receipt["ForensicSessionTimeline Receipt<br/>(audit_chain_valid && runtime_chain_valid)"]
```

---

## 4. Dependencies & Downstream Consumers
- **Upstream Dependencies**:
  - [[core-audit-ledger]] (`agent_workspace.core.audit_ledger.AuditLedger`)
  - `agent_workspace.core.runtime_events.RuntimeEventsLedger`
- **Downstream Consumers**:
  - [[core-pipeline]] / Coding Pipeline Forensics
  - Forensic Verification Endpoints (`/v1/forensics/session/{session_id}`)
  - Offline Auditing CLI & Forensic Evidence Export
