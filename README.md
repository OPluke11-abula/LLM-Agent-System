# FindAi Studio — LLM Agent System (LAS)

[English](#english) | [繁體中文](#繁體中文)

---

## English

> **The First AI-Maintainable Agent Framework**
> Stop fighting rigid framework abstractions. FindAi Studio uses a Contract-First design (`.agent/` PAP + `INSTRUCTIONS_FOR_AI.md`) that lets cutting-edge LLMs safely understand, refactor, and extend your Agent workflows autonomously. It's not just an AI Agent — it's an AI that builds your AI.
>
> Natively supports Claude 3.5 Sonnet and GPT-4o with zero vendor lock-in.

LAS is a readable, maintainable, observable, and portable local Agent Runtime
with a visual control-plane direction. It is not another generic LLM framework.
Its product value is the combination of:

- **Topological Workspace** — a structured-log, node-based visual workspace that turns complex AI agent sessions into an infinite canvas of interconnected task blocks
- **Contract-First AI Handoff** — PAP-compatible `.agent/` workspace contracts that let both humans and AI safely inspect, verify, and extend the codebase
- **Multi-Provider LLM Abstraction** — native support for Gemini, Claude 3.5 Sonnet, GPT-4o, and Ollama with zero vendor lock-in
- **FastAPI REST / SSE / WebSocket** — production-ready API layer with synchronous, streaming, and real-time bidirectional communication
- **Pluggable Memory Backends** — SQLite (default) and Redis for enterprise-scale persistent long-term memory
- **Local Viewer** — React + React Flow topology visualisation with live status animations

### Three-Minute Start

```powershell
git clone <repo-url>
cd LLM-Agent-System
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
.\scripts\verify.cmd -SkipViewer
```

Optional full bootstrap, including dependency install:

```powershell
.\scripts\bootstrap_verify.cmd
```

Provider SDKs are optional. Install them only when you need hosted backends:

```powershell
pip install -r requirements-providers.txt
```

Use standard Windows CPython for dependency installation. MSYS/MinGW Python may
try to compile native wheels locally and fail on packages such as
`pydantic-core`.

### Start the API Server

```powershell
uvicorn agent_workspace.api:app --host 0.0.0.0 --port 8000
curl http://127.0.0.1:8000/v1/health
```

### Start the Viewer

```powershell
cd viewer
npm install
npm run dev
```

### Architecture

```
LLM-Agent-System/
├── .agent/                          # PAP workspace contract (AI handoff surface)
│   ├── agent.md                     # Agent persona & capabilities
│   └── skills/                      # Skill contracts (one .md per tool)
├── agent_workspace/
│   ├── core/
│   │   ├── engine.py                # AgentEngine — closed-loop runtime
│   │   ├── router.py                # AgentRouter — streaming orchestration
│   │   └── providers.py             # Multi-LLM provider abstraction
│   ├── skills/                      # Python tool implementations
│   ├── memory/                      # Generated session & memory data
│   ├── api.py                       # FastAPI adapter (REST / SSE / WebSocket)
│   ├── memory_backends.py           # MemoryBackend (SQLite, Redis)
│   ├── topology_bridge.py           # Topology state serialisation
│   ├── topology_stream.py           # Stream wrapper emitting topology events
│   ├── observability.py             # Prometheus metrics & OpenTelemetry tracing
│   ├── tool_manifest.py             # Runtime-tool ↔ PAP-contract sync
│   ├── pap_validate.py              # Zero-dependency .agent/ contract validator
│   └── config.yaml                  # Active LLM provider configuration
├── viewer/                          # React + React Flow topology viewer (Vite + Tauri)
│   └── src/
│       ├── components/TopologyView.tsx  # Infinite canvas topology view
│       ├── utils/topologyUtils.ts       # Dagre layout & node mapping
│       └── types.ts                     # Shared TypeScript type definitions
├── scripts/                         # Bootstrap and verification commands
└── workspace/                       # Generated topology state output
```

#### Design Principles

- Keep `agent_workspace/core/` focused on runtime behaviour only.
- Add HTTP, topology, viewer, and protocol concerns through adapters and bridge layers.
- Treat `.agent/`, PAP sync, and tool contracts as the AI handoff surface.
- Treat runtime JSON, memory DBs, caches, and topology state as generated data — never commit them.
- Prefer reliable delegation contracts over unbounded swarm behaviour.

### Provider Configuration

LAS reads the active provider from `agent_workspace/config.yaml`:

```yaml
llm:
  provider: "google-genai"
  model: "gemini-2.5-flash"
  temperature: 0.0
  max_tokens: 4096
```

| Provider | Example model | Required environment |
| --- | --- | --- |
| `google-genai` / `gemini` | `gemini-2.5-flash` | `GOOGLE_API_KEY` |
| `openai` | `gpt-4o` | `OPENAI_API_KEY` |
| `anthropic` | `claude-3-5-sonnet-latest` | `ANTHROPIC_API_KEY` |
| `ollama` | `llama3.1` | local Ollama server |

### Memory Backend Configuration

By default LAS uses SQLite. To switch to Redis, set the `MEMORY_BACKEND` and `REDIS_URL` environment variables:

```powershell
$env:MEMORY_BACKEND = "redis"
$env:REDIS_URL = "redis://localhost:6379"
```

### API Surface

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/v1/health` | Health, provider, readiness |
| `GET` | `/v1/tools` | Live PAP-aligned tool manifest |
| `POST` | `/v1/chat` | Synchronous agent request |
| `POST` | `/v1/stream` | SSE stream with tool events |
| `WS` | `/v1/stream_ws` | WebSocket bidirectional streaming |
| `WS` | `/v1/stream` | WebSocket multi-turn streaming |
| `POST` | `/v1/task` | Async task submission |
| `GET` | `/v1/session/{id}` | Session memory and task state |
| `GET` | `/v1/memory` | Long-term memory records |
| `GET` | `/v1/memory/query` | Long-term memory search |
| `GET` | `/v1/metrics` | Prometheus metrics |
| `GET/PUT` | `/v1/config` | Local LLM configuration |

### Topological Workspace

The topology bridge converts each agent session into a structured JSON state file (`topology_state.json`) that serves as the **single source of truth** for the visual workspace.

Each **node** represents a task with:
- `title` — human-readable task name
- `status` — state machine (`todo` → `in_process` → `review` → `done` / `error`)
- `assigned_agent` — which agent owns this task
- `description` — task context
- `result_summary` — compressed outcome (populated on completion)

Each **edge** defines task dependencies with typed connections (`handoff`, `tool`, `rbac`, `error`, `hitl`).

Dry-run topology generation (no LLM required):

```powershell
python agent_workspace/topology_stream.py stream --msg "test" --session verify-p1 --dry-run
```

### Contract Pipeline

```powershell
python agent_workspace\pap_validate.py
python agent_workspace\tool_manifest.py sync
python agent_workspace\tool_manifest.py validate
```

`pap_validate.py` is dependency-free and checks the `.agent/` workspace
contract. `tool_manifest.py` reflects live runtime tools and verifies that each
tool has a matching PAP skill contract.

### Product Roadmap

| Phase | Status | Scope |
| --- | --- | --- |
| P0 | ✅ Done | UTF-8 docs, bootstrap/verify, generated-data governance |
| P1 | ✅ Done | FastAPI WebSocket streaming, native multi-provider (Claude / GPT-4o), Redis memory backend |
| P2 | ✅ Done | Governed memory (episodic, semantic, retention, delete, citation), Topological Workspace schema & viewer |
| P3 | 🔲 Next | Delegation hardening: cancellation, traceability, replay, audit, tool limits, cost measurement |
| P4 | 🔲 Planned | Package LAS as local-first, auditable, AI-maintainable, protocol-compatible runtime infrastructure |

---

## 繁體中文

> **首個讓 AI 幫你客製化 AI 的框架 (The First AI-Maintainable Agent Framework)**
> 透過 Contract-First 設計 (`.agent/` + `INSTRUCTIONS_FOR_AI.md`)，強大的模型能自主擴充並維護你的工作流，而不會破壞核心架構。原生無縫支援 Claude 3.5 Sonnet 與 GPT-4o。

LAS 的定位是「可讀、可維護、可觀測、可移植的本地 Agent Runtime + 視覺控制台」。
它不是又一個聊天 agent 或一般 LLM framework，而是人和 AI 都能安全接手維護的
Agent Runtime 標準樣板。

核心功能：

- **拓撲式工作區 (Topological Workspace)** — 用結構化日誌將 AI agent session 轉化為視覺化無限畫布，每個方塊代表一個任務節點
- **Contract-First AI 交接** — PAP 相容的 `.agent/` 合約讓人類與 AI 都能安全地檢視、驗證、擴充程式碼
- **多模型 LLM 抽象層** — 原生支援 Gemini、Claude 3.5 Sonnet、GPT-4o、Ollama，零供應商鎖定
- **FastAPI REST / SSE / WebSocket** — 生產級 API 層，支援同步、串流、即時雙向通訊
- **可插拔記憶體後端** — SQLite (預設) 與 Redis 企業級持久化長期記憶
- **本地 Viewer** — React + React Flow 拓撲視覺化，具備即時狀態動畫

### 三分鐘啟動

```powershell
git clone <repo-url>
cd LLM-Agent-System
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
.\scripts\verify.cmd -SkipViewer
```

完整 bootstrap：

```powershell
.\scripts\bootstrap_verify.cmd
```

Provider SDK 可選安裝：

```powershell
pip install -r requirements-providers.txt
```

安裝 dependencies 時建議使用標準 Windows CPython。MSYS/MinGW Python 可能會改成
本機編譯 native wheels，導致 `pydantic-core` 這類套件安裝失敗。

### 啟動 API 伺服器

```powershell
uvicorn agent_workspace.api:app --host 0.0.0.0 --port 8000
curl http://127.0.0.1:8000/v1/health
```

### 啟動 Viewer

```powershell
cd viewer
npm install
npm run dev
```

### 產品核心

LAS 的護城河不是「又一個聊天 agent」，而是 Contract-First Runtime：

- `.agent/` 是 AI 接手 repo 的協作合約
- `tool_manifest.py` 把 runtime tool 反射成 PAP contract
- `pap_validate.py` 是零依賴 workspace contract gate
- `topology_bridge.py` 把 runtime session 轉成拓撲式結構化日誌 (JSON)
- `memory_backends.py` 支援 SQLite 與 Redis，是 memory governance 的基礎
- delegation 應先做可靠、可追蹤、可審計，而不是追求 swarm 噱頭

### 拓撲式工作區

每個任務方塊具備：
- **標題 (title)** — 人類可讀的任務名稱
- **狀態機 (status)** — `todo` → `in_process` → `review` → `done` / `error`
- **負責 Agent (assigned_agent)** — 執行該任務的 agent
- **執行摘要 (result_summary)** — 任務完成後自動濃縮的結果

每條連線 (edge) 定義任務相依性，支援型別：`handoff`、`tool`、`rbac`、`error`、`hitl`。

### 驗證命令

```powershell
.\scripts\verify.cmd -SkipViewer
python agent_workspace\pap_validate.py
python agent_workspace\tool_manifest.py validate
python agent_workspace\topology_stream.py stream --msg "test" --session verify-p1 --dry-run
```

### 開發原則

- 不把 UI、HTTP、topology 或 PAP 邏輯塞進 `agent_workspace/core/`
- 新能力優先放在 adapter、bridge、contract pipeline
- runtime JSON、memory DB、cache、topology state 都是 generated data，不應提交
- README、PAP 文件、log、Python 註解必須維持乾淨 UTF-8
- 每次新增 tool，都要同步 `.agent/skills/*.md` 並跑 contract validation

### 優先級

| 階段 | 狀態 | 範圍 |
| --- | --- | --- |
| P0 | ✅ 完成 | 亂碼修復、bootstrap/verify、generated data 治理 |
| P1 | ✅ 完成 | FastAPI WebSocket 串流、多模型原生支援 (Claude / GPT-4o)、Redis 記憶體後端 |
| P2 | ✅ 完成 | 可治理記憶體 (Governed Memory)、拓撲式工作區 Schema 與 Viewer |
| P3 | 🔲 下一步 | delegation 完整化：取消、追蹤、重放、審計、工具限額、成本度量 |
| P4 | 🔲 規劃中 | 商業包裝：local-first、auditable、AI-maintainable、protocol-compatible |
