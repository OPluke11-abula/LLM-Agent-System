# FindAi Studio LLM Agent System

[English](#english) | [繁體中文](#繁體中文)

---

## English

LAS is a readable, maintainable, observable, and portable local Agent Runtime
with a visual control-plane direction. It is not trying to become another
generic LLM framework. Its product value is the combination of:

- a small Python runtime for file-aware, tool-using agents
- PAP-compatible workspace contracts under `.agent/`
- FastAPI REST/SSE adapter
- multi-provider LLM abstraction
- local working memory and long-term memory backend
- topology bridge for session observability
- local viewer material for visual operation

Market message:

> An AI-maintainable agent runtime you can read, verify, and operate locally. Natively supports Claude 3.5 Sonnet and GPT-4o.

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

If you only need the backend API:

```powershell
uvicorn agent_workspace.api:app --host 0.0.0.0 --port 8000
curl http://127.0.0.1:8000/v1/health
```

### Core Positioning

LAS should be developed as an **AI-maintainable Agent Runtime reference
implementation**, not a chatbot app. The contract-first layer is a product
feature: it lets human developers and AI agents safely inspect, verify, and
extend the repo without guessing hidden conventions.

### Architecture Principles

- Keep `agent_workspace/core/` focused on runtime behavior.
- Add HTTP, topology, viewer, and protocol behavior through adapters and
  bridge layers.
- Treat `.agent/`, PAP sync, and tool contracts as the AI handoff surface.
- Treat runtime JSON, memory DBs, caches, and topology state as generated data.
- Prefer reliable delegation contracts over unbounded swarm behavior.

### Runtime Layout

| Path | Purpose |
| --- | --- |
| `.agent/` | PAP-compatible workspace contract |
| `agent_workspace/core/` | engine, router, provider abstraction |
| `agent_workspace/skills/` | reflected Python tools |
| `agent_workspace/memory/` | generated session and long-term memory data |
| `agent_workspace/api.py` | FastAPI adapter |
| `agent_workspace/tool_manifest.py` | runtime-tool to PAP-contract pipeline |
| `agent_workspace/topology_bridge.py` | topology state serialization |
| `agent_workspace/topology_stream.py` | stream wrapper that emits topology events |
| `viewer/` | local visual console material |
| `scripts/` | bootstrap and verification commands |

### Provider Configuration

LAS reads the active provider from `agent_workspace/config.yaml`.

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
| `openai` | `gpt-4o` | `OPENAI_API_KEY` |
| `anthropic` | `claude-3-5-sonnet-latest` | `ANTHROPIC_API_KEY` |
| `ollama` | `llama3.1` | local Ollama server |

### Contract Pipeline

```powershell
python agent_workspace\pap_validate.py
python agent_workspace\tool_manifest.py sync
python agent_workspace\tool_manifest.py validate
```

`pap_validate.py` is dependency-free and checks the `.agent/` workspace
contract. `tool_manifest.py` reflects live runtime tools and verifies that each
tool has a matching PAP skill contract.

### API Surface

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/v1/health` | health, provider, readiness |
| `GET` | `/v1/tools` | live PAP-aligned tool manifest |
| `POST` | `/v1/chat` | synchronous agent request |
| `POST` | `/v1/stream` | SSE stream with tool events |
| `POST` | `/v1/task` | async task submission |
| `GET` | `/v1/session/{id}` | session memory and task state |
| `GET` | `/v1/memory` | long-term memory records |
| `GET` | `/v1/memory/query` | long-term memory search |
| `GET` | `/v1/metrics` | Prometheus metrics |
| `GET/PUT` | `/v1/config` | local LLM configuration |

### Topology Bridge

Dry-run topology generation without calling an LLM:

```powershell
python agent_workspace/topology_stream.py stream --msg "test" --session verify-p1 --dry-run
```

Default output:

```text
workspace/topology_state.json
```

### Product Roadmap

P0:
- ✅ UTF-8 documentation and logs
- ✅ clean generated-data governance
- ✅ one-command bootstrap and verification
- ✅ fresh-environment validation for PAP and tool contracts

P1:
- ✅ FastAPI WebSocket SSE adapter
- ✅ Native Multi-provider support (Claude 3.5 Sonnet, GPT-4o)
- make topology viewer a session observability and control plane
- add replay, event timeline, tool failure heatmap, RBAC trace, and session diff

P2:
- ✅ evolve memory into governed memory: episodic, semantic, user preference, and project memory with retention, delete, citation, confidence, and privacy boundaries

P3:

- harden delegation: cancellation, traceability, replay, audit, tool limits, and
  cost measurement

P4:

- package LAS as local-first, auditable, AI-maintainable, and
  protocol-compatible runtime infrastructure

---

## 繁體中文

LAS 的定位是「可讀、可維護、可觀測、可移植的本地 Agent Runtime + 視覺控制台」。
它不應再被包裝成普通聊天 agent 或一般 LLM framework，而應成為人和 AI 都能安全
接手維護的 Agent Runtime 標準樣板。原生支援 Claude 3.5 Sonnet 與 GPT-4o。

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

Provider SDK 可選安裝；只在本機需要特定 hosted provider 時執行：

```powershell
pip install -r requirements-providers.txt
```

安裝 dependencies 時建議使用標準 Windows CPython。MSYS/MinGW Python 可能會改成
本機編譯 native wheels，導致 `pydantic-core` 這類套件安裝失敗。

啟動 FastAPI：

```powershell
uvicorn agent_workspace.api:app --host 0.0.0.0 --port 8000
curl http://127.0.0.1:8000/v1/health
```

### 產品核心

LAS 的護城河不是「又一個聊天 agent」，而是 contract-first runtime：

- `.agent/` 是 AI 接手 repo 的協作合約
- `tool_manifest.py` 把 runtime tool 反射成 PAP contract
- `pap_validate.py` 是零依賴 workspace contract gate
- topology bridge 把 runtime session 轉成可視覺化狀態
- memory backend 是未來 memory governance 的基礎
- delegation 應先做可靠、可追蹤、可審計，而不是追求 swarm 噱頭

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

P0：✅ 亂碼修復、bootstrap/verify、generated data 治理。  
P1：✅ FastAPI WebSocket 串流支援、✅ 多模型原生支援 (Claude 3.5 / GPT-4o)。 topology viewer 升級成 session observability/control plane。  
P2：✅ memory backend 升級成可治理、可刪除、可引用來源的產品能力 (Governed Memory)。  
P3：delegation contract 完整化，不追求 swarm 噱頭。  
P4：✅ 商業包裝：local-first、auditable、AI-maintainable、protocol-compatible。
