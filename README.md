# FindAi Studio — LLM Agent System (LAS)

LAS is a local, contract-first agent runtime with a FastAPI service, a Python
operations CLI, Portable Agent Protocol (PAP) workspace contracts, and a
Tauri/React visual control plane.

[English](#english) | [繁體中文](#繁體中文)

## English

### What LAS provides

- A typed Python runtime under agent_workspace/core for routing, memory,
  governance, audit, sandboxing, provider access, and multi-agent workflows.
- PAP workspace contracts under .agent with protocol_version 1.0.0.
- Read-only structural code-graph tools with bounded output.
- A React 19 + Tauri 2 desktop viewer for topology, task flow, activity,
  governance, settings, token-mode telemetry, and design-agent state.
- Hosted provider adapters for Google Gemini, Anthropic, and OpenAI, plus local
  Ollama support. Configure only the provider you intend to use.

### Requirements

- Windows 10 or Windows 11
- Python 3.11 or newer
- Node.js 22 LTS or newer
- Rust stable and the Tauri 2 Windows prerequisites when building the desktop
  installer

### Quick start

#### 1. Install and verify the Python runtime

~~~powershell
git clone https://github.com/OPluke11-abula/LLM-Agent-System.git
cd LLM-Agent-System
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\scripts\verify.cmd -SkipViewer
~~~

Optional Google provider dependencies:

~~~powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-providers.txt
~~~

Provider credentials are read from GOOGLE_API_KEY, OPENAI_API_KEY, or
ANTHROPIC_API_KEY. Ollama does not require a hosted-provider API key. Keep
credentials in local environment files; never commit them.

#### 2. Start the API

~~~powershell
.\.venv\Scripts\python.exe -m uvicorn agent_workspace.api:app --host 127.0.0.1 --port 8000
~~~

#### 3. Start the web viewer

~~~powershell
npm.cmd --prefix viewer install
npm.cmd --prefix viewer run dev
~~~

#### 4. Start the Tauri desktop viewer

~~~powershell
$env:AGENT_WORKSPACE_DIR="$PWD\workspace"
npm.cmd --prefix viewer run tauri -- dev
~~~

### Windows release artifacts

The prebuilt version 0.1.1 NSIS installer is stored in releases:

- ai-agent-topology-viewer_0.1.1_x64-setup.exe

Verify a downloaded artifact before running it:

~~~powershell
Get-FileHash .\releases\ai-agent-topology-viewer_0.1.1_x64-setup.exe -Algorithm SHA256
~~~

Expected SHA-256:
`18448AB860EAA2BD795CA4DE5BA2F80682E1150369C0212423A1BCFE752BABA5`.
This repository build is not Authenticode-signed; verify the hash before use.

Build the verified NSIS installer locally:

~~~powershell
npm.cmd --prefix viewer run tauri -- build --bundles nsis
~~~

Tauri writes the installer below viewer/src-tauri/target/release/bundle/nsis.
MSI packaging is not claimed by this release because WiX ICE validation failed
in the current Windows environment.

### Developer CLI

~~~powershell
# List registered runtime tools
.\.venv\Scripts\python.exe -m agent_workspace.cli --list-skills

# Validate the PAP workspace
.\.venv\Scripts\python.exe -m agent_workspace.cli --validate

# Run the workspace linter
.\.venv\Scripts\python.exe -m agent_workspace.cli lint .

# Run a declarative workflow
.\.venv\Scripts\python.exe -m agent_workspace.cli --run-workflow WORKFLOW_ID

# Start an interactive agent session
.\.venv\Scripts\python.exe -m agent_workspace.cli --chat

# Validate runtime/PAP tool parity and scan for secrets
.\.venv\Scripts\python.exe -m agent_workspace.tool_manifest validate

# Build the local structural code graph
.\.venv\Scripts\python.exe -m agent_workspace.codebase_index --root .
~~~

### Verification

The authoritative repository gate is:

~~~powershell
.\scripts\verify.cmd
~~~

It runs Python compilation, the full pytest suite, PAP validation, runtime tool
contract checks, secret scanning, the viewer production build, UI verification,
and Swarm governance UI checks.

Focused viewer checks:

~~~powershell
npm.cmd --prefix viewer run build
npm.cmd --prefix viewer run verify:ui
npm.cmd --prefix viewer run test:swarm-ui
~~~

Screenshot verification is available through:

~~~powershell
npm.cmd --prefix viewer run verify:ui:screenshots
~~~

Set UI_VERIFY_STRICT_SCREENSHOTS=1 when screenshot capture must be a hard gate.

### Repository layout

| Path | Purpose |
|---|---|
| agent_workspace/core | Runtime business logic |
| agent_workspace/routes | FastAPI adapters |
| agent_workspace/skills | Python runtime tool implementations |
| .agent | PAP contracts, workflows, roles, and durable project knowledge |
| viewer | React/Tauri control plane |
| scripts/verify.cmd | Authoritative verification gate |
| releases | Tracked Windows installers |

### Git safety hooks

Verification does not modify .git/hooks by default. Install the optional local
guard only when you want it:

~~~powershell
.\scripts\verify.cmd -SkipTests -SkipViewer -InstallGitHooks
~~~

The generated pre-push hook rejects destructive or non-fast-forward Git
operations unless a human intentionally supplies the documented override.

## 繁體中文

LAS 是一套合約優先的本地 AI Agent Runtime，整合 FastAPI、Python 開發者
CLI、Portable Agent Protocol（PAP）工作區合約，以及 Tauri/React 視覺控制台。

### 主要功能

- agent_workspace/core 提供路由、記憶、治理、審計、沙箱、模型供應商與
  多代理協作核心。
- .agent 使用 protocol_version 1.0.0，保存 PAP 合約、工作流與專案知識。
- 提供有輸出上限的唯讀結構化程式碼圖工具。
- React 19 + Tauri 2 桌面控制台涵蓋拓撲、任務流程、活動記錄、治理、
  設定、Token 模式遙測與 Design Agent 狀態。
- 支援 Google Gemini、Anthropic、OpenAI 與本地 Ollama；只需設定實際使用
  的供應商。

### 快速安裝

~~~powershell
git clone https://github.com/OPluke11-abula/LLM-Agent-System.git
cd LLM-Agent-System
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\scripts\verify.cmd -SkipViewer
~~~

若使用 Google provider，再安裝可選依賴：

~~~powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-providers.txt
~~~

Hosted provider 分別使用 GOOGLE_API_KEY、OPENAI_API_KEY 或
ANTHROPIC_API_KEY。請只放在本機環境設定中，不可提交到 Git。

### 啟動 API 與 Viewer

~~~powershell
.\.venv\Scripts\python.exe -m uvicorn agent_workspace.api:app --host 127.0.0.1 --port 8000
npm.cmd --prefix viewer install
npm.cmd --prefix viewer run dev
~~~

啟動 Tauri 桌面版：

~~~powershell
$env:AGENT_WORKSPACE_DIR="$PWD\workspace"
npm.cmd --prefix viewer run tauri -- dev
~~~

### Windows 0.1.1 安裝檔

releases 目錄包含：

- ai-agent-topology-viewer_0.1.1_x64-setup.exe

SHA-256：
`18448AB860EAA2BD795CA4DE5BA2F80682E1150369C0212423A1BCFE752BABA5`。
此版本未使用 Authenticode 簽章，執行前請先核對雜湊值。

自行建置已驗證的 NSIS 安裝檔：

~~~powershell
npm.cmd --prefix viewer run tauri -- build --bundles nsis
~~~

此版本不宣告 MSI 建置成功；目前 Windows 環境的 WiX ICE 校驗失敗。

### 完整驗證

~~~powershell
.\scripts\verify.cmd
~~~

此命令會執行 Python 編譯、完整 pytest、PAP 校驗、runtime tool 合約與
秘密掃描、viewer production build、UI verifier，以及 Swarm governance
UI 驗證。只有實際完成的檢查才可宣告通過。

## License

Elastic License 2.0. See LICENSE.
