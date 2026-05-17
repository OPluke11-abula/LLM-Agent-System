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
- Topology bridge foundation
- FastAPI adapter foundation

v2.0 priorities:

1. **FastAPI REST/SSE API layer**: completed as an external adapter.
2. **Multi-provider abstraction**: initial support completed for Google GenAI, OpenAI, Anthropic, and Ollama.
3. **PAP-compatible positioning**: completed at the workspace contract level through `.agent/agent.md`, entry documents, and per-tool skill contracts.
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
python -m py_compile agent_workspace\api.py agent_workspace\core\providers.py agent_workspace\topology_bridge.py agent_workspace\topology_stream.py
```

Smoke-check provider factory wiring:

```powershell
python -c "import sys; sys.path.insert(0, 'agent_workspace'); from core.providers import ProviderFactory; print(type(ProviderFactory.get_provider('openai')).__name__); print(type(ProviderFactory.get_provider('anthropic')).__name__); print(type(ProviderFactory.get_provider('ollama')).__name__)"
```

Smoke-check PAP manifest and skill contracts:

```powershell
python agent_workspace\pap_validate.py
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
- Topology bridge foundation
- FastAPI adapter foundation

v2.0 優先事項：

1. **FastAPI REST/SSE API 層**：已用外部 adapter 完成。
2. **Multi-Provider 抽象層**：已完成 Google GenAI、OpenAI、Anthropic、Ollama 初版支援。
3. **PAP-compatible 定位**：已在 workspace contract 層完成，包含 `.agent/agent.md`、entry documents、逐工具 skill contracts。
4. **持久化記憶**：保留 working memory，同時加入 Qdrant、Chroma 或 Weaviate 作為長期語意記憶。

v2.5 優先事項：

- OpenTelemetry tracing
- Prometheus metrics
- Structured JSON logging
- 對齊 PAP skills contract 的標準 Tool Manifest
- Supervisor-worker 多 Agent 協作

v3.0 優先事項：

- Golden test suites
- Hallucination 與任務完成率 benchmark
- Evaluation CI/CD
- No-code Agent Builder

### 驗證

編譯檢查 Python 檔案：

```powershell
python -m py_compile agent_workspace\api.py agent_workspace\core\providers.py agent_workspace\topology_bridge.py agent_workspace\topology_stream.py
```

Smoke-check Provider factory wiring：

```powershell
python -c "import sys; sys.path.insert(0, 'agent_workspace'); from core.providers import ProviderFactory; print(type(ProviderFactory.get_provider('openai')).__name__); print(type(ProviderFactory.get_provider('anthropic')).__name__); print(type(ProviderFactory.get_provider('ollama')).__name__)"
```

Smoke-check PAP manifest 與 skill contracts：

```powershell
python agent_workspace\pap_validate.py
```

驗證 topology JSON 建立：

```powershell
python agent_workspace/topology_stream.py stream --msg "test" --session verify-p1 --dry-run
```
