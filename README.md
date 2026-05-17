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
- **RBAC and semantic routing foundation**: allowed tools and intent routing are separated from tool execution.
- **Multi-provider LLM layer**: `google-genai`, `openai`, `anthropic`, and `ollama` share one provider contract.
- **PAP-compatible workspace contract**: `.agent/` declares LAS as a Portable-Agent-Protocol compatible reference application surface.
- **Persistent memory foundation**: session working memory can roll into a local long-term store with query support.
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

### PAP-Compatible Workspace

LAS now includes a `.agent/` protocol workspace:

- `.agent/agent.md`: executable PAP manifest for this repository.
- `.agent/skills.md`: runtime-facing skill registry.
- `.agent/prompts.md`: prompt contract for `agent_workspace/agent.jinja2`.
- `.agent/memory.md`: working-memory contract and long-term memory direction.
- `.agent/workflows.md`: CLI, FastAPI, and topology workflows.
- `.agent/skills/*.md`: per-tool contracts for reflected LAS skills.

This is a contract layer. It does not replace the LAS engine or move PAP logic
into `agent_workspace/core/`.

### Multi-Provider Configuration

LAS reads the active provider from `agent_workspace/config.yaml`:

```yaml
llm:
  provider: "google-genai"
  model: "gemini-2.5-flash"
  temperature: 0.0
  max_tokens: 4096
```

Supported providers:

| Provider | Example model | Required environment |
| --- | --- | --- |
| `google-genai` / `gemini` | `gemini-2.5-flash` | `GOOGLE_API_KEY` |
| `openai` | `gpt-4.1-mini` | `OPENAI_API_KEY` |
| `anthropic` | `claude-3-5-haiku-latest` | `ANTHROPIC_API_KEY` |
| `ollama` | `llama3.1` | Local Ollama server, no API key |

OpenAI-compatible custom endpoints can use `OPENAI_BASE_URL` or `llm.base_url`. Ollama can use `OLLAMA_BASE_URL` or `llm.base_url`.

PowerShell examples:

```powershell
$env:GOOGLE_API_KEY="your-google-key"
$env:OPENAI_API_KEY="your-openai-key"
$env:ANTHROPIC_API_KEY="your-anthropic-key"
$env:OLLAMA_BASE_URL="http://127.0.0.1:11434"
```

### Persistent Memory

LAS has two memory layers:

- **Working memory**: `agent_workspace/memory/<session_id>.json`, owned by `MemoryManager`.
- **Long-term memory**: pluggable `MemoryBackend` (default: `SQLiteBackend` → `agent_workspace/memory/long_term_memory.db`), owned by `LongTermMemoryStore`.

When the session window exceeds the working-memory retention limit, `AgentRouter`
calls the memory hook and persists a deterministic summary into the long-term
store. The backend is selected via `config.yaml` and can be swapped to Qdrant,
Chroma, or Weaviate by implementing the `MemoryBackend` interface.

Backend contract (`agent_workspace/memory_backends.py`):

| Method | Purpose |
| --- | --- |
| `write(session_id, key, value)` | Persist a record |
| `read(session_id, key)` | Retrieve a single record |
| `search(query, session_id, top_k)` | Full-text or semantic search |
| `all_records()` | List every stored record |

Configuration:

```yaml
memory:
  long_term_enabled: true
  backend: "sqlite"        # or "qdrant", "chroma", "weaviate" (future)
```

CLI inspection:

```powershell
python agent_workspace/long_term_memory.py list
python agent_workspace/long_term_memory.py query --q "customer preference"
```

### Observability

LAS includes a built-in observability module (`agent_workspace/observability.py`) with two capabilities:

**1. Structured JSON Logging**

All log output is emitted as single-line JSON objects with `timestamp`, `level`, `logger`, `message`, and caller-supplied `extra` fields (e.g. `session_id`, `tool_name`, `latency_ms`):

```json
{"timestamp": "2026-05-17T16:27:56Z", "level": "INFO", "logger": "core.router", "message": "Agent Loop started", "session_id": "user-456", "intent": "TASK"}
```

Controlled by `configure_logging(json_output=True)` at process startup. CLI (`run.py`) defaults to human-readable format; API (`api.py`) defaults to JSON.

**2. Prometheus Metrics**

