# LAS Optimization Decisions: 9-Question Decision Framework

**Audit Phase**: Phase 7 — Optimization, Hardening & Final Report  
**Inspection Date**: 2026-09-14  
**Protocol Version**: 3.8.0  
**Authority**: Invariant 0.1 (調研先行 / Anti-Summary Invariant)  
**Deliverable**: Gate 7 — Optimization Decisions

---

## 1. Governance Decision Framework

In accordance with Section 14 of the LAS Optimization Plan and Protocol 3.8.0 § 0.3, every modification made to the codebase is evaluated and justified against the standard **9-Question Decision Framework**:

1. **Problem**: What problem does this change solve?
2. **Observed Vulnerability**: What concrete failure or vulnerability was observed?
3. **Minimal Change**: What is the minimal change that solves this problem?
4. **Blast Radius**: What are the side effects or blast radius?
5. **No Speculative Code**: Does this introduce dead code or speculative features?
6. **Backwards Compatibility**: Is this backwards-compatible with existing contracts?
7. **Automated Proof**: How do automated tests prove this change works?
8. **Failure Handling**: What failure modes exist, and how are they handled?
9. **Anti-Corruption Compliance**: Does this comply with the 7 Universal Anti-Corruption Principles?

---

## 2. Hardening Decision Log

