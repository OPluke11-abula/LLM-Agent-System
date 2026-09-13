---
tags:
  - architecture/leaf
  - security/policy
  - rbac/governance
  - layer/l5
type: module_leaf
layer: L5-Security-Sandbox-and-Merkle
module: agent_workspace.core.policy_gate
file_path: agent_workspace/core/policy_gate.py
sync_status: verified
---

# Module: UnifiedPolicyGate (RBAC, Role Scope & Consensus Evaluator)

## 1. Three-Line Architectural Annotation
- **Responsibility**: Gatekeeper evaluating tool invocation authorization, file path mutation boundaries per role, and multi-agent consensus validation.
- **Invariant**: High-risk tool calls (e.g., shell execution, state modification) require either an active human approval token or a verified multi-signature consensus proof.
- **Data Flow**: Intercepts requests from [[core-router]], matches requested files against ROLE_SCOPE_RESTRICTIONS, computes SHA256 payload hashes, and logs audit events to [[core-audit-ledger]].

---

## 2. Source Code & Symbol Mapping

**Source Location**: [policy_gate.py](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/policy_gate.py) (204 lines)

### Symbol Table

| Symbol | Kind | Line Range | Description |
| :--- | :--- | :--- | :--- |
| ROLE_SCOPE_RESTRICTIONS | dict | L16-L45 | Authoritative glob pattern mapping restricting each of the 10 roles to its mutable boundary. |
| PolicyGateRequest | class | L55-L68 | Pydantic model encapsulating incoming request (	ool_name,
ole, 	arget_files, consensus_proof, payload). |
| PolicyGateDecision | class | L71-L82 | Pydantic model representing verdict (allowed,
eason,
equires_hitl, payload_hash). |
| UnifiedPolicyGate | class | L85-L204 | Policy evaluation engine applying hierarchical security rules. |
| payload_hash_for | def | L94-L100 | Computes deterministic SHA256 hex digest of tool arguments payload. |
| evaluate | def | L102-L132 | Core decision algorithm checking RBAC whitelist, role scope boundaries, and cryptographic consensus. |
| _validate_scope | def | L134-L171 | Checks each target file against role allowed glob patterns using
nmatch. |
| _has_valid_consensus | def | L173-L179 | Verifies whether the request carries a valid consensus certificate from [[core-discussion-room]]. |
| _record_decision | def | L181-L204 | Records the gate decision to the persistent audit ledger with decision metadata. |

---

## 3. Decision Evaluation Flowchart

`mermaid
flowchart TD
    Req([Incoming PolicyGateRequest]) --> ScopeCheck{Target files match<br/>Role Scope Patterns?}
    ScopeCheck -- No --> DenyScope[Decision: DENIED<br/>Reason: Role Boundary Violation]
    ScopeCheck -- Yes --> ToolCheck{Is Tool High-Risk?<br/>bash, write_file, git_push}
    ToolCheck -- No --> AllowSafe[Decision: ALLOWED<br/>Low-Risk Read Tool]
    ToolCheck -- Yes --> ConsensusCheck{Valid Consensus Proof<br/>or Admin HITL Token?}
    ConsensusCheck -- Yes --> AllowVerified[Decision: ALLOWED<br/>Cryptographically Verified]
    ConsensusCheck -- No --> DenyGate[Decision: DENIED / REQUIRES_HITL<br/>Missing Consensus/Token]

    DenyScope --> Record[Log Decision to Audit Ledger]
    AllowSafe --> Record
    AllowVerified --> Record
    DenyGate --> Record
    Record --> Ret([Return PolicyGateDecision])
`

---

## 4. Operational Invariants & Anti-Corruption Guardrails
1. **Strict Default-Deny**: Any tool or target file not explicitly permitted by role configuration is rejected by default.
2. **Deterministic Payload Hashing**: All evaluated requests are indexed by their SHA256 payload hash to prevent replay attacks and race condition swaps.
3. **No Silent Overrides**: Gating decisions cannot be bypassed in production mode; developer overrides require setting RUNTIME_ENVIRONMENT=test.

---

## 5. Verification & Test Evidence
- **Test Suites**:
  - [	est_policy_gate.py](file:///d:/GitHub/LLM-Agent-System/agent_workspace/tests/test_policy_gate.py)
  - [	est_rbac.py](file:///d:/GitHub/LLM-Agent-System/agent_workspace/tests/test_rbac.py)
- **Execution Receipt**: Bytecode validated via compileall exit code 0.

---

## 6. Topological Linkage
- **Upstream Layer**: [[L5-Security-Sandbox-and-Merkle]]
- **Control Plane**: [[10 7-Layer System Architecture & Control Plane Topology]]
- **Collaborating Modules**:
  - [[core-router]]
  - [[core-agent-crew]]
  - [[core-audit-ledger]]
  - [[core-discussion-room]]