| Metric | Type | Labels |
| --- | --- | --- |
| `las_request_total` | Counter | endpoint, session_id |
| `las_request_latency_seconds` | Histogram | endpoint |
| `las_request_errors_total` | Counter | endpoint, error_type |
| `las_tool_call_total` | Counter | tool_name, status |
| `las_tool_call_latency_seconds` | Histogram | tool_name |
| `las_llm_call_total` | Counter | provider, status |
| `las_llm_call_latency_seconds` | Histogram | provider |
| `las_active_sessions` | Gauge | — |

Exposed via `GET /v1/metrics` (Prometheus scrape target). `prometheus_client` is a soft dependency — if not installed, all metrics become harmless no-ops.

```powershell
pip install prometheus_client
curl http://localhost:8000/v1/metrics
```

**3. OpenTelemetry Distributed Tracing**

LAS provides zero-intrusion OpenTelemetry tracing. If `opentelemetry` packages are installed, all HTTP requests, agent loops, LLM calls, and tool executions are automatically traced and tied together in a single Trace ID hierarchy. Log outputs injected by the JSON Formatter will include `trace_id` and `span_id`.

```powershell
pip install opentelemetry-api opentelemetry-sdk opentelemetry-instrumentation-fastapi
```

### Multi-Agent Supervisor-Worker Orchestration (Swarm)

LAS supports advanced multi-agent workflows out-of-the-box via the **Supervisor-Worker delegation pattern**:

- **Worker Personas**: Define specialized worker agents in `agent_workspace/agents/` using `[agent_name].yaml` (for `allowed_tools`) and `[agent_name].jinja2` (for persona).
- **Delegation Tool**: Supervisors use the `delegate_task` tool to spawn a new asynchronous worker agent. 
- **Memory Isolation**: Each worker receives a sub-session ID (e.g. `user123:math_expert`) preventing memory pollution.
- **Trace Context Propagation**: Because of native OpenTelemetry support, sub-agent invocations show up beautifully nested under the Supervisor's trace tree.

### Tool Manifest (PAP Sync)

LAS dynamically loads tools from `agent_workspace/skills/` via Pydantic reflection. To maintain compatibility with the Portable Agent Protocol (PAP), you can automatically sync these runtime tools to static PAP skill contracts.

```powershell
# Generate a tool_manifest.json and sync .agent/skills/*.md
python agent_workspace/tool_manifest.py sync

# Validate that all runtime tools have matching PAP contracts
python agent_workspace/tool_manifest.py validate
```

The live PAP-aligned tool manifest is also exposed via the API:

```powershell
curl http://localhost:8000/v1/tools
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

The API adapter lives at `agent_workspace/api.py`. It uses the public `AgentEngine` and `AgentRouter` interfaces and checks the required environment variable for the configured provider.

Start the server:

```powershell
uvicorn agent_workspace.api:app --host 0.0.0.0 --port 8000
```

Endpoints:

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/v1/health` | Health check, active provider, and provider readiness |
| `POST` | `/v1/chat` | Synchronous single request / response chat |
| `POST` | `/v1/stream` | Server-Sent Events stream for incremental agent output |
| `POST` | `/v1/task` | Submit an asynchronous long-running task |
| `GET` | `/v1/session/{id}` | Read session memory and in-memory task status |
| `GET` | `/v1/memory` | List long-term memory records |
| `GET` | `/v1/memory/query` | Query long-term memory records |

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

The local `ai-agent-topology-viewer` material includes the first Phase 2 topology UI:

- `useTopology()` listens for `topology_updated`.
- `TopologyView` renders one or two sessions as React Flow DAGs.
- Custom nodes cover `session_root`, `agent` / `handoff`, `tool_call`, and `hitl_gate`.
- Custom edges cover `handoff`, `tool`, `rbac` / `hitl`, and `error`.
- The legacy task-flow screen remains as fallback when no topology state is loaded.

The viewer repository is local merge material. The backend repository remains the pushed source of truth.

### Roadmap

Current v1.x:

- CLI-first runtime
- Multi-provider provider contract
- PAP-compatible `.agent/` workspace
- Session memory
- Local long-term memory store
- Topology bridge foundation
- FastAPI adapter foundation

v2.0 priorities:

1. **FastAPI REST/SSE API layer**: completed as an external adapter.
2. **Multi-provider abstraction**: initial support completed for Google GenAI, OpenAI, Anthropic, and Ollama.
3. **PAP-compatible positioning**: completed at the workspace contract level through `.agent/agent.md`, entry documents, and per-tool skill contracts.
4. **Persistent memory**: pluggable `MemoryBackend` with `SQLiteBackend` (FTS5 search) as default; vector backends such as Qdrant, Chroma, or Weaviate can be added by implementing the same interface.
5. **Observability**: structured JSON logging and Prometheus metrics completed via `observability.py`; `GET /v1/metrics` endpoint live.
6. **Tool Manifest**: PAP-aligned skill contract auto-sync completed via `tool_manifest.py`; `GET /v1/tools` endpoint live.

v2.5 priorities:

- OpenTelemetry tracing (distributed trace context)
- Supervisor-worker multi-agent orchestration

v3.0 priorities:

- Golden test suites
- Hallucination and task-completion benchmarks
- Evaluation CI/CD
- No-code Agent Builder

### Validation

Compile-check Python files:

```powershell
python -m py_compile agent_workspace\api.py agent_workspace\core\providers.py agent_workspace\long_term_memory.py agent_workspace\observability.py agent_workspace\pap_validate.py agent_workspace\topology_bridge.py agent_workspace\topology_stream.py
```

Smoke-check provider factory wiring:

```powershell
python -c "import sys; sys.path.insert(0, 'agent_workspace'); from core.providers import ProviderFactory; print(type(ProviderFactory.get_provider('openai')).__name__); print(type(ProviderFactory.get_provider('anthropic')).__name__); print(type(ProviderFactory.get_provider('ollama')).__name__)"
```

Smoke-check PAP manifest and skill contracts:

```powershell
python agent_workspace\pap_validate.py
```

Smoke-check long-term memory (SQLiteBackend):

```powershell
python -c "import sys; sys.path.insert(0,'agent_workspace'); from long_term_memory import LongTermMemoryStore; s=LongTermMemoryStore('agent_workspace/memory'); rec=s.add_session_summary('smoke',[{'user':'remember blue widgets','assistant':'noted'}]); assert s.query('blue'); print('long-term memory ok')"
```

Verify topology JSON creation:

```powershell
python agent_workspace/topology_stream.py stream --msg "test" --session verify-p1 --dry-run
```

---

## 繁體中文

FindAi Studio LLM Agent System，簡稱 LAS，是為 FindAi Studio 打造的生產就緒型 LLM Agent 後端框架。核心目標是保持可閱讀、可維護、可由 AI 自動客製化，同時避免變成過度抽象的重型框架。

市場定位：

> 一個你真正能讀懂、真正能維護的 Agent 框架。不是魔法，是工程。

### 現有強項

- **雙軌架構**：`knowledge_base/` 存放 Persona 與領域知識；`skills/` 存放可執行工具。
- **Jinja2 動態提示詞注入**：Prompt 放在模板中，不寫死在程式碼裡。
- **Pydantic 工具自動反射**：新增工具不需要修改核心引擎。
- **閉環狀態機**：同一工具連續失敗會中止，避免無限 hallucination loop。
- **Session 記憶隔離**：每個 session 都有獨立記憶檔。
- **RBAC 與語意路由基礎**：工具權限、意圖判斷、工具執行彼此分離。
- **Multi-Provider LLM 層**：`google-genai`、`openai`、`anthropic`、`ollama` 共用同一個 Provider contract。
- **PAP-compatible workspace contract**：`.agent/` 已宣告 LAS 作為 Portable-Agent-Protocol compatible reference application surface。
- **持久化記憶基礎**：session working memory 可滾動寫入本機 long-term store，並支援查詢。
- **拓撲橋接層**：Runtime 事件可序列化到 `workspace/topology_state.json`，供視覺化 Viewer 使用。
- **FastAPI Adapter**：REST 與 SSE endpoint 已可對外暴露引擎能力，且不把 HTTP 邏輯寫入核心模組。

### 架構原則

- 引擎核心保持穩定。
- 整合行為透過 adapter 與 bridge layer 外掛。
- 不把 UI、HTTP、產品專屬邏輯放入閉環 runtime。
- Runtime JSON 是產生資料，不應提交到 Git。