### DEC-01: Direct GovernedToolRegistry Scope Guard Enforcement
1. **Problem**: Direct tool registry invocations bypassed ScopeGuard boundary checks.
2. **Observed Vulnerability**: A caller or subagent holding a reference to `GovernedToolRegistry` could directly call `filesystem_write` or `shell_exec` without path whitelist or destructive command checks (GAP-03).
3. **Minimal Change**: Inserted `self.guard.validate_tool_call` directly inside `GovernedToolRegistry.filesystem_write` ([`agent_executor.py:226`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/agent_executor.py#L226)) and `shell_exec` ([`agent_executor.py:244`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/agent_executor.py#L244)).
4. **Blast Radius**: Zero breaking changes. Only unauthorized direct writes/commands are intercepted.
5. **No Speculative Code**: Zero dead code; uses existing `ScopeGuard.validate_tool_call` method.
6. **Backwards Compatibility**: 100% compatible with existing callers and tests.
7. **Automated Proof**: `agent_workspace/tests/test_governance_negative.py::test_direct_governed_tool_registry_write_enforces_scope` (PASS).
8. **Failure Handling**: Raises typed `PermissionError` when scope is violated.
9. **Anti-Corruption Compliance**: Enforces Principle 2 (Extreme Single Responsibility) and Principle 4 (Typed Failures Only).

---

### DEC-02: Separation of Duties & Anti-Self-Approval Enforcement
1. **Problem**: Autonomous agents could self-approve their own plans and scope expansion gates.
2. **Observed Vulnerability**: Agents could set `actor_id="autonomous_agent"` and approve their own mission approval gates, bypassing human sign-off (GAP-02).
3. **Minimal Change**:
   - Added `prevent_self_approval` validator in [`mission_contracts.py:187`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/mission_contracts.py#L187).
   - Added anti-self-approval rule rejecting agent actor IDs in [`mission_model.py:294`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/mission_model.py#L294).
   - Enforced human approver verification in `check_stop_and_wait_gate` ([`precheck.py:120`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/precheck.py#L120)).
4. **Blast Radius**: Rejects only self-approvals and agent-role approvals. Valid human approvals proceed normally.
5. **No Speculative Code**: No new external auth frameworks or PGP dependencies added.
6. **Backwards Compatibility**: Preserves all existing human-approved test suites.
7. **Automated Proof**: `agent_workspace/tests/test_adversarial_governance.py::test_adv_05_self_approval_attack` (PASS).
8. **Failure Handling**: Raises `ValueError("Self-approval is strictly forbidden")` or `GateApprovalRequiredError`.
9. **Anti-Corruption Compliance**: Enforces Principle 5 (Specification-First) and Principle 6 (Idempotence & Side-Effect Safety).

---

### DEC-03: Register Grounded Reviewer Roles with Strict Read-Only Policies
1. **Problem**: Missing reviewer roles in scope restrictions allowed reviewer agents to issue code mutations.
2. **Observed Vulnerability**: Roles `QA_TEST_AGENT` and `PERFORMANCE_LATENCY_AGENT` defaulted to unconstrained permissions (GAP-04).
3. **Minimal Change**: Explicitly registered `QA_TEST_AGENT` and `PERFORMANCE_LATENCY_AGENT` with `read_only: True` in `ROLE_SCOPE_RESTRICTIONS` ([`policy_gate.py:68-73`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/policy_gate.py#L68-L73)).
4. **Blast Radius**: Only restricts reviewer roles. Zero impact on developer roles (`DOMAIN_LOGIC_AGENT`, etc.).
5. **No Speculative Code**: Populated existing dictionary configuration.
6. **Backwards Compatibility**: 100% backwards-compatible.
7. **Automated Proof**: `agent_workspace/tests/test_adversarial_governance.py::test_adv_06_reviewer_contamination_attack` (PASS).
8. **Failure Handling**: Intercepted by `ScopeGuard` raising `ScopeExpansionRequest` with `"Reviewer role is strictly read-only"`.
9. **Anti-Corruption Compliance**: Enforces Principle 7 (Configuration over Hardcoding).

---

### DEC-04: Non-Empty Verification Ladder Guard
1. **Problem**: Empty test strategies produced false-positive green status and generated unverified Draft PRs.
2. **Observed Vulnerability**: When `plan.test_strategy = []`, `receipts = []`, `failed_receipts = []`, causing `result.status = VerificationStatus.PASS` (GAP-05).
3. **Minimal Change**: Added `if not receipts:` check in [`pipeline/manager.py:378`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/pipeline/manager.py#L378), setting `result.status = FAIL`.
4. **Blast Radius**: Blocks delivery only when zero verification steps are executed.
5. **No Speculative Code**: Simple 5-line guard.
6. **Backwards Compatibility**: All pipelines with valid test strategies continue to pass.
7. **Automated Proof**: `agent_workspace/tests/test_adversarial_governance.py::test_pipeline_rejects_empty_verification_ladder` (PASS).
8. **Failure Handling**: Pipeline transitions to `FAILED` with explicit error `"Verification ladder cannot be empty"`.
9. **Anti-Corruption Compliance**: Enforces Principle 5 (Specification-First) and "Evidence Before Completion".

---

### DEC-05: Terminal Stage Monotonic Transition Guard
1. **Problem**: Pipeline executions in terminal stages could be re-opened or re-executed.
2. **Observed Vulnerability**: Pipeline manager allowed submitting plans or transitioning stages after reaching `COMPLETED` or `FAILED` (GAP-06).
3. **Minimal Change**: Added monotonic check in `_record_stage` ([`pipeline/manager.py:92-95`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/pipeline/manager.py#L92)).
4. **Blast Radius**: Only affects illegal re-entry attempts into terminal pipeline sessions.
5. **No Speculative Code**: Re-uses existing enum states.
6. **Backwards Compatibility**: Normal linear pipelines are untouched.
7. **Automated Proof**: `agent_workspace/tests/test_adversarial_governance.py::test_pipeline_terminal_stage_monotonic_guard` (PASS).
8. **Failure Handling**: Raises `ValueError("Illegal state transition: cannot re-enter active stage from terminal stage")`.
9. **Anti-Corruption Compliance**: Enforces Principle 6 (Idempotence & Side-Effect Safety).

---

### DEC-06: Protocol Version & PAP Tool Manifest Parity
1. **Problem**: Protocol baseline was outdated (3.7.0 vs 3.8.0), and tool manifest had schema mismatches.
2. **Observed Vulnerability**: `verify.ps1` failed on PAP validation due to missing `generate_spec.md` and version mismatch.
3. **Minimal Change**:
   - Updated baseline in `pap_validate.py` to `3.8.0`.
   - Added schema validation support in `workflow_lint.py`.
   - Added backward-compatible alias and created `.agent/skills/generate_spec.md`.
4. **Blast Radius**: Internal verification tools only.
5. **No Speculative Code**: Fulfills exact specifications of Protocol 3.8.0.
6. **Backwards Compatibility**: 100% compatible with existing scripts.
7. **Automated Proof**: `.\scripts\verify.ps1` completes Steps 1 through 8 with Exit Code 0.
8. **Failure Handling**: Clear typed validation errors on contract mismatch.
9. **Anti-Corruption Compliance**: Enforces Principle 1 (Zero Dead Code) and Principle 7 (Configuration over Hardcoding).
