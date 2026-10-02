---
tags:
  - architecture/leaf
  - security/sandbox
  - isolation/filesystem
  - layer/l5
type: module_leaf
layer: L5-Security-Sandbox-and-Merkle
module: agent_workspace.core.sandbox
file_path: agent_workspace/core/sandbox.py
sync_status: verified
---

# Module: SandboxGuard (Filesystem Isolation & Rollback Sandbox)

## 1. Three-Line Architectural Annotation
- **Responsibility**: Provides safe execution boundaries for code evaluation, AST validation for synthesized skills, and atomic filesystem snapshot transactions with rollback capabilities.
- **Invariant**: File modifications within a transaction are fully reverted on exception; operations attempting path traversal outside the designated workspace root are aborted.
- **Data Flow**: Wraps tool executions initiated by [[core-router]], tracks mutated file paths, creates temporary shadow snapshots, and commits or rolls back changes.

---

## 2. Source Code & Symbol Mapping

**Source Location**: [sandbox.py](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/sandbox.py) (422 lines)

### Symbol Table

| Symbol | Kind | Line Range | Description |
| :--- | :--- | :--- | :--- |
| FileSnapshotTransaction | class | L44-L148 | Context manager creating snapshot backups of targeted files before mutation. |
| __enter__ | def | L50-L76 | Backs up original file contents into shadow directory. |
|
ollback | def | L78-L134 | Restores mutated files from shadow backup upon tool failure or exception. |
| cleanup | def | L136-L142 | Removes temporary shadow snapshots on successful transaction completion. |
| make_safe_open | def | L151-L181 | Factory function returning a restricted open() callable enforcing path jail. |
|
alidate_generated_skill | def | L183-L225 | Uses Python AST parser to reject malicious imports (subprocess, os.system, eval, socket calls). |
|
alidate_skill_name | def | L227-L230 | Enforces alphanumeric naming conventions on dynamic skills. |
| SandboxGuard | class | L232-L422 | Security controller managing isolated tool execution and environment quotas. |
| execute_safe | def | L251-L422 | Dispatches tools inside transaction wrapper with resource monitoring and timeouts. |

---

## 3. Transaction Rollback Lifecycle

`mermaid
sequenceDiagram
    autonumber
    participant Router as AgentRouter
    participant Guard as SandboxGuard
    participant Tx as FileSnapshotTransaction
    participant FS as Local Filesystem

    Router->>Guard: execute_safe(tool, args)
    Guard->>Tx: __enter__()
    Tx->>FS: Snapshot target files to .sandbox/
    Guard->>Guard: Execute tool logic
    alt Execution Successful
        Guard->>Tx: cleanup()
        Tx->>FS: Purge snapshot cache
        Guard-->>Router: Success Result
    else Tool Fails or Error Raised
        Guard->>Tx: rollback()
        Tx->>FS: Restore original files from .sandbox/
        Guard-->>Router: Raise ToolExecutionError (FS Clean)
    end
`

---

## 4. Operational Invariants & Anti-Corruption Guardrails
1. **Path Traversal Jail**: Paths containing .. or resolving outside workspace_path raise SecurityViolationError.
2. **AST Static Whitelist**: Generated code containing __import__, eval, or untrusted system calls is blocked before execution.
3. **Atomic Rollback Guarantee**: If writing a file fails midway, the original file is guaranteed to be restored to its exact previous byte state.

---

## 5. Verification & Test Evidence
- **Test Suites**:
  - [	est_sandbox.py](file:///d:/GitHub/LLM-Agent-System/agent_workspace/tests/test_sandbox.py)
  - [	est_sandbox_defense.py](file:///d:/GitHub/LLM-Agent-System/agent_workspace/tests/test_sandbox_defense.py)
- **Execution Receipt**: Bytecode validated via compileall exit code 0.

---

## 6. Topological Linkage
- **Upstream Layer**: [[L5-Security-Sandbox-and-Merkle]]
- **Control Plane**: [[10 7-Layer System Architecture & Control Plane Topology]]
- **Collaborating Modules**:
  - [[core-router]]
  - [[core-policy-gate]]
  - [[core-audit-ledger]]
