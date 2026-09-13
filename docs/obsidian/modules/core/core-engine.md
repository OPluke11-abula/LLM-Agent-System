---
tags:
  - architecture/leaf
  - runtime/engine
  - tool-dispatch
  - layer/l3
type: module_leaf
layer: L3-Runtime-Execution-and-Swarm
module: agent_workspace.core.engine
file_path: agent_workspace/core/engine.py
sync_status: verified
---

# Core Engine Leaf Note (`core-engine`)

> **File Path**: `agent_workspace/core/engine.py`
> **Layer**: [[L3-Runtime-Execution-and-Swarm]]
> **Assigned Role**: `DOMAIN_LOGIC_AGENT` (Luke) / `BACKEND_INFRA_AGENT` (Ethan)
> **Verification**: `python -m compileall agent_workspace/core/engine.py` (`PASS`)

---

## 1. 3-Line Code Annotation (English)
1. `AgentEngine` serves as the primary runtime owner orchestrating Jinja2 prompt rendering and reflected Pydantic tool execution.
2. Maintains strict separation of concern by delegating all HTTP gateway, Tauri IPC, and UI state synchronization to outer adapters.
3. Automatically triggers thread-level handoffs (`HandoffRequired`) whenever rolling session turn counts exceed configured thresholds.

---

## 2. Key Symbols & Exact Line Numbers

| Symbol Name | Symbol Type | Line Number Range | Architectural Responsibility |
|---|---|---|---|
| `HandoffRequired` | Class (`RuntimeError`) | Lines 49–60 | Signals context window saturation and requests cognitive relay handoff export |
| `AgentEngine` | Class | Lines 62–927 | Central dual-parser engine executing prompt rendering and tool dispatching |
| `AgentEngine.__init__` | Method | Lines 68–127 | Initializes Jinja2 environment, markdown skills discovery, and tool registry |
| `AgentEngine._discover_tools` | Method | Lines 140–210 | Dynamically reflects Python functions and Pydantic schemas under `skills/` |
| `AgentEngine.execute_tool` | Method | Lines 380–495 | Evaluates preconditions, runs precheck gates, and executes tool transactions |
| `AgentEngine.render_prompt` | Method | Lines 520–610 | Injects markdown knowledge contexts into Jinja2 templates |

---

## 3. Dependency & Call Graph

- **Upstream Callers**: `agent_workspace/core/router.py`, `agent_workspace/core/workflow_engine.py`, `agent_workspace/api.py`.
- **Downstream Callees**:
  - `agent_workspace/core/precheck.py` (`SkillsPrechecker`)
  - `agent_workspace/core/security.py` (`safe_workspace_path`, `validate_session_id`)
  - `agent_workspace/skills/` (Reflected tool modules)

---

## 4. Hard Invariants & Anti-Corruption Rules

- **Zero Swallowed Exceptions**: All tool execution failures must raise typed exceptions or return structured error models.
- **Path Sanitization**: Every file path passed to tool execution must be sanitized through `safe_workspace_path` to prevent path traversal.
