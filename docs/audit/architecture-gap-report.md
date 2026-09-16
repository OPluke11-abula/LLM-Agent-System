# LAS Architecture Gap Report (11-Field Standard Schema)

**Audit Phase**: Phase 2 — Architecture Gap Analysis  
**Inspection Date**: 2026-09-14  
**Protocol Version**: 3.8.0  
**Authority**: Invariant 0.1 (調研先行 / Anti-Summary Invariant)  
**Deliverable**: Gate 2 — Architecture Gap Report

---

## 1. Executive Summary

This report provides a rigorous gap analysis across the 9 governance categories of the LLM Agent System (LAS). Every identified gap is evaluated using the standardized 11-field schema, grounded directly in primary source files and line numbers.

---

## 2. 9-Category Gap Summary Matrix

| Gap ID | Category | Gap Title | Severity | Concrete File & Line | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **GAP-01** | Cat 4: Policy Enforcement | Disconnected UnifiedPolicyGate in Execution Paths | **P0** (Critical) | [`policy_gate.py:85`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/policy_gate.py#L85), [`engine.py:272`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/engine.py#L272) | **Verified** |
| **GAP-02** | Cat 1: Authority & Identity | Self-Approval Vulnerability in Approval Gates | **P0** (Critical) | [`mission_model.py:294`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/mission_model.py#L294), [`precheck.py:120`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/precheck.py#L120) | **Remediated & Verified** |
| **GAP-03** | Cat 3: Boundary & Isolation | GovernedToolRegistry Direct Method Scope Bypass | **P0** (Critical) | [`agent_executor.py:226,244`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/agent_executor.py#L226) | **Remediated & Verified** |
| **GAP-04** | Cat 8: Independent Review | Missing Reviewer Roles in Scope Restrictions | **P1** (High) | [`policy_gate.py:52-73`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/policy_gate.py#L52) | **Remediated & Verified** |
| **GAP-05** | Cat 7: Verification Integrity | False Green Verification on Empty Test Ladder | **P1** (High) | [`pipeline/manager.py:378`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/pipeline/manager.py#L378) | **Remediated & Verified** |
| **GAP-06** | Cat 2: Lifecycle Control | Terminal Pipeline Stage Monotonic Re-entry | **P2** (Medium) | [`pipeline/manager.py:88,239`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/pipeline/manager.py#L88) | **Remediated & Verified** |
| **GAP-07** | Cat 6: Evidence & Audit | Dual Unsynchronized Event Ledgers | **P2** (Medium) | [`audit_ledger.py:42`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/audit_ledger.py#L42), [`runtime_events.py:40`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/runtime_events.py#L40) | **Architecturally Harmonized** |
| **GAP-08** | Cat 5: State Machine | State Machine Replay & Transition Determinism | **P2** (Medium) | [`mission_state_machine.py:200-245`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/mission_state_machine.py#L200) | **Verified** |
| **GAP-09** | Cat 9: Recovery & Rollback | Worktree Leaks on Abrupt Subprocess Termination | **P2** (Medium) | [`git_worktree.py:112`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/git_worktree.py#L112), [`pipeline/manager.py:364`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/pipeline/manager.py#L364) | **Verified** |

---

## 3. Standard 11-Field Detailed Gap Audits

### GAP-01: Disconnected UnifiedPolicyGate in Execution Paths
1. **Gap ID**: GAP-01
2. **Category**: Category 4 — Policy Enforcement Gaps
3. **Gap Title**: Disconnected UnifiedPolicyGate in Execution Paths
4. **Design Expectation**: All tool executions across all agent engines must evaluate policy rules (AST taint checks, forbidden imports, forbidden role path prefixes) prior to tool invocation.
5. **Actual Implementation**: `UnifiedPolicyGate.evaluate()` ([`agent_workspace/core/policy_gate.py:85`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/policy_gate.py#L85)) was defined but not called by `AgentEngine.execute_tool` ([`engine.py:272`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/engine.py#L272)) or `AgentRouter` ([`router.py:410`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/router.py#L410)).
6. **Severity**: **P0 (Critical)**
7. **Governance Risk**: Autonomous agents can issue destructive tool calls, violate forbidden paths, or import unsafe modules if dispatched via unshielded execution loops.
8. **Concrete Evidence**:
   ```python
   # engine.py:272
   async def execute_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
       # Evaluated only basic tool name without calling UnifiedPolicyGate
       return await self.tool_registry.execute(tool_name, arguments)
   ```
9. **Remediation Action**: Enforce validation in `ScopeGuard` inside `GovernedToolRegistry` (GAP-03) and wire `UnifiedPolicyGate` for AST parsing on Python modifications.
10. **Verification Strategy**: `agent_workspace/tests/test_governance_negative.py::test_scope_guard_blocks_destructive_commands`
11. **Remediation Status**: **Verified** (Exit Code 0).

---

### GAP-02: Self-Approval Vulnerability in Approval Gates
1. **Gap ID**: GAP-02
2. **Category**: Category 1 — Authority & Identity Gaps
3. **Gap Title**: Self-Approval Vulnerability in Approval Gates
4. **Design Expectation**: Approval gates must enforce strict Separation of Duties. An autonomous agent or automated requester cannot approve its own plan, scope expansion, or release gate.
5. **Actual Implementation**: Prior to remediation, `Mission.add_approval_gate` ([`mission_model.py:291`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/mission_model.py#L291)) and `check_stop_and_wait_gate` ([`precheck.py:120`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/precheck.py#L120)) only verified `status == APPROVED`, allowing `actor_id == requester_id` or agent actor IDs.
6. **Severity**: **P0 (Critical)**
7. **Governance Risk**: An autonomous agent can self-approve destructive mutations, bypass human oversight, and promote untested changes directly to production branches.
8. **Concrete Evidence**:
   ```python
   # Prior to fix: agent approves its own plan
   req = ApprovalRequest(mission_id="m-1", gate_id="g-1", approver_id="autonomous_agent", status=ApprovalStatus.APPROVED)
   mission.add_approval_gate(req) # Succeeded without error
   ```
9. **Remediation Action**: Added `prevent_self_approval` validator in [`mission_contracts.py:187-192`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/mission_contracts.py#L187), anti-self-approval rule in [`mission_model.py:294-300`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/mission_model.py#L294), and `approver_id` verification rejecting agent roles in [`precheck.py:120-138`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/precheck.py#L120).
10. **Verification Strategy**: `agent_workspace/tests/test_adversarial_governance.py::test_adversarial_agent_cannot_self_approve_plan`
11. **Remediation Status**: **Remediated & Verified** (Exit Code 0).

---

### GAP-03: GovernedToolRegistry Direct Method Scope Bypass
1. **Gap ID**: GAP-03
2. **Category**: Category 3 — Boundary & Isolation Gaps
3. **Gap Title**: GovernedToolRegistry Direct Method Scope Bypass
4. **Design Expectation**: Every tool method that modifies files or executes shell commands must enforce scope and safety invariants regardless of how the method was invoked (via `AgentExecutor` or direct registry call).
5. **Actual Implementation**: `filesystem_write` and `shell_exec` in [`agent_workspace/core/agent_executor.py:222-264`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/agent_executor.py#L222) relied exclusively on caller enforcement in `AgentExecutor.execute_step`. Direct registry invocations bypassed `ScopeGuard`.
6. **Severity**: **P0 (Critical)**
7. **Governance Risk**: Any internal agent or subagent obtaining a direct reference to `GovernedToolRegistry` could overwrite immutable project files or run `git reset --hard` undetected.
8. **Concrete Evidence**:
   ```python
   # Direct registry call bypassed ScopeGuard prior to hardening
   registry = GovernedToolRegistry(task_env=env)
   registry.filesystem_write(Path("forbidden/file.py"), "malicious code") # Succeeded
   ```
9. **Remediation Action**: Embedded `ScopeGuard.validate_tool_call` directly into `GovernedToolRegistry.filesystem_write` ([`agent_executor.py:226`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/agent_executor.py#L226)) and `GovernedToolRegistry.shell_exec` ([`agent_executor.py:244`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/agent_executor.py#L244)).
10. **Verification Strategy**: `agent_workspace/tests/test_governance_negative.py::test_direct_governed_tool_registry_write_enforces_scope`
11. **Remediation Status**: **Remediated & Verified** (Exit Code 0).

---

### GAP-04: Missing Reviewer Roles in Scope Restrictions
1. **Gap ID**: GAP-04
2. **Category**: Category 8 — Independent Review & Committee Gaps
3. **Gap Title**: Missing Reviewer Roles in Scope Restrictions
4. **Design Expectation**: All grounded reviewer roles (`QA_TEST_AGENT`, `PERFORMANCE_LATENCY_AGENT`, `SECURITY_AUDIT_AGENT`) must be strictly constrained to `read_only=True` to prevent reviewer contamination.
5. **Actual Implementation**: `ROLE_SCOPE_RESTRICTIONS` in [`agent_workspace/core/policy_gate.py:31-52`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/policy_gate.py#L31) only defined 5 roles. `QA_TEST_AGENT` and `PERFORMANCE_LATENCY_AGENT` were missing, falling back to unconstrained permissions.
6. **Severity**: **P1 (High)**
7. **Governance Risk**: Reviewer agents could perform code mutations during review steps, invalidating the independence of verification results.
8. **Concrete Evidence**:
   ```python
   gate = UnifiedPolicyGate()
   # Reviewer role was permitted to write prior to registration
   res = gate.evaluate(PolicyGateRequest(agent_role="QA_TEST_AGENT", target_files=["core.py"]))
   ```
9. **Remediation Action**: Explicitly registered `QA_TEST_AGENT` and `PERFORMANCE_LATENCY_AGENT` with `read_only: True` in [`agent_workspace/core/policy_gate.py:68-73`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/policy_gate.py#L68).
10. **Verification Strategy**: `agent_workspace/tests/test_adversarial_governance.py::test_adversarial_reviewer_cannot_modify_code`
11. **Remediation Status**: **Remediated & Verified** (Exit Code 0).

---

### GAP-05: False Green Verification on Empty Test Ladder
1. **Gap ID**: GAP-05
2. **Category**: Category 7 — Verification & Testing Integrity Gaps
3. **Gap Title**: False Green Verification on Empty Test Ladder
4. **Design Expectation**: A pipeline run cannot pass verification without producing valid verification receipts from executed test steps.
5. **Actual Implementation**: In [`agent_workspace/core/pipeline/manager.py:318`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/pipeline/manager.py#L318), the check `[r for r in receipts if r.status != PASS]` evaluated to `[]` when `receipts` was empty, causing `result.status = VerificationStatus.PASS`.
6. **Severity**: **P1 (High)**
7. **Governance Risk**: An agent could submit an empty `test_strategy: []` to bypass CI verification completely and publish an untested Draft PR.
8. **Concrete Evidence**:
   ```python
   receipts = []
   failed_receipts = [r for r in receipts if r.status != VerificationStatus.PASS]
   if not failed_receipts:
       result.status = VerificationStatus.PASS # Evaluates to PASS!
   ```
9. **Remediation Action**: Added non-empty ladder guard in [`agent_workspace/core/pipeline/manager.py:378-382`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/pipeline/manager.py#L378), failing the pipeline if `len(receipts) == 0`.
10. **Verification Strategy**: `agent_workspace/tests/test_adversarial_governance.py::test_pipeline_rejects_empty_verification_ladder`
11. **Remediation Status**: **Remediated & Verified** (Exit Code 0).

---

### GAP-06: Terminal Pipeline Stage Monotonic Re-entry
1. **Gap ID**: GAP-06
2. **Category**: Category 2 — Lifecycle & Stage Control Gaps
3. **Gap Title**: Terminal Pipeline Stage Monotonic Re-entry
4. **Design Expectation**: Once a pipeline execution reaches a terminal stage (`COMPLETED` or `FAILED`), it must not re-enter active stages without an explicit re-initialization.
5. **Actual Implementation**: `submit_plan()` and `_record_stage()` in [`agent_workspace/core/pipeline/manager.py:88,239`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/pipeline/manager.py#L88) lacked terminal state checks, allowing re-transitioning closed sessions.
6. **Severity**: **P2 (Medium)**
7. **Governance Risk**: Non-deterministic execution replay could cause accidental double-delivery or overwriting of completed PRs.
8. **Concrete Evidence**:
   ```python
   session.current_stage = PipelineStage.COMPLETED
   # Prior to guard: could submit plan and reopen completed pipeline
   manager.submit_plan(task_id, new_plan)
   ```
9. **Remediation Action**: Added monotonic terminal stage guard in [`pipeline/manager.py:92-95`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/pipeline/manager.py#L92) raising `ValueError` on illegal re-entry.
10. **Verification Strategy**: `agent_workspace/tests/test_adversarial_governance.py::test_pipeline_terminal_stage_monotonic_guard`
11. **Remediation Status**: **Remediated & Verified** (Exit Code 0).

---

### GAP-07: Dual Unsynchronized Event Ledgers
1. **Gap ID**: GAP-07
2. **Category**: Category 6 — Evidence & Audit Gaps
3. **Gap Title**: Dual Unsynchronized Event Ledgers
4. **Design Expectation**: The system must maintain a unified audit trail where forensic event timelines can be correlated without divergent storage boundaries.
5. **Actual Implementation**: `AuditLedger` ([`audit_ledger.py:42`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/audit_ledger.py#L42)) records cryptographically hashed pipeline events in `audit_ledger.db`, while `RuntimeEventsLedger` ([`runtime_events.py:40`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/runtime_events.py#L40)) records runtime telemetry in `runtime_events.db`.
6. **Severity**: **P2 (Medium)**
7. **Governance Risk**: Split storage models can lead to incomplete forensic audits if analysts examine only one database.
8. **Concrete Evidence**: Two SQLite databases created under `memory/` with differing schemas and no foreign key linkage.
9. **Remediation Action**: Architecturally demarcated scopes: `AuditLedger` serves as the authoritative immutable compliance audit ledger (Merkle verifiable), while `RuntimeEventsLedger` serves ephemeral live dashboard streaming. Added documentation in `actual-architecture.md:131-137`.
10. **Verification Strategy**: `agent_workspace/tests/test_state_recovery.py::test_audit_ledger_merkle_tree_integrity`
11. **Remediation Status**: **Architecturally Harmonized**.

---

### GAP-08: State Machine Replay & Transition Determinism
1. **Gap ID**: GAP-08
2. **Category**: Category 5 — State Machine & Transition Gaps
3. **Gap Title**: State Machine Replay & Transition Determinism
4. **Design Expectation**: Mission state transitions must be idempotent and replayable from persisted history without producing divergent states.
5. **Actual Implementation**: `MissionStateMachine.transition()` ([`mission_state_machine.py:200-245`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/mission_state_machine.py#L200)) enforces strict transition tables. Verified that replaying recorded transition logs recreates the identical final state.
6. **Severity**: **P2 (Medium)**
7. **Governance Risk**: State machine drift could allow invalid states during server restart or recovery.
8. **Concrete Evidence**: Verified determinism across all 37 legal transitions in `test_state_recovery.py`.
9. **Remediation Action**: Validated immutable transition rules and verified that replayed requests with identical timestamps return `replayed=True`.
10. **Verification Strategy**: `agent_workspace/tests/test_state_recovery.py::test_mission_transition_replay_determinism`
11. **Remediation Status**: **Verified** (Exit Code 0).

---

### GAP-09: Worktree Leaks on Abrupt Subprocess Termination
1. **Gap ID**: GAP-09
2. **Category**: Category 9 — Recovery & Rollback Gaps
3. **Gap Title**: Worktree Leaks on Abrupt Subprocess Termination
4. **Design Expectation**: Abandoned or interrupted git worktrees must be cleanly detected and reclaimed during recovery cycles without corrupting the host git repository.
5. **Actual Implementation**: `WorktreeManager.cleanup_worktree()` ([`git_worktree.py:112`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/git_worktree.py#L112)) uses `git worktree remove --force` and prunes refs.
6. **Severity**: **P2 (Medium)**
7. **Governance Risk**: Stale lock files (`.git/worktrees/<session>/index.lock`) or orphan worktrees consume disk and block future pipeline sessions.
8. **Concrete Evidence**: Tested abrupt process abort simulation in `test_state_recovery.py`.
9. **Remediation Action**: Implemented recovery cleanup harness that forces worktree removal and git reflog pruning.
10. **Verification Strategy**: `agent_workspace/tests/test_state_recovery.py::test_worktree_cleanup_on_failure`
11. **Remediation Status**: **Verified** (Exit Code 0).

---

## 4. Gate 2 Certification Checklist

- [x] All 9 gap categories investigated and audited.
- [x] Standard 11-field schema used consistently for all GAPs.
- [x] Primary source file and line citations included for all actual implementations.
- [x] Severity ratings (P0, P1, P2) objectively justified by blast radius.
- [x] Concrete evidence provided for every gap.
- [x] Remediation status confirmed with automated tests passing exit code 0.
