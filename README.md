# FindAi Studio LLM Agent System

[English](#english) | [繁體中文](#繁體中文)

---

## English

FindAi Studio LLM Agent System is the Python engine foundation for building file-aware, tool-using LLM agents. It keeps the core runtime small and explicit: Jinja2 prompt rendering, Pydantic tool reflection, session memory, RBAC-style allowed tool lists, async streaming, and self-correction around failed tool use.

This repository is also the engine side of the FindAi Studio topology integration. The engine core remains unchanged; topology data is emitted through external bridge material instead of being embedded into the closed-loop runtime.

### Architecture Principles

- **Engine core stays stable**: existing files in `agent_workspace/core/` and `agent_workspace/run.py` are not modified for visualization.
- **Bridge instead of intrusion**: topology serialization lives in `agent_workspace/topology_bridge.py`.
- **Topology is event data**: session starts, tool calls, handoffs, errors, and completion states become JSON events.
- **Viewer compatibility**: generated `workspace/topology_state.json` can be watched by the Tauri topology viewer.

### Key Features

- **Dual-track architecture**: separates persona/knowledge files in `knowledge_base/` from executable tools in `skills/`.
- **Pydantic tool reflection**: discovers Python functions that accept Pydantic models and exposes JSON schemas.
- **Jinja2 prompts**: renders `agent.jinja2` with session and knowledge context.
- **Session memory isolation**: stores conversation memory under `agent_workspace/memory/`.
- **Async streaming**: exposes incremental stream events for status, text chunks, tool calls, tool results, and errors.
- **Topology bridge**: writes a schema-versioned `topology_state.json` using atomic file replacement.

### Quick Start

Install dependencies:

```powershell
pip install -r requirements.txt
```

Set a Gemini API key before running the real engine:

```powershell
$env:GOOGLE_API_KEY="your-api-key-here"
```

Check the engine:

```powershell
python agent_workspace/run.py summary
```

Run a normal stream:

```powershell
python agent_workspace/run.py stream --msg "Calculate 123 * 456" --session stream-test
```

### Topology Bridge Usage

The bridge is intentionally external to the engine core.

Dry-run topology generation without calling the LLM:

```powershell
python agent_workspace/topology_stream.py stream --msg "test" --session verify-p1 --dry-run
```

Run the agent stream and emit topology events:

```powershell
python agent_workspace/topology_stream.py stream --msg "Calculate 123 * 456" --session stream-test
```

By default, the topology state is written to:

```text
workspace/topology_state.json
```

You can override the shared workspace directory:

```powershell
$env:AGENT_WORKSPACE_DIR="D:\GitHub\FindAi-Studio\workspace"
python agent_workspace/topology_stream.py stream --msg "test" --session verify-p1
```

Or provide a direct output path:

```powershell
python agent_workspace/topology_stream.py stream --msg "test" --session verify-p1 --output "D:\tmp\topology_state.json"
```

### Topology State Contract

`topology_state.json` uses schema version `1.0.0` and contains:

- `schema_version`
- `session_id`
- `started_at`
- `updated_at`
- `stats`
- `nodes`
- `edges`

Supported topology event values:

- `node_type`: `session_root`, `agent`, `handoff`, `tool_call`, `hitl_gate`, `error`
- `edge_type`: `handoff`, `tool`, `rbac`, `error`, `hitl`
- `status`: `pending`, `running`, `completed`, `error`, `awaiting_approval`

### Validation

Compile-check the new bridge files:

```powershell
python -m py_compile agent_workspace\topology_bridge.py agent_workspace\topology_stream.py
```

Verify JSON creation:

```powershell
python agent_workspace/topology_stream.py stream --msg "test" --session verify-p1 --dry-run
```

### AI Assistant Rules

If you are an AI assistant working in this repository:

- Do not modify the closed-loop engine core for visualization.
- Do not move UI logic into Python engine internals.
- Add bridge/adapters externally when new integration behavior is needed.
- Keep runtime JSON files out of version control.

---

## 繁體中文

FindAi Studio LLM Agent System 是用來建構具備檔案感知、工具呼叫能力的 Python LLM Agent 引擎地基。核心 runtime 保持小而清楚：Jinja2 提示詞渲染、Pydantic 工具反射、Session 記憶、類 RBAC 的工具允許清單、非同步串流，以及工具失敗後的自我修正。

本 repo 也是 FindAi Studio 拓撲整合中的引擎端。引擎核心不被視覺化需求改動；拓撲資料透過外部橋接層輸出，而不是塞進閉環 runtime 裡。

### 架構原則

- **引擎核心穩定不動**：不為了視覺化修改 `agent_workspace/core/` 或 `agent_workspace/run.py`。
- **用橋接取代入侵**：拓撲序列化集中在 `agent_workspace/topology_bridge.py`。
- **拓撲就是事件資料**：Session 啟動、工具呼叫、Handoff、錯誤、完成狀態都轉成 JSON 事件。
- **相容 Viewer**：產生的 `workspace/topology_state.json` 可被 Tauri topology viewer 監聽。

### 主要能力

- **雙軌架構**：`knowledge_base/` 放 persona/knowledge，`skills/` 放可執行工具。
- **Pydantic 工具反射**：自動發現接受 Pydantic model 的 Python 函式並輸出 JSON schema。
- **Jinja2 提示詞**：用 session 與 knowledge context 渲染 `agent.jinja2`。
- **Session 記憶隔離**：對話記憶存放於 `agent_workspace/memory/`。
- **非同步串流**：輸出 status、text chunk、tool call、tool result、error 等串流事件。
- **拓撲橋接層**：以原子寫檔方式產生具 schema version 的 `topology_state.json`。

### 快速開始

安裝依賴：

```powershell
pip install -r requirements.txt
```

執行真實引擎前，先設定 Gemini API key：

```powershell
$env:GOOGLE_API_KEY="your-api-key-here"
```

檢查引擎狀態：

```powershell
python agent_workspace/run.py summary
```

執行一般串流：

```powershell
python agent_workspace/run.py stream --msg "Calculate 123 * 456" --session stream-test
```

### 拓撲橋接層用法

橋接層刻意放在引擎核心之外。

不呼叫 LLM，只產生拓撲 JSON：

```powershell
python agent_workspace/topology_stream.py stream --msg "test" --session verify-p1 --dry-run
```

執行 Agent 串流並輸出拓撲事件：

```powershell
python agent_workspace/topology_stream.py stream --msg "Calculate 123 * 456" --session stream-test
```

預設輸出位置：

```text
workspace/topology_state.json
```

也可以指定共享 workspace：

```powershell
$env:AGENT_WORKSPACE_DIR="D:\GitHub\FindAi-Studio\workspace"
python agent_workspace/topology_stream.py stream --msg "test" --session verify-p1
```

或直接指定輸出檔：

```powershell
python agent_workspace/topology_stream.py stream --msg "test" --session verify-p1 --output "D:\tmp\topology_state.json"
```

### 拓撲狀態契約

`topology_state.json` 使用 schema version `1.0.0`，包含：

- `schema_version`
- `session_id`
- `started_at`
- `updated_at`
- `stats`
- `nodes`
- `edges`

支援的拓撲事件值：

- `node_type`：`session_root`、`agent`、`handoff`、`tool_call`、`hitl_gate`、`error`
- `edge_type`：`handoff`、`tool`、`rbac`、`error`、`hitl`
- `status`：`pending`、`running`、`completed`、`error`、`awaiting_approval`

### 驗證

檢查橋接檔案語法：

```powershell
python -m py_compile agent_workspace\topology_bridge.py agent_workspace\topology_stream.py
```

驗證 JSON 產生：

```powershell
python agent_workspace/topology_stream.py stream --msg "test" --session verify-p1 --dry-run
```

### AI Agent 工作規則

如果你是正在本 repo 工作的 AI Agent：

- 不要為了視覺化修改閉環引擎核心。
- 不要把 UI 邏輯塞進 Python 引擎內部。
- 需要整合行為時，從外部新增 bridge 或 adapter。
- runtime JSON 不進版本控制。
