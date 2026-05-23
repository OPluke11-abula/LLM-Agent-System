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
- **Markdown SkillLoader** — seamlessly auto-discovers and bridges `anthropics/skills` format (`SKILL.md`) into Pydantic-executable tools
- **Zero-Build Viewer** — extremely lightweight DAG topology viewer (`workspace/viewer.html`) without any build-step overhead
- **Structured Log Memory** — intelligent auto-compression of completed task logs to maintain optimal context window utilization
- **Multi-Provider LLM Abstraction** — native support for Gemini, Claude 3.5 Sonnet, GPT-4o, and Ollama with zero vendor lock-in
- **Pluggable Memory Backends** — SQLite (default) and Redis for enterprise-scale persistent long-term memory

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

**Option A (Zero-Build Lightweight Viewer):**
```powershell
python -m http.server 8000
# Open http://localhost:8000/workspace/viewer.html
```

**Option B (Full React Tauri App):**
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
├── spec/                            # PAP Specification JSON Schemas (formal contracts)
│   ├── agent-schema.json            # Schema for agent metadata
│   ├── skill-contract.schema.json   # Schema for skill contracts
│   ├── memory.schema.json           # Schema for episodic/semantic memory records
│   └── workflow.schema.json         # Schema for workflow definitions
├── agent_workspace/
│   ├── core/
│   │   ├── engine.py                # AgentEngine — closed-loop runtime
│   │   ├── router.py                # AgentRouter — streaming orchestration
│   │   ├── skill_loader.py          # Markdown SKILL.md Auto-Discovery
│   │   └── providers.py             # Multi-LLM provider abstraction
│   ├── skills/                      # Python tool & Markdown skill implementations
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
├── scripts/                         # Bootstrap and verification commands
└── workspace/                       # Generated topology state output
    ├── workspace.md                 # ASCII Topological DAG state
    ├── workspace.json               # Structured state graph
    ├── viewer.html                  # Zero-build frontend viewer
    └── agents/                      # Generated PAP Agent Specifications
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
| `POST` | `/v1/chat` | Synchronous agent request (supports optional `account_id` payload) |
| `POST` | `/v1/stream` | SSE stream with tool events (supports optional `account_id` payload) |
| `WS` | `/v1/stream_ws` | WebSocket bidirectional streaming |
| `WS` | `/v1/stream` | WebSocket multi-turn streaming |
| `POST` | `/v1/task` | Async task submission (supports optional `account_id` payload) |
| `GET` | `/v1/session/{id}` | Session memory and task state |
| `GET` | `/v1/memory` | Long-term memory records |
| `GET` | `/v1/memory/query` | Long-term memory search |
| `GET` | `/v1/metrics` | Prometheus metrics |
| `GET/PUT` | `/v1/config` | Local LLM configuration |
| `GET` | `/v1/accounts` | List configured accounts and token usages |
| `POST` | `/v1/accounts` | Add or update an LLM provider account |
| `DELETE` | `/v1/accounts/{id}`| Delete a specific account |
| `GET` | `/v1/accounts/active`| Get the active account |
| `POST` | `/v1/accounts/active`| Set active account for LLM calls

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

### Developer Operations CLI & Workflows

LAS provides a unified Developer CLI toolbelt (`agent_workspace/cli.py`) for managing runtime skills, memory, validation, and declarative n8n-like workflows:

```powershell
# List all registered local and global skills
python agent_workspace/cli.py --list-skills

# Describe a specific skill contract schema in YAML
python agent_workspace/cli.py --describe-skill calculate

# Run zero-dependency PAP workspace validation
python agent_workspace/cli.py --validate

# Read/Write persistent long-term memory records
python agent_workspace/cli.py --session my-session --memory-write sem-rule-1 "Direct memory update"
python agent_workspace/cli.py --session my-session --memory-read sem-rule-1

# Execute a declarative DAG workflow defined in .agent/workflows/<id>.md
python agent_workspace/cli.py --run-workflow my_workflow

# Resume a failed workflow run from its last checkpoint
python agent_workspace/cli.py --run-workflow my_workflow --resume
```

Declarative workflows run step-by-step using an **Asynchronous Workflow Engine** (`core/workflow_engine.py`) which tracks state transitions (`pending` -> `running` -> `success` / `failed`), manages dynamic Jinja2 parameter rendering, and supports checkpoint serialization to `.agent/workflows/runs/<session_id>.json` for automatic resumption.

### Contract Pipeline & Workspace Contexts

```powershell
python agent_workspace\pap_validate.py
python agent_workspace\tool_manifest.py sync
python agent_workspace\tool_manifest.py validate
```

- `pap_validate.py` is dependency-free and checks the `.agent/` workspace contract.
- `tool_manifest.py` reflects live runtime tools and verifies that each tool has a matching PAP skill contract.
- **Formal JSON Schemas (`spec/`)**: Strictly defines and validates the schema rules for Agents, Skills, Memories, and Workflows under `spec/*.json`.
- **Dynamic Context Loading**: The runtime engine (`AgentEngine`) auto-discovers and dynamic-loads `.agent/agent.md` (Agent Identity/Persona) and `.agent/agent_tasks.md` (Task Queue) as active knowledge contexts, injecting them directly into the system prompts.
- **Agent Guidelines**: Strict end-of-turn development checklist rules are configured in `AGENT.md` (e.g., bug checks, architectural checks, bilingual README updates, and Git verification).