### 安裝

```powershell
pip install -r requirements.txt
```

### PAP-Compatible Workspace

LAS 現在包含 `.agent/` protocol workspace：

- `.agent/agent.md`：本 repo 的 PAP manifest。
- `.agent/skills.md`：runtime-facing skill registry。
- `.agent/prompts.md`：對應 `agent_workspace/agent.jinja2` 的 prompt contract。
- `.agent/memory.md`：working memory contract 與長期記憶方向。
- `.agent/workflows.md`：CLI、FastAPI、topology workflows。
- `.agent/skills/*.md`：LAS 反射工具的逐工具 contract。

這是一層協定契約，不取代 LAS engine，也不把 PAP 邏輯搬進
`agent_workspace/core/`。

### Multi-Provider 設定

LAS 從 `agent_workspace/config.yaml` 讀取目前使用的 Provider：

```yaml
llm:
  provider: "google-genai"
  model: "gemini-2.5-flash"
  temperature: 0.0
  max_tokens: 4096
```

支援的 Provider：

| Provider | 範例模型 | 必要環境變數 |
| --- | --- | --- |
| `google-genai` / `gemini` | `gemini-2.5-flash` | `GOOGLE_API_KEY` |
| `openai` | `gpt-4.1-mini` | `OPENAI_API_KEY` |
| `anthropic` | `claude-3-5-haiku-latest` | `ANTHROPIC_API_KEY` |
| `ollama` | `llama3.1` | 本機 Ollama server，不需要 API key |

OpenAI-compatible 自訂 endpoint 可使用 `OPENAI_BASE_URL` 或 `llm.base_url`。Ollama 可使用 `OLLAMA_BASE_URL` 或 `llm.base_url`。

PowerShell 範例：

```powershell
$env:GOOGLE_API_KEY="your-google-key"
$env:OPENAI_API_KEY="your-openai-key"
$env:ANTHROPIC_API_KEY="your-anthropic-key"
$env:OLLAMA_BASE_URL="http://127.0.0.1:11434"
```

### 持久化記憶

LAS 有兩層記憶：

- **Working memory**：`agent_workspace/memory/<session_id>.json`，由 `MemoryManager` 管理。
- **Long-term memory**：可插拔 `MemoryBackend`（預設 `SQLiteBackend` → `agent_workspace/memory/long_term_memory.db`），由 `LongTermMemoryStore` 管理。

當 session window 超過 working-memory 保留上限時，`AgentRouter` 會呼叫 memory
hook，將 deterministic summary 寫入 long-term store。Backend 由 `config.yaml` 選擇，
未來可透過實作 `MemoryBackend` 介面無縫替換為 Qdrant、Chroma 或 Weaviate。

Backend contract (`agent_workspace/memory_backends.py`)：

| 方法 | 用途 |
| --- | --- |
| `write(session_id, key, value)` | 寫入記錄 |
| `read(session_id, key)` | 讀取單筆記錄 |
| `search(query, session_id, top_k)` | 全文或語意搜尋 |
| `all_records()` | 列出所有記錄 |

設定：

```yaml
memory:
  long_term_enabled: true
  backend: "sqlite"        # 或 "qdrant", "chroma", "weaviate"（未來）
```

CLI 檢視：

```powershell
python agent_workspace/long_term_memory.py list
python agent_workspace/long_term_memory.py query --q "customer preference"
```

### 可觀測性

LAS 內建可觀測性模組（`agent_workspace/observability.py`），提供兩項核心能力：

**1. 結構化 JSON Logging**

所有 log 輸出為單行 JSON 物件，包含 `timestamp`、`level`、`logger`、`message` 以及呼叫端傳入的 `extra` 欄位（如 `session_id`、`tool_name`、`latency_ms`）：

```json
{"timestamp": "2026-05-17T16:27:56Z", "level": "INFO", "logger": "core.router", "message": "Agent Loop started", "session_id": "user-456", "intent": "TASK"}
```

透過 `configure_logging(json_output=True)` 於啟動時控制。CLI（`run.py`）預設人類可讀格式；API（`api.py`）預設 JSON。

**2. Prometheus Metrics**

