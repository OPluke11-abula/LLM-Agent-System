# Governance Path Audit: LLM Agent System (LAS)

**Audit Phase**: Phase C — Architecture vs Implementation Consistency  
**Inspection Date**: 2026-09-14  
**Protocol Version**: 3.8.0  
**Authority**: Invariant 0.1 (調研先行 / Anti-Summary Invariant)  

---

## 1. Execution Entry Point Audit

Every mechanism by which an agent or external caller can initiate execution in LAS was mapped and audited:

| Entry Point | Concrete File & Line | Governance Gate Checked | Vulnerability / Bypass Risk |
| :--- | :--- | :--- | :--- |
| **`CodingPipelineManager.execute_pipeline`** | [`pipeline/manager.py:295`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/pipeline/manager.py#L295) | Worktree isolation, `ScopeGuard`, Verification Ladder, Committee Review | Empty `test_strategy` bypasses verification ladder (GAP-05). |
| **`GovernedToolRegistry.filesystem_write`** | [`agent_executor.py:222`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/agent_executor.py#L222) | Path containment within root (`is_relative_to`) | Missing `task_env.is_path_mutable` check on direct registry calls (GAP-03). |
| **`GovernedToolRegistry.shell_exec`** | [`agent_executor.py:241`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/agent_executor.py#L241) | Process execution within worktree directory | Missing `DESTRUCTIVE_COMMAND_PATTERNS` regex filter on direct calls (GAP-03). |
| **`AgentEngine.execute_tool`** | [`engine.py:272`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/engine.py#L272) | Mock tool registry / local tool mapping | Completely bypasses `UnifiedPolicyGate` and `AuditLedger` (GAP-01). |
| **`AgentRouter._execute_tool_with_approval`** | [`router.py:410`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/router.py#L410) | Interactive approval callback prompt | Tool executes without unified policy gate evaluation. |
| **`MissionStateMachine.transition`** | [`mission_state_machine.py:44`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/mission_state_machine.py#L44) | Gate status check (`ApprovalStatus.APPROVED`) | Self-approval allowed: doesn't verify approver != mission author (GAP-02). |
| **`routes/missions.py:record_approval`** | [`routes/missions.py:257`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/routes/missions.py#L257) | Checks mission existence | Any actor can approve any mission without separation of duties (GAP-02). |

---

## 2. Policy Bypass Detection Inventory

Through concrete code trace analysis, the following bypass vectors were identified:

1. **Direct Tool Invocation Bypass**:
   - `AgentExecutor.execute_step` enforces `ScopeGuard.validate_tool_call`.
   - However, if code or a subagent invokes `GovernedToolRegistry.filesystem_write` directly with an unauthorized path (e.g. modifying `.agent/` or outside assigned mutable scope), the method executed without checking `self.guard.task_env.is_path_mutable`.
   - **Fix Required**: Add scope validation into `GovernedToolRegistry` internal methods.

2. **Self-Approval Gate Bypass**:
   - When transitioning from `PLANNING` or `APPROVAL_REQUIRED` to `IN_PROGRESS`, the state machine checks:
     ```python
     gate = next((g for g in mission.approval_gates if g.gate_type == "plan_approval"), None)
     if not gate or gate.status != ApprovalStatus.APPROVED:
         raise MissionTransitionError(...)
     ```
   - An agent with `actor_id="agent-007"` can call `mission.add_approval_gate(ApprovalGate(gate_type="plan_approval", status=ApprovalStatus.APPROVED, actor_id="agent-007"))`.
   - **Fix Required**: Enforce `gate.actor_id != mission.actor_id` across model and state machine.

3. **Empty Test Ladder Bypass**:
   - In `CodingPipelineManager.execute_pipeline`:
     ```python
     receipts = self.run_verification_ladder(...)
     failed_receipts = [r for r in receipts if r.status != "PASS"]
     if not failed_receipts:
         verification_status = VerificationStatus.PASS
     ```
   - If `test_strategy=[]`, `receipts=[]`, `failed_receipts=[]`, yielding `PASS`.
   - **Fix Required**: Explicitly require `len(plan.test_strategy) > 0` and at least 1 PASS receipt.

---

## 3. Negative Governance Test Specification

To programmatically verify these boundaries and prevent regressions, automated negative tests are implemented in [`agent_workspace/tests/test_governance_negative.py`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/tests/test_governance_negative.py):

1. `test_governed_tool_registry_rejects_immutable_path_direct_call`
2. `test_governed_tool_registry_rejects_destructive_command_direct_call`
3. `test_mission_self_approval_prohibited`
4. `test_pipeline_rejects_empty_test_ladder`
5. `test_reviewer_role_rejects_code_modification`
6. `test_terminal_stage_reentry_rejected`
