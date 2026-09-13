---
tags:
  - architecture/leaf
  - runtime/workflow
  - dag/execution
  - layer/l3
type: module_leaf
layer: L3-Runtime-Execution-and-Swarm
module: agent_workspace.core.workflow_engine
file_path: agent_workspace/core/workflow_engine.py
sync_status: verified
---

# Module: WorkflowEngine (DAG Execution & Self-Healing Engine)

## 1. Three-Line Architectural Annotation
- **Responsibility**: Orchestrates asynchronous Directed Acyclic Graph (DAG) workflows with topological step dependency resolution, context variable hydration, and conditional branching.
- **Invariant**: Step execution must be strictly idempotent and atomic; failures trigger automatic self-healing reflection via _invoke_llm_healing before transitioning to terminal failure state.
- **Data Flow**: Consumes workflow JSON definitions conforming to spec/workflow.schema.json, hydrates parameters via _resolve_placeholder, persists state snapshots to disk, and emits telemetry events to [[core-ws-manager]].

---

## 2. Source Code & Symbol Mapping

**Source Location**: [workflow_engine.py](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/workflow_engine.py) (806 lines)

### Symbol Table

| Symbol | Kind | Line Range | Description |
| :--- | :--- | :--- | :--- |
| StepState | class | L31-L37 | Enumeration of step execution states (PENDING, RUNNING, COMPLETED, FAILED, SKIPPED, HEALING). |
| WorkflowRunState | class | L41-L49 | State container holding
un_id, workflow_id, status, step_outputs, context, and timestamps. |
| WorkflowEngine | class | L52-L806 | Core orchestrator managing workflow lifecycle, persistence, and execution. |
|
egister_callback | def | L58-L60 | Registers event listeners for workflow lifecycle hooks (on_step_start, on_step_complete, on_healing). |
| load_workflow | def | L97-L127 | Loads and validates workflow JSON definitions from config/workflows/. |
| _validate_step_graph | def | L130-L201 | Validates DAG integrity, detecting circular dependencies and dangling step transitions. |
| save_state | def | L203-L240 | Serializes WorkflowRunState to atomic JSON files under .agent/runs/. |
| load_state | def | L242-L284 | Hydrates workflow run state from disk for pause/resume and failover support. |
| _resolve_placeholder | def | L286-L318 | Hydrates ${steps.step_id.output.field} and ${inputs.field} context variables. |
| _invoke_llm_healing | def | L320-L394 | Autonomous reflection loop that submits step error traces to LLM providers to patch step parameters. |
| _execute_step_async | def | L396-L545 | Asynchronously dispatches a single step to tool sandboxes or agent crew roles. |
| execute | def | L547-L789 | Main execution loop driving topological step ordering and concurrency windows. |
| _get_next_step_id | def | L791-L806 | Evaluates branch conditions and yields next valid step identifier in DAG. |

---

## 3. Workflow Execution Lifecycle & Call Graph

`mermaid
sequenceDiagram
    autonumber
    participant Caller as Caller / Router
    participant Engine as WorkflowEngine
    participant Validator as _validate_step_graph
    participant StepExec as _execute_step_async
    participant Healer as _invoke_llm_healing
    participant Storage as Disk (.agent/runs/)

    Caller->>Engine: execute(workflow_id, inputs)
    Engine->>Validator: Validate step graph & dependencies
    Validator-->>Engine: DAG Validated (Topological Order)
    loop For Each Ready Step in DAG
        Engine->>StepExec: _execute_step_async(step, context)
        alt Step Succeeded
            StepExec-->>Engine: Output Data
            Engine->>Storage: save_state(RUNNING, step_outputs)
        else Step Failed & Retries Exceeded
            Engine->>Healer: _invoke_llm_healing(step, error_msg)
            alt Healing Succeeded
                Healer-->>Engine: Patched Step Parameters
                Engine->>StepExec: Retry with Patched Context
            else Healing Failed
                Engine->>Storage: save_state(FAILED)
                Engine-->>Caller: Raise WorkflowExecutionError
            end
        end
    end
    Engine->>Storage: save_state(COMPLETED)
    Engine-->>Caller: Final Run Output Context
`

---

## 4. Operational Invariants & Anti-Corruption Guardrails
1. **DAG Cycle Prevention**: Any cycle detected in _validate_step_graph immediately halts execution with a typed WorkflowValidationError before any step is invoked.
2. **Crash-Resilient State Persistence**: Every state transition is written atomically using temporary file renaming (.tmp -> .json) to prevent corrupted state files during ungraceful process terminations.
3. **Bounded Healing Budget**: Self-healing reflection via _invoke_llm_healing is capped at a maximum of 3 iterations per step to eliminate infinite remediation loops.

---

## 5. Verification & Test Evidence
- **Test Suites**:
  - [	est_workflow_engine.py](file:///d:/GitHub/LLM-Agent-System/agent_workspace/tests/test_workflow_engine.py)
  - [	est_workflow_lint.py](file:///d:/GitHub/LLM-Agent-System/agent_workspace/tests/test_workflow_lint.py)
- **Execution Receipt**: Bytecode validated via compileall exit code 0.

---

## 6. Topological Linkage
- **Upstream Layer**: [[L3-Runtime-Execution-and-Swarm]]
- **Control Plane**: [[10 7-Layer System Architecture & Control Plane Topology]]
- **Task DAG**: [[05 Task Status & Multi-Agent Execution DAG]]
- **Collaborating Modules**:
  - [[core-router]]
  - [[core-agent-crew]]
  - [[core-sandbox]]
  - [[core-audit-ledger]]
