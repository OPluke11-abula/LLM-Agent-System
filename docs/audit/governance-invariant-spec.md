# LAS Governance Invariant Specification

**Audit Phase**: Phase 3 — Governance & Consistency Validation  
**Inspection Date**: 2026-09-14  
**Protocol Version**: 3.8.0  
**Authority**: Invariant 0.1 (調研先行 / Anti-Summary Invariant)  
**Deliverable**: Gate 3 — Governance Invariant Specification

---

## 1. Governance Invariant Taxonomy

The LLM Agent System (LAS) enforces six (6) non-negotiable core invariants to guarantee that an autonomous agent cannot perform unobservable, unauthorized, unverified, or destructive actions.

$$\text{Governance Integrity} \equiv \bigwedge_{i=1}^{6} \text{Invariant}_i$$

---

## 2. Formal Invariant Specifications

### Invariant 1: No Unobserved Mutation
- **Formal Statement**:
  $$\forall \text{ mutation } m \in \mathcal{M} \implies \exists \text{ event } e \in \mathcal{E} \text{ such that } \text{AuditLedger.record}(e) \wedge \text{Hash}(e) \in \text{HashChain}$$
- **Meaning**: No tool execution that modifies the filesystem, executes a shell command, or mutates a git repository may occur without synchronously appending a cryptographically linked event to `AuditLedger`.
- **Enforcement Point**: [`agent_workspace/core/agent_executor.py:288`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/agent_executor.py#L288), [`agent_workspace/core/pipeline/manager.py:102`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/pipeline/manager.py#L102).
- **Violation Behavior**: Immediate execution abort; untracked operations cause Merkle root mismatch on verification.
- **Verification Proof**: [`agent_workspace/tests/test_state_recovery.py::test_audit_ledger_merkle_tree_integrity`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/tests/test_state_recovery.py#L105) (PASS).

---

### Invariant 2: No Privileged Self-Approval (Separation of Duties)
- **Formal Statement**:
  $$\forall \text{ approval } a = (req, app) \implies (app.\text{actor\_id} \ne req.\text{requester\_id}) \wedge (app.\text{role} \notin \mathcal{R}_{\text{agent}})$$
- **Meaning**: An autonomous agent cannot approve its own plan, scope expansion, or delivery gate. Approvals require an explicit human authority (`approver_id != requester_id`).
- **Enforcement Points**:
  - Model: [`agent_workspace/core/mission_model.py:294-300`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/mission_model.py#L294-L300)
  - Contract: [`agent_workspace/core/mission_contracts.py:187-192`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/mission_contracts.py#L187-L192)
  - Precheck Gate: [`agent_workspace/core/precheck.py:120-138`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/precheck.py#L120-L138)
- **Violation Behavior**: Raises `ValueError("Self-approval is strictly forbidden")` or `GateApprovalRequiredError`.
- **Verification Proof**: [`agent_workspace/tests/test_adversarial_governance.py::test_adversarial_agent_cannot_self_approve_plan`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/tests/test_adversarial_governance.py#L12) (PASS).

---

### Invariant 3: No Unverified Delivery (Verification Non-Emptiness)
- **Formal Statement**:
  $$\text{Deliver}(P) \implies (\mathcal{R}_{\text{verify}} \ne \emptyset) \wedge \left( \forall r \in \mathcal{R}_{\text{verify}}, r.\text{status} = \text{PASS} \wedge r.\text{exit\_code} = 0 \right)$$
- **Meaning**: A coding pipeline run cannot advance to Draft PR publication or completion without executing at least one verification step, and all verification receipts must show exit code 0.
- **Enforcement Point**: [`agent_workspace/core/pipeline/manager.py:378-386`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/pipeline/manager.py#L378-L386).
- **Violation Behavior**: `result.status = VerificationStatus.FAIL`; `error_message = "Verification ladder cannot be empty"`; halts delivery.
- **Verification Proof**: [`agent_workspace/tests/test_adversarial_governance.py::test_pipeline_rejects_empty_verification_ladder`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/tests/test_adversarial_governance.py#L65) (PASS).

---

### Invariant 4: No Direct Main Mutation (Worktree Isolation)
- **Formal Statement**:
  $$\forall \text{ file modification } f \in \mathcal{F}_{\text{mod}} \implies \text{Path}(f) \subseteq \text{Worktree}(\text{session\_id}) \wedge \text{Path}(f) \cap \text{MainRepo} = \emptyset$$
- **Meaning**: All file changes and command executions are isolated within dedicated git worktrees (`.worktrees/<session_id>`). The root repository working directory remains completely immutable.
- **Enforcement Points**:
  - Worktree Creation: [`agent_workspace/core/git_worktree.py:73`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/git_worktree.py#L73)
  - Scope Guard: [`agent_workspace/core/agent_executor.py:187-219`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/agent_executor.py#L187-L219)
- **Violation Behavior**: Raises `PermissionError` or `ValueError("Path outside sandbox root")`.
- **Verification Proof**: [`agent_workspace/tests/test_governance_negative.py::test_scope_guard_blocks_path_traversal`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/tests/test_governance_negative.py#L18) (PASS).

---

### Invariant 5: Monotonic Stage Lifecycle (Terminal State Monotonicity)
- **Formal Statement**:
  $$\text{CurrentStage} \in \{\text{COMPLETED}, \text{FAILED}, \text{CANCELLED}\} \implies \text{NextStage} \notin \{\text{PLAN}, \text{CODE}, \text{VERIFY}, \text{REVIEW}\}$$
- **Meaning**: Once a pipeline execution or mission transitions into a terminal state, it cannot be reopened, mutated, or re-executed without an explicit re-creation.
- **Enforcement Points**:
  - Pipeline Manager: [`agent_workspace/core/pipeline/manager.py:92-95, 239`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/pipeline/manager.py#L92)
  - State Machine: [`agent_workspace/core/mission_state_machine.py:110, 202`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/mission_state_machine.py#L110)
- **Violation Behavior**: Raises `ValueError("Illegal state transition: cannot re-enter active stage from terminal stage")`.
- **Verification Proof**: [`agent_workspace/tests/test_adversarial_governance.py::test_pipeline_terminal_stage_monotonic_guard`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/tests/test_adversarial_governance.py#L82) (PASS).

---

### Invariant 6: Strict Reviewer Isolation (Read-Only Review Boundary)
- **Formal Statement**:
  $$\forall \text{ agent } a \text{ where } a.\text{role} \in \mathcal{R}_{\text{reviewer}} \implies \text{Policy}(a).\text{read\_only} = \text{True} \wedge \mathcal{M}_{\text{allowed}}(a) = \emptyset$$
- **Meaning**: Reviewer and QA agents (`QA_TEST_AGENT`, `PERFORMANCE_LATENCY_AGENT`, `SECURITY_AUDIT_AGENT`) have zero write or mutation privileges.
- **Enforcement Point**: [`agent_workspace/core/policy_gate.py:52-73`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/policy_gate.py#L52-L73).
- **Violation Behavior**: `UnifiedPolicyGate.evaluate()` returns `allowed = False` with `denial_reason = "Reviewer role ... is strictly read-only"`.
- **Verification Proof**: [`agent_workspace/tests/test_adversarial_governance.py::test_adversarial_reviewer_cannot_modify_code`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/tests/test_adversarial_governance.py#L45) (PASS).

---

## 3. Invariant Enforcement Summary

| Invariant | Primary Source Code | Enforcement Type | Automated Test Coverage | Gate Status |
| :--- | :--- | :--- | :--- | :--- |
| **Inv 1: No Unobserved Mutation** | `agent_executor.py:288` | Synchronous Audit Recording | `test_state_recovery.py` | **ENFORCED** |
| **Inv 2: No Self-Approval** | `mission_model.py:294` | Model & Schema Validator | `test_adversarial_governance.py` | **ENFORCED** |
| **Inv 3: No Unverified Delivery** | `pipeline/manager.py:378` | Pipeline Guardrail | `test_adversarial_governance.py` | **ENFORCED** |
| **Inv 4: No Direct Main Mutation** | `git_worktree.py:73` | Git Worktree Isolation | `test_governance_negative.py` | **ENFORCED** |
| **Inv 5: Monotonic Lifecycle** | `pipeline/manager.py:92` | State Machine Guard | `test_adversarial_governance.py` | **ENFORCED** |
| **Inv 6: Strict Reviewer Isolation** | `policy_gate.py:68` | Policy Gate Role Rule | `test_adversarial_governance.py` | **ENFORCED** |
