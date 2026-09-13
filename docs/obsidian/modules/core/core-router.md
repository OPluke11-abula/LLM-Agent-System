---
tags:
  - architecture/leaf
  - gateway/routing
  - dispatch/orchestration
  - layer/l2
type: module_leaf
layer: L2-Protocol-and-Contract-Gateways
module: agent_workspace.core.router
file_path: agent_workspace/core/router.py
sync_status: verified
---

# Module: AgentRouter (Intent Dispatch & Tool Routing Gateway)

## 1. Three-Line Architectural Annotation
- **Responsibility**: Ingress gateway classifying incoming user and system intents, evaluating RBAC permissions, and orchestrating single-turn or streaming tool calling loops.
- **Invariant**: Every mutating tool execution requires approval clearance via _wait_for_approval and passes through [[core-policy-gate]] before dispatch.
- **Data Flow**: Accepts prompt payloads, interacts with [[core-providers]] for inference, intercepts tool calls via _handle_tool_calls, and maintains conversation state via MemoryManager.

---

## 2. Source Code & Symbol Mapping

**Source Location**: [
outer.py](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/router.py) (1715 lines)

### Symbol Table

| Symbol | Kind | Line Range | Description |
| :--- | :--- | :--- | :--- |
| ToolValidationError | class | L28-L30 | Raised when a tool call payload violates contract JSON schema. |
| ApprovalDeniedError | class | L33-L35 | Raised when human-in-the-loop (HITL) rejects tool execution. |
| SwarmRouteRegistry | class | L41-L149 | Maintains dynamic routing table mapping task classifications to swarm role handlers. |
| MemoryManager | class | L159-L209 | Manages conversation turn persistence and sliding window context limits. |
| TemplateWatcher | class | L212-L246 | File watcher monitoring hot-reloadable system prompt templates on disk. |
| AgentRouter | class | L249-L1715 | Primary routing orchestrator handling intent detection, HITL approvals, and agent loops. |
| pause_session /
esume_session | def | L255-L263 | Session lifecycle controls to pause or unfreeze active agent streams. |
| _wait_for_approval | def | L335-L404 | HITL gating mechanism blocking tool execution until human approval token is provided. |
|
esolve_approval | def | L405-L409 | Signals pending approval future with APPROVED or DENIED. |
| _execute_tool_with_approval | def | L410-L445 | Wraps tool execution with audit recording and policy enforcement. |
| list_skills | def | L464-L498 | Enumerates discoverable tools and skills registered in spec/. |
|
alidate_call | def | L534-L632 | Strict validation of incoming tool arguments against JSON schema contracts. |
| _classify_intent | def | L692-L743 | Zero-shot / rule-based intent classifier assigning requests to specific agent roles. |
|
un_agent_loop | def | L745-L779 | Synchronous multi-turn ReAct loop driving tool invocation and reflection. |
| stream_agent_loop | def | L1250-L1276 | Asynchronous streaming generator yielding token chunks and intermediate tool events. |
| _handle_tool_calls | def | L1182-L1248 | Executes vetted tool invocations inside sandbox boundaries. |
| discover_skill | def | L1618-L1703 | Autonomous skill discovery and synthesis from external documentation. |

---

## 3. Router Dispatch Sequence Diagram

`mermaid
sequenceDiagram
    autonumber
    participant User as User / Cockpit
    participant Router as AgentRouter
    participant Gate as UnifiedPolicyGate
    participant Provider as BaseLLMProvider
    participant Sandbox as SandboxGuard
    participant Ledger as AuditLedger

    User->>Router: run_agent_loop(prompt, session_id)
    Router->>Router: _classify_intent(prompt)
    Router->>Provider: complete(messages, tools)
    Provider-->>Router: ToolCall(name, args)
    Router->>Router: validate_call(name, args)
    Router->>Gate: evaluate(role, tool, target_files)
    alt Requires Human Approval
        Router->>Router: _wait_for_approval(request_id)
        User->>Router: resolve_approval(request_id, APPROVED)
    end
    Router->>Sandbox: execute_safe(tool, args)
    Sandbox-->>Router: Execution Output
    Router->>Ledger: record_event(TOOL_EXECUTED, hash)
    Router->>Provider: complete(messages + tool_result)
    Provider-->>Router: Final Response Text
    Router-->>User: AgentTurnResponse
`

---

## 4. Operational Invariants & Anti-Corruption Guardrails
1. **Schema Strictness**: All tool arguments are strictly validated against spec/ schemas; undeclared parameters trigger immediate ToolValidationError.
2. **Approval Enforcement**: Mutating tools (bash, write_file, git_push) cannot execute if approval state is missing or denied.
3. **Sliding Memory Window**: Transcripts exceeding context token budget automatically trigger compaction via [[core-memory]] before provider invocation.

---

## 5. Verification & Test Evidence
- **Test Suites**:
  - [	est_router_validation.py](file:///d:/GitHub/LLM-Agent-System/agent_workspace/tests/test_router_validation.py)
  - [	est_router_conductor.py](file:///d:/GitHub/LLM-Agent-System/agent_workspace/tests/test_router_conductor.py)
  - [	est_route_swarm_direct.py](file:///d:/GitHub/LLM-Agent-System/agent_workspace/tests/test_route_swarm_direct.py)
- **Execution Receipt**: Bytecode validated via compileall exit code 0.

---

## 6. Topological Linkage
- **Upstream Layer**: [[L2-Protocol-and-Contract-Gateways]]
- **Control Plane**: [[10 7-Layer System Architecture & Control Plane Topology]]
- **Collaborating Modules**:
  - [[core-policy-gate]]
  - [[core-providers]]
  - [[core-sandbox]]
  - [[core-audit-ledger]]