### Product Roadmap

| Phase | Status | Scope |
| --- | --- | --- |
| P0 | ✅ Done | UTF-8 docs, bootstrap/verify, generated-data governance |
| P1 | ✅ Done | FastAPI WebSocket streaming, native multi-provider (Claude / GPT-4o), Redis memory backend |
| P2 | ✅ Done | Governed memory (episodic, semantic, retention, delete, citation), Topological Workspace schema & viewer |
| P3 | ✅ Done | Delegation hardening: timeout protection, worker config, tool loops, cost measurement |
| P4 | ✅ Done | Multi-Account support & real-time token tracking for seamless vibe coding |
| P5 | 🔲 Next | Package LAS as local-first, auditable, AI-maintainable, protocol-compatible runtime infrastructure |

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
- **Markdown SkillLoader** — 完美橋接 `anthropics/skills` 格式，讓 `SKILL.md` 自動轉換成 Pydantic 可執行的原生工具
- **結構化日誌系統 (Structured Logs)** — 透過優雅的壓縮演算法自動精簡已完成任務的日誌，並支援月份歸檔，保持記憶體最小佔用
- **零編譯視覺化前端 (Zero-Build Viewer)** — 位於 `workspace/viewer.html`，以純淨的 Vanilla JS、Tailwind CSS 與 Dagre 打造極輕量無相依的前端展示
- **多模型 LLM 抽象層** — 原生支援 Gemini、Claude 3.5 Sonnet、GPT-4o、Ollama，零供應商鎖定
- **可插拔記憶體後端** — SQLite (預設) 與 Redis 企業級持久化長期記憶

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

**選項 A (極輕量無編譯 Viewer):**
```powershell
python -m http.server 8000
# 打開 http://localhost:8000/workspace/viewer.html
```

**選項 B (完整 React Tauri App):**
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

### 開發者指令集與工作流 (Developer CLI & Workflows)

LAS 提供統一的開發者工具箱 (`agent_workspace/cli.py`)，用於管理執行期工具、長期記憶、工作區驗證以及執行 n8n 式的宣告式工作流：

```powershell
# 列出所有已註冊的本地與全域工具合約
python agent_workspace/cli.py --list-skills

# 以 YAML 格式展示特定工具合約細節
python agent_workspace/cli.py --describe-skill calculate

# 執行零相依性 PAP 工作區合約結構驗證
python agent_workspace/cli.py --validate

# 讀取/寫入持久化長期記憶記錄
python agent_workspace/cli.py --session my-session --memory-write sem-rule-1 "直接更新記憶"
python agent_workspace/cli.py --session my-session --memory-read sem-rule-1

# 執行定義於 .agent/workflows/<id>.md 的宣告式 DAG 工作流
python agent_workspace/cli.py --run-workflow my_workflow

# 從上次失敗的檢查點恢復（Resume）工作流執行
python agent_workspace/cli.py --run-workflow my_workflow --resume
```

宣告式工作流採用**非同步工作流引擎** (`core/workflow_engine.py`) 進行，全程追蹤狀態轉換（`pending` -> `running` -> `success` / `failed`），並會將進度與資料序列化至 `.agent/workflows/runs/<session_id>.json` 供隨時中斷重啟。

### 驗證命令與 PAP 整合

```powershell
.\scripts\verify.cmd -SkipViewer
python agent_workspace\pap_validate.py
python agent_workspace\tool_manifest.py validate
python agent_workspace\topology_stream.py stream --msg "test" --session verify-p1 --dry-run
```

- **規格 Schema 正式化 (`spec/`)**：在根目錄的 `spec/` 資料夾內定義了 Agent 身分、Skill 工具合約、Episodic/Semantic 記憶體以及 Workflow 流程的完整 JSON Schema 規範。
- **動態上下文載入 (Dynamic Context Loading)**：LAS 執行引擎 (`AgentEngine`) 原生支援動態載入 `.agent/` 目錄下的 PAP 協定合約。它會自動偵測並解析目前運行的 Agent 身分宣告檔 (`.agent/agent.md`) 以及任務隊列 (`.agent/agent_tasks.md`)，並將其自動注入 Jinja2 系統提示詞中，使 Agent 具備完全的身分與任務自我認知。
- **自我檢核檢索 (`AGENT.md`)**：專案根目錄下的 `AGENT.md` 定義了每次工作結束時的 5 項核心自我檢核步驟（Bug/冗餘清理、架構職責審查、`.agent/` 自主更新、中英文 `README.md` 分開維護、Git Commit/Push 前預檢測試），確保專案在開發中自我演進且架構不走樣。

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
| P3 | ✅ 完成 | delegation 完整化：超時保護、取消、追蹤、工具限制、成本與 token 度量 |
| P4 | ✅ 完成 | 多帳號管理與即時 Token 用量/額度追蹤，不中斷 Vibe Coding 流程 |
| P5 | 🔲 下一步 | 商業包裝：local-first、auditable、AI-maintainable、protocol-compatible |
