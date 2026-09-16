# LAS State Machine Specification

**Audit Phase**: Phase 4 — State Machine, Event & Recovery Validation  
**Inspection Date**: 2026-09-14  
**Protocol Version**: 3.8.0  
**Authority**: Invariant 0.1 (調研先行 / Anti-Summary Invariant)  
**Deliverable**: Gate 4 — State Machine Specification

---

## 1. Overview & State Architecture

The LLM Agent System (LAS) maintains two synchronized, deterministic state machines:
1. **Mission Aggregate State Machine** ([`agent_workspace/core/mission_state_machine.py`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/mission_state_machine.py)): Governs multi-agent task lifecycles, human approval gates, budget enforcement, and review transitions.
2. **Coding Pipeline Stage Model** ([`agent_workspace/core/pipeline/manager.py`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/pipeline/manager.py)): Governs the 5-stage software delivery pipeline (Plan -> Code -> Verify -> Review -> Deliver).

---

## 2. Mission Aggregate State Machine

### 2.1 State Space Definition

| State Enum | State Type | Description |
| :--- | :--- | :--- |
| `DRAFT` | Initial | Mission defined but planning has not started. |
| `PLANNING` | Active | Agent formulating implementation plan and resource budget. |
| `AWAITING_APPROVAL` | Gate | Plan submitted; execution paused waiting for human PO approval. |
| `RUNNING` | Active | Plan approved; agent executing tools and code modifications. |
| `NEEDS_DECISION` | Gate | Execution encountered ambiguous scope; requires PO decision. |
| `SCOPE_BLOCKED` | Blocked | Scope expansion rejected; execution blocked pending resolution. |
| `VERIFYING` | Active | Code modifications complete; verification ladder running. |
| `CI_FAILED` | Remediation | Verification tests failed; entering self-healing or retry. |
| `REVIEW_READY` | Gate | Verification passed; review committee evaluating consensus. |
| `DRAFT_PR_CREATED` | Gate | Draft PR published; awaiting final PO merge approval. |
| `PAUSED` | Suspended | Operator manually paused mission execution. |
| `CLOSED` | **Terminal** | Mission successfully delivered and archived. |
| `CANCELLED` | **Terminal** | Operator or policy aborted mission execution. |
| `FAILED` | **Terminal** | Mission unrecoverably failed or violated invariants. |
| `BUDGET_EXHAUSTED` | **Terminal** | Token or financial budget ceiling exceeded. |

### 2.2 Formal Mission Transition Table

The state machine implements 37 legal transitions mapped in `_LEGAL_TRANSITIONS` ([`mission_state_machine.py:57-108`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/mission_state_machine.py#L57-L108)):

| Current State | Event Trigger | Target State | Guard Conditions & Validators |
| :--- | :--- | :--- | :--- |
| `DRAFT` | `START_PLANNING` | `PLANNING` | Valid initial parameters, non-empty intent. |
| `DRAFT` | `CANCEL` | `CANCELLED` | Cancellation reason supplied. |
| `PLANNING` | `SUBMIT_PLAN` | `AWAITING_APPROVAL` | Requires valid `PlanApprovalSubject` and token estimate. |
| `PLANNING` | `EXHAUST_BUDGET` | `BUDGET_EXHAUSTED` | Budget ceiling reached. |
| `PLANNING` | `FAIL` | `FAILED` | Unhandled error in planning. |
| `AWAITING_APPROVAL` | `APPROVE_PLAN` | `RUNNING` | `approver_id != requester_id`, human authority verified. |
| `AWAITING_APPROVAL` | `REJECT_PLAN` | `PLANNING` | Returns feedback to agent for replanning. |
| `RUNNING` | `BEGIN_VERIFICATION` | `VERIFYING` | Worktree mutations completed. |
| `RUNNING` | `REQUEST_SCOPE_EXPANSION`| `NEEDS_DECISION` | Scope expansion payload provided. |
| `NEEDS_DECISION` | `APPROVE_SCOPE` | `RUNNING` | Human approves requested file globs. |
| `NEEDS_DECISION` | `REJECT_SCOPE` | `PLANNING` | Agent forced to replan within original scope. |
| `VERIFYING` | `COMPLETE_VERIFICATION`| `REVIEW_READY` | All verification ladder steps exit code 0. |
| `VERIFYING` | `FAIL_CI` | `CI_FAILED` | At least one test failure recorded. |
| `CI_FAILED` | `RETRY_VERIFICATION` | `VERIFYING` | Self-healing patch applied. |
| `REVIEW_READY` | `CREATE_DRAFT_PR` | `DRAFT_PR_CREATED` | Committee score $\ge$ threshold (unanimous/majority). |
| `DRAFT_PR_CREATED` | `CLOSE` | `CLOSED` | Human PO signs off on delivery. |
| `* (Active)` | `PAUSE` | `PAUSED` | Suspends active processes. |
| `* (Active)` | `CANCEL` | `CANCELLED` | Aborts execution; triggers worktree cleanup. |

### 2.3 Terminal State Invariants

Terminal states are strictly defined by `_TERMINAL_STATES = {CLOSED, CANCELLED, FAILED, BUDGET_EXHAUSTED}` ([`mission_state_machine.py:110`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/mission_state_machine.py#L110)):
- **Irreversibility**: Any transition request where `current_state \in _TERMINAL_STATES` raises `MissionTransitionError(TransitionErrorCode.ILLEGAL_TRANSITION)`.
- **Idempotent Replay**: If a transition request is received that matches the last recorded transition in `transition_history` (same event, same timestamp, same subject), the machine returns `replayed=True` without mutating state.

---

## 3. Coding Pipeline Stage Model

### 3.1 Stage Progression & Monotonicity

The pipeline operates across 5 linear stages plus terminal states:

$$\text{PLAN} \longrightarrow \text{ISOLATED\_MUTATION} \longrightarrow \text{VERIFY\_AND\_EVIDENCE} \longrightarrow \text{COMMITTEE\_REVIEW} \longrightarrow \text{DRAFT\_PR\_EXPORT} \longrightarrow \text{COMPLETED}$$

If any step fails and self-healing is exhausted, the pipeline transitions to `FAILED`.

### 3.2 Monotonic Transition Guard

Implemented in [`agent_workspace/core/pipeline/manager.py:92-95`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/pipeline/manager.py#L92):
```python
if result.current_stage in (PipelineStage.COMPLETED, PipelineStage.FAILED) and stage not in (PipelineStage.COMPLETED, PipelineStage.FAILED):
    raise ValueError(
        f"Illegal state transition: cannot re-enter active stage '{stage.value}' from terminal stage '{result.current_stage.value}'"
    )
```

This prevents accidental re-execution, double delivery, or state corruption after pipeline termination.