| 指標名稱 | 類型 | 標籤 |
| --- | --- | --- |
| `las_request_total` | Counter | endpoint, session_id |
| `las_request_latency_seconds` | Histogram | endpoint |
| `las_request_errors_total` | Counter | endpoint, error_type |
| `las_tool_call_total` | Counter | tool_name, status |
| `las_tool_call_latency_seconds` | Histogram | tool_name |
| `las_llm_call_total` | Counter | provider, status |
| `las_llm_call_latency_seconds` | Histogram | provider |
| `las_active_sessions` | Gauge | — |

透過 `GET /v1/metrics`（Prometheus scrape target）暴露。`prometheus_client` 為 soft dependency — 若未安裝，所有指標自動降級為無副作用的 No-op。

```powershell
pip install prometheus_client
curl http://localhost:8000/v1/metrics
```

**3. OpenTelemetry 分散式追蹤 (Tracing)**

LAS 提供零侵入的 OpenTelemetry 追蹤。只要安裝了相關套件，所有的 HTTP Request、Agent Loop、LLM 呼叫以及 Tool 執行都會自動記錄並整合在同一個 Trace ID 底下。透過 JSON Logging 輸出的日誌也會自動綁定 `trace_id` 和 `span_id`，完美支援企業級 ELK/Jaeger 除錯。

```powershell
pip install opentelemetry-api opentelemetry-sdk opentelemetry-instrumentation-fastapi
```

### 多 Agent 協作 (Supervisor-Worker Swarm)

LAS 原生支援多智能體協作架構，透過**主從委派模式 (Delegation Pattern)** 處理複雜任務：

- **子特工註冊表**：在 `agent_workspace/agents/` 定義專精特工。例如 `math_expert.yaml` (權限設定) 與 `math_expert.jinja2` (專屬人設)。
- **委派工具**：主 Agent (Supervisor) 可呼叫 `delegate_task` 工具，在背景啟動獨立的 Event Loop 與全新的 Worker 實例。
- **記憶隔離**：每一個 Worker 都有衍生的子 Session ID（例如 `user123:math_expert`），避免上下文污染。
- **追蹤連貫性**：得益於 OTel 整合，Worker 的行為軌跡會完美掛載於 Supervisor 的 Trace 樹狀結構之下。

### Tool Manifest (PAP Sync)

LAS 在 runtime 透過 Pydantic 動態反射載入 `agent_workspace/skills/` 內的工具。為了與 Portable Agent Protocol (PAP) 保持相容，我們提供了自動同步機制，將 runtime 工具轉為靜態的 PAP skill contracts。

```powershell
# 產生 tool_manifest.json 並同步更新 .agent/skills/*.md
python agent_workspace/tool_manifest.py sync

# 驗證所有 runtime 工具是否都有對應的 PAP contract
python agent_workspace/tool_manifest.py validate
```

即時的 PAP 工具清單也透過 API 暴露：

```powershell
curl http://localhost:8000/v1/tools
```

### CLI 使用

檢查引擎狀態：

```powershell
python agent_workspace/run.py summary
```

執行一般 stream：

```powershell
python agent_workspace/run.py stream --msg "Calculate 123 * 456" --session stream-test
```

### FastAPI 服務層

API adapter 位於 `agent_workspace/api.py`。它只透過公開的 `AgentEngine` 與 `AgentRouter` 介面呼叫引擎，並依照目前設定的 Provider 檢查必要環境變數。

啟動 server：

```powershell
uvicorn agent_workspace.api:app --host 0.0.0.0 --port 8000
```

Endpoints：

| Method | Path | 用途 |
| --- | --- | --- |
| `GET` | `/v1/health` | 健康檢查、目前 Provider、Provider readiness |
| `POST` | `/v1/chat` | 同步單次對話 |
| `POST` | `/v1/stream` | Server-Sent Events 串流輸出 |
| `POST` | `/v1/task` | 提交非同步長任務 |
| `GET` | `/v1/session/{id}` | 讀取 session memory 與記憶體中的 task 狀態 |
| `GET` | `/v1/memory` | 列出 long-term memory records |
| `GET` | `/v1/memory/query` | 查詢 long-term memory records |

同步範例：

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

拓撲橋接層刻意放在引擎核心外部。

不呼叫 LLM，只產生 dry-run topology JSON：

```powershell
python agent_workspace/topology_stream.py stream --msg "test" --session verify-p1 --dry-run
```

