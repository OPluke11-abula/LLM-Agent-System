# FindAi Studio LLM Agent System

[English](#english) | [繁體中文](#繁體中文)

---

## English

FindAi Studio LLM Agent System, or LAS, is a production-ready backend framework for building file-aware, tool-using LLM agents. Its core goal is to stay readable, maintainable, and customizable by AI without becoming a heavy abstraction framework.

Market message:

> An agent framework you can actually read and maintain. Not magic, engineering.

### Current Strengths

- **Dual-track architecture**: `knowledge_base/` holds persona and domain knowledge; `skills/` holds executable tools.
- **Jinja2 prompt injection**: prompts live in templates instead of being hard-coded.
- **Pydantic tool reflection**: tools can be added without changing core engine code.
- **Closed-loop state machine**: repeated tool failures are stopped instead of looping forever.
- **Session memory isolation**: each session has its own memory file.
- **RBAC and semantic routing foundation**: allowed tools and intent routing are already separated from tool execution.
- **Topology bridge**: runtime events can be serialized to `workspace/topology_state.json` for a visual topology viewer.
- **FastAPI adapter**: REST and SSE endpoints expose the engine without moving HTTP logic into core modules.

### Architecture Principles

- Keep the engine core stable.
- Add integration behavior through adapters and bridge layers.
- Do not place UI, HTTP, or product-specific logic inside the closed-loop runtime.
- Runtime JSON files are generated data and should not be committed.

### Install

```powershell
pip install -r requirements.txt
```

Set a Gemini API key before calling the default provider:

```powershell
$env:GOOGLE_API_KEY="your-api-key-here"
```

### CLI Usage

Check engine status:

```powershell
python agent_workspace/run.py summary
```

Run a normal stream:

```powershell
python agent_workspace/run.py stream --msg "Calculate 123 * 456" --session stream-test
```

### FastAPI Service Layer

The API adapter lives at `agent_workspace/api.py`. It uses the public `AgentEngine` and `AgentRouter` interfaces.

Start the server:

```powershell
uvicorn agent_workspace.api:app --host 0.0.0.0 --port 8000
```

Endpoints:

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/v1/health` | Health check for local dev, load balancers, and future K8s probes |
| `POST` | `/v1/chat` | Synchronous single request / response chat |
| `POST` | `/v1/stream` | Server-Sent Events stream for incremental agent output |
| `POST` | `/v1/task` | Submit an asynchronous long-running task |
| `GET` | `/v1/session/{id}` | Read session memory and in-memory task status |

Synchronous example:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/v1/chat `
  -ContentType "application/json" `
  -Body '{"msg":"Hello","session":"demo"}'
```

SSE example:

```powershell
curl.exe -N `
  -H "Content-Type: application/json" `
  -d "{\"msg\":\"Hello\",\"session\":\"demo\"}" `
  http://127.0.0.1:8000/v1/stream
```

### Topology Bridge

The topology bridge is intentionally external to the engine core.

Dry-run topology generation without calling the LLM:

```powershell
python agent_workspace/topology_stream.py stream --msg "test" --session verify-p1 --dry-run
```

Run the agent stream and emit topology events:

```powershell
python agent_workspace/topology_stream.py stream --msg "Calculate 123 * 456" --session stream-test
```

Default output:

```text
workspace/topology_state.json
```

Override the shared workspace directory:

```powershell
$env:AGENT_WORKSPACE_DIR="D:\GitHub\FindAi-Studio\workspace"
python agent_workspace/topology_stream.py stream --msg "test" --session verify-p1
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

Supported values:

- `node_type`: `session_root`, `agent`, `handoff`, `tool_call`, `hitl_gate`, `error`
- `edge_type`: `handoff`, `tool`, `rbac`, `error`, `hitl`
- `status`: `pending`, `running`, `completed`, `error`, `awaiting_approval`

On Windows, a Tauri file watcher can briefly hold `topology_state.json` while Python replaces it. `TopologyEmitter._atomic_write()` retries the final `os.replace()` on `PermissionError`.

### Local Viewer Material

The local `ai-agent-topology-viewer` material now includes the first Phase 2 topology UI:

- `useTopology()` listens for `topology_updated`.
- `TopologyView` renders one or two sessions as React Flow DAGs.
- Custom nodes cover `session_root`, `agent` / `handoff`, `tool_call`, and `hitl_gate`.
- Custom edges cover `handoff`, `tool`, `rbac` / `hitl`, and `error`.
- The legacy task-flow screen remains as fallback when no topology state is loaded.

### Roadmap

Current v1.x:

- CLI-only
- Single default provider
- Session memory
- Limited observability

v2.0 priorities:

1. **FastAPI REST/SSE API layer**: completed as an external adapter.
2. **Multi-provider abstraction**: add OpenAI, Anthropic, and Ollama providers behind the existing provider interface.
3. **PAP-compatible positioning**: LAS is intended to serve as the Portable-Agent-Protocol reference application. Memory and tool contracts should align with PAP as both projects version forward.
4. **Persistent memory**: keep working memory while adding long-term semantic memory through Qdrant, Chroma, or Weaviate.

v2.5 priorities:

- OpenTelemetry tracing
- Prometheus metrics
- Structured JSON logging
- Standard Tool Manifest aligned with PAP skills contracts
- Supervisor-worker multi-agent orchestration

v3.0 priorities:

- Golden test suites
- Hallucination and task-completion benchmarks
- Evaluation CI/CD
- No-code Agent Builder

### Validation

Compile-check Python files:

```powershell
python -m py_compile agent_workspace\api.py agent_workspace\topology_bridge.py agent_workspace\topology_stream.py
```

Verify topology JSON creation:

```powershell
python agent_workspace/topology_stream.py stream --msg "test" --session verify-p1 --dry-run
```

---

## 繁體中文

FindAi Studio LLM Agent System，簡稱 LAS，是為可讀、可維護、可由 AI 客製化而設計的生產就緒型 LLM Agent 後端框架。它避免過度抽象，目標是讓工程師能清楚理解每一層在做什麼。

市場訊息：

> 一個你真正能讀懂、真正能維護的 Agent 框架。不是魔法，是工程。

### 現有強項

- **雙軌架構**：`knowledge_base/` 放 persona 與領域知識，`skills/` 放可執行工具。
- **Jinja2 提示詞注入**：prompt 放在模板，不硬寫在程式碼中。
- **Pydantic 工具反射**：新增工具不需要修改核心引擎。
- **閉環狀態機**：連續工具失敗會中斷，避免無限 hallucination loop。
- **Session 記憶隔離**：每個 session 有自己的記憶檔。
- **RBAC 與語意路由雛形**：工具權限與意圖判斷已和工具執行分離。
- **拓撲橋接層**：執行事件可序列化成 `workspace/topology_state.json`，供視覺化 Viewer 使用。
- **FastAPI adapter**：用 REST 與 SSE 對外暴露引擎，不把 HTTP 邏輯塞進核心模組。

### 架構原則

- 引擎核心保持穩定。
- 整合行為透過 adapter 與 bridge layer 新增。
- UI、HTTP、產品特定邏輯不進閉環 runtime。
- runtime JSON 是生成資料，不進版控。

### 安裝

```powershell
pip install -r requirements.txt
```

呼叫預設 provider 前，先設定 Gemini API key：

```powershell
$env:GOOGLE_API_KEY="your-api-key-here"
```

### CLI 用法

檢查引擎狀態：

```powershell
python agent_workspace/run.py summary
```

執行一般串流：

```powershell
python agent_workspace/run.py stream --msg "Calculate 123 * 456" --session stream-test
```

### FastAPI 服務層

API adapter 位於 `agent_workspace/api.py`，透過公開的 `AgentEngine` 與 `AgentRouter` 介面呼叫引擎。

啟動 server：

```powershell
uvicorn agent_workspace.api:app --host 0.0.0.0 --port 8000
```

端點：

| 方法 | 路徑 | 用途 |
| --- | --- | --- |
| `GET` | `/v1/health` | 健康檢查，供本機開發、load balancer、未來 K8s probe 使用 |
| `POST` | `/v1/chat` | 同步單次對話 |
| `POST` | `/v1/stream` | Server-Sent Events 串流輸出 |
| `POST` | `/v1/task` | 提交非同步長任務 |
| `GET` | `/v1/session/{id}` | 查詢 session 記憶與目前 process 內的 task 狀態 |

同步呼叫範例：

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/v1/chat `
  -ContentType "application/json" `
  -Body '{"msg":"Hello","session":"demo"}'
```

SSE 範例：

```powershell
curl.exe -N `
  -H "Content-Type: application/json" `
  -d "{\"msg\":\"Hello\",\"session\":\"demo\"}" `
  http://127.0.0.1:8000/v1/stream
```

### 拓撲橋接層

拓撲橋接層刻意放在引擎核心之外。

不呼叫 LLM，只產生 topology JSON：

```powershell
python agent_workspace/topology_stream.py stream --msg "test" --session verify-p1 --dry-run
```

執行 Agent 串流並輸出拓撲事件：

```powershell
python agent_workspace/topology_stream.py stream --msg "Calculate 123 * 456" --session stream-test
```

預設輸出：

```text
workspace/topology_state.json
```

指定共享 workspace：

```powershell
$env:AGENT_WORKSPACE_DIR="D:\GitHub\FindAi-Studio\workspace"
python agent_workspace/topology_stream.py stream --msg "test" --session verify-p1
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

支援值：

- `node_type`：`session_root`、`agent`、`handoff`、`tool_call`、`hitl_gate`、`error`
- `edge_type`：`handoff`、`tool`、`rbac`、`error`、`hitl`
- `status`：`pending`、`running`、`completed`、`error`、`awaiting_approval`

在 Windows 上，Tauri watcher 可能會在 Python 替換 `topology_state.json` 時短暫持有檔案。`TopologyEmitter._atomic_write()` 會在 `PermissionError` 時重試最後的 `os.replace()`。

### 本機 Viewer 材料

本機 `ai-agent-topology-viewer` 已有第一版 Phase 2 拓撲 UI：

- `useTopology()` 監聽 `topology_updated`。
- `TopologyView` 可用 React Flow DAG 顯示一個或兩個 session。
- 自訂節點涵蓋 `session_root`、`agent` / `handoff`、`tool_call`、`hitl_gate`。
- 自訂邊涵蓋 `handoff`、`tool`、`rbac` / `hitl`、`error`。
- 沒有 topology state 時，保留舊 task-flow 畫面作為 fallback。

### 路線圖

目前 v1.x：

- CLI-only
- 單一預設 provider
- Session memory
- 可觀測性不足

v2.0 優先事項：

1. **FastAPI REST/SSE API 層**：已完成外部 adapter。
2. **Multi-Provider 抽象**：在現有 provider interface 後方加入 OpenAI、Anthropic、Ollama。
3. **PAP-compatible 定位**：LAS 目標是 Portable-Agent-Protocol 的 reference application。記憶與工具 contract 需要隨 PAP 版本持續對齊。
4. **持久化記憶**：保留 working memory，同時用 Qdrant、Chroma 或 Weaviate 增加長期語意記憶。

v2.5 優先事項：

- OpenTelemetry tracing
- Prometheus metrics
- Structured JSON logging
- 與 PAP skills contract 對齊的標準 Tool Manifest
- Supervisor-worker 多 Agent 協作

v3.0 優先事項：

- Golden test suites
- Hallucination 與任務完成率 benchmark
- Evaluation CI/CD
- No-code Agent Builder

### 驗證

檢查 Python 檔案：

```powershell
python -m py_compile agent_workspace\api.py agent_workspace\topology_bridge.py agent_workspace\topology_stream.py
```

驗證 topology JSON：

```powershell
python agent_workspace/topology_stream.py stream --msg "test" --session verify-p1 --dry-run
```