執行 Agent stream 並輸出拓撲事件：

```powershell
python agent_workspace/topology_stream.py stream --msg "Calculate 123 * 456" --session stream-test
```

預設輸出：

```text
workspace/topology_state.json
```

覆寫共享 workspace 目錄：

```powershell
$env:AGENT_WORKSPACE_DIR="D:\GitHub\FindAi-Studio\workspace"
python agent_workspace/topology_stream.py stream --msg "test" --session verify-p1
```

### Topology State Contract

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

在 Windows 上，Tauri file watcher 可能短暫持有 `topology_state.json`，導致 Python replace 檔案時遇到鎖定。`TopologyEmitter._atomic_write()` 會在 `PermissionError` 時重試最後的 `os.replace()`。

### 本機 Viewer 材料

本機 `ai-agent-topology-viewer` 材料已包含 Phase 2 第一版拓撲 UI：

- `useTopology()` 監聽 `topology_updated`。
- `TopologyView` 使用 React Flow DAG 呈現一個或兩個 session。
- 自訂節點涵蓋 `session_root`、`agent` / `handoff`、`tool_call`、`hitl_gate`。
- 自訂邊涵蓋 `handoff`、`tool`、`rbac` / `hitl`、`error`。
- 若尚未載入 topology state，保留舊 task-flow 畫面作為 fallback。

Viewer repo 只是本機合併材料；後端 repo 才是已 push 的 source of truth。

### 路線圖

目前 v1.x：

- CLI-first runtime
- Multi-provider provider contract
- PAP-compatible `.agent/` workspace
- Session memory
- Local long-term memory store
- Topology bridge foundation
- FastAPI adapter foundation

v2.0 優先事項：

1. **FastAPI REST/SSE API 層**：已用外部 adapter 完成。
2. **Multi-Provider 抽象層**：已完成 Google GenAI、OpenAI、Anthropic、Ollama 初版支援。
3. **PAP-compatible 定位**：已在 workspace contract 層完成，包含 `.agent/agent.md`、entry documents、逐工具 skill contracts。
4. **持久化記憶**：已完成可插拔 `MemoryBackend` 架構，預設使用 `SQLiteBackend`（FTS5 搜尋）；Qdrant、Chroma 或 Weaviate 等 vector backend 只需實作同一介面即可接入。
5. **可觀測性**：已完成結構化 JSON Logging 與 Prometheus Metrics（透過 `observability.py`）；`GET /v1/metrics` 端點已上線。
6. **Tool Manifest**：已完成 PAP skill contract 自動同步（透過 `tool_manifest.py`）；`GET /v1/tools` 端點已上線。

v2.5 優先事項：

- OpenTelemetry tracing（分散式追蹤上下文）
- Supervisor-worker 多 Agent 協作

v3.0 優先事項：

- Golden test suites
- Hallucination 與任務完成率 benchmark
- Evaluation CI/CD
- No-code Agent Builder

### 驗證

編譯檢查 Python 檔案：

```powershell
python -m py_compile agent_workspace\api.py agent_workspace\core\providers.py agent_workspace\long_term_memory.py agent_workspace\observability.py agent_workspace\pap_validate.py agent_workspace\topology_bridge.py agent_workspace\topology_stream.py
```

Smoke-check Provider factory wiring：

```powershell
python -c "import sys; sys.path.insert(0, 'agent_workspace'); from core.providers import ProviderFactory; print(type(ProviderFactory.get_provider('openai')).__name__); print(type(ProviderFactory.get_provider('anthropic')).__name__); print(type(ProviderFactory.get_provider('ollama')).__name__)"
```

Smoke-check PAP manifest 與 skill contracts：

```powershell
python agent_workspace\pap_validate.py
```

Smoke-check long-term memory（SQLiteBackend）：

```powershell
python -c "import sys; sys.path.insert(0,'agent_workspace'); from long_term_memory import LongTermMemoryStore; s=LongTermMemoryStore('agent_workspace/memory'); rec=s.add_session_summary('smoke',[{'user':'remember blue widgets','assistant':'noted'}]); assert s.query('blue'); print('long-term memory ok')"
```

驗證 topology JSON 建立：

```powershell
python agent_workspace/topology_stream.py stream --msg "test" --session verify-p1 --dry-run
```
