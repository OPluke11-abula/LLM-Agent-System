# 🌌 FindAi Studio — LLM Agent System (LAS)

<div align="center">

![GitHub License](https://img.shields.io/badge/license-Elastic%202.0-blueviolet?style=for-the-badge)
![Python Version](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.14-blue?style=for-the-badge)
![Framework Protocol](https://img.shields.io/badge/protocol-PAP%20v0.1.0-orange?style=for-the-badge)
![Build Status](https://img.shields.io/badge/tests-142%20passed%20%2F%20100%25%20green-success?style=for-the-badge)

### [English](#-english) | [繁體中文](#-繁體中文)

</div>

---

## 🌐 English

> ### 🧠 **The First AI-Maintainable Agent Framework**
> Stop fighting rigid framework abstractions. FindAi Studio uses a **Contract-First design** (`.agent/` PAP + `INSTRUCTIONS_FOR_AI.md`) that lets cutting-edge LLMs safely understand, refactor, and extend your Agent workflows autonomously. **It's not just an AI Agent — it's an AI that builds your AI.**
>
> *Natively supports Gemini, Claude 3.5 Sonnet, GPT-4o, and Ollama with zero vendor lock-in.*

LAS is an extremely readable, maintainable, observable, and portable local Agent Runtime with a visual multi-dashboard control-plane. It is built upon four pillars:

* 🗺️ **Topological Workspace** — A node-based visual control-plane that transforms complex multi-agent sessions into an infinite canvas of interconnected task blocks.
* 🔏 **Contract-First Handoff** — PAP-compatible `.agent/` workspace contracts that allow humans and AI to safely inspect, verify, and extend the codebase.
* 🏢 **Agent Corporate Swarm** — Runs role-specialized agents concurrently (CEO, Developer, Auditor) operating collectively like an agile software company.
* 🧠 **Self-Healing & Self-Evolving Swarm** — Features automated runtime error self-healing, dynamic multi-account failover swapping, dynamic LLM upscaling/downscaling, SQLite FTS5 semantic indexing, runtime dynamic skill discovery & verification, and dynamic event-loop bottleneck self-tuning.


---

### 🗺️ Live Topological Dagre View

```text
 ┌────────────────────────────────────────────────────────┐
 │            Moderator View: CEO Strategy Room           │
 └───────────────────────────┬────────────────────────────┘
                             │
                             │ (Handoff Edge: glowing gold)
                             ▼
 ┌────────────────────────────────────────────────────────┐
 │            R&D Center: Developer Workspace             │
 └───────────────────────────┬────────────────────────────┘
                             ├─────────────────────────────┐
                             │                             │ (Tool/API Edge: glowing blue)
                             ▼                             ▼
 ┌───────────────────────────────────────┐     ┌───────────────────────────────────────┐
 │       Auditor: Telemetry & Billing    │     │       HITL Gate: Human Approval       │
 │   (Real-time Token & cost charts)     │     │      (goldPulse amber border)         │
 └───────────────────────────────────────┘     └───────────────────────────────────────┘
```

---

### 🏢 Corporate Swarm Architecture

```mermaid
graph TD
    subgraph CEO_Dashboard [CEO / Moderator Control Plane]
        A["1. Dispatch Objective"] --> B["2. Task Decomposition"]
        B --> C["3. Delegate to Specialized Workers"]
    end
    
    subgraph Developer_Dashboard [R&D Center]
        D["4. Load Skill Contracts (.agent/skills/)"] --> E["5. Live CLI Linter & Pytest Runner"]
        E --> F["6. Auto-generate Workflows (.agent/workflows/)"]
    end
    
    subgraph Auditor_Dashboard [Finance & Observability]
        G["7. Real-time Token Tracking"] --> H["8. Failover Account Rotator"]
        H --> I["9. Cost Billing Logs (USD)"]
    end
    
    C -->|Dynamic WebSocket WS| D
    F -->|Telemetry Metrics| G
```

---

### ⚡ Quick Start (Three-Minute Setup)

#### 1. Setup Environment & Validate
```powershell
git clone <repo-url>
cd LLM-Agent-System
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
.\scripts\verify.cmd -SkipViewer
```

#### 2. Start the API Server
```powershell
uvicorn agent_workspace.api:app --host 0.0.0.0 --port 8000
```

#### 3. Launch Visual Dashboards
* **Option A (Zero-Build Vanilla HTML5 Panel):**
  ```powershell
  python -m http.server 8000
  # Open http://localhost:8000/workspace/viewer.html
  ```
* **Option B (Full Vite + React Flow Tauri Desktop App):**
  ```powershell
  cd viewer
  npm install
  npm run dev
  ```
  *(To compile a standalone high-performance desktop `.exe` app, execute `npm run tauri build`)*

---

### 🔌 Developer Operations CLI

LAS features a unified operations toolbelt (`agent_workspace/cli.py`):

```powershell
# List all registered local & global skills
python agent_workspace/cli.py --list-skills

# Run static schema checks on all PAP contracts
python agent_workspace/cli.py --validate

# Execute a declarative DAG workflow script
python agent_workspace/cli.py --run-workflow my_workflow

# Run interactive closed-loop session with live HITL approvals
python agent_workspace/cli.py --chat
```

---

## 🌐 繁體中文

> ### 🧠 **首個讓 AI 幫你客製化與重構 AI 的框架**
> 拒絕僵硬死板的框架抽象。FindAi Studio 採用 **合約優先 (Contract-First) 設計** (`.agent/` PAP + `INSTRUCTIONS_FOR_AI.md`)，讓最尖端的大模型在**不污染、不破壞核心架構**的前提下，安全地自主理解、重構、編譯並擴充你的工作流。**它不僅是一個智慧體 —— 它是一個幫你生產智慧體的自動化工廠。**
>
> *原生無縫支援 Gemini, Claude 3.5 Sonnet, GPT-4o 與 Ollama，零供應商鎖定。*

---

### 🗺️ 實時拓撲 Dagre 觀測圖

```text
 ┌────────────────────────────────────────────────────────┐
 │             Moderator View: CEO 戰略指揮官視角          │
 └───────────────────────────┬────────────────────────────┘
                             │
                             │ (Handoff 邊線：琥珀金粒子流)
                             ▼
 ┌────────────────────────────────────────────────────────┐
 │              R&D Center: 開發工程師畫布編輯器           │
 └───────────────────────────┬────────────────────────────┘
                             ├─────────────────────────────┐
                             │                             │ (Tool/API 邊線：流動藍光)
                             ▼                             ▼
 ┌───────────────────────────────────────┐     ┌───────────────────────────────────────┐
 │         Auditor: 財務計費與統計儀表板  │     │        HITL Gate: 人機審批閘口         │
 │     (實時 Token 統計與延遲折線圖)       │     │       (金黃脈動 goldPulse 邊框)        │
 └───────────────────────────────────────┘     └───────────────────────────────────────┘
```

---

### 🏢 公司化協同架構 (Mermaid)

```mermaid
graph TD
    subgraph CEO_Dashboard [CEO 戰略決策層]
        A["1. 派發企業總體 OKR"] --> B["2. 任務自動拓撲分解"]
        B --> C["3. 調度 delegate_task 指派子任務"]
    end
    
    subgraph Developer_Dashboard [R&D 開發中心]
        D["4. 載入 PAP 工具合約 (.agent/skills/)"] --> E["5. 自動編譯校驗與 Pytest 執行"]
        E --> F["6. 畫布一鍵匯出 workflows (.agent/workflows/)"]
    end
    
    subgraph Auditor_Dashboard [財務與觀測站]
        G["7. 實時 Token 計費稽核"] --> H["8. Fallback 帳號防線切換"]
        H --> I["9. 產出美元消費對帳單"]
    end
    
    C -->|動態 WebSocket 串流| D
    F -->|系統 Telemetry 指標| G
```

---

### ⚡ 快速啟動 (三分鐘環境搭建)

#### 1. 建立虛擬環境與校驗
```powershell
git clone <repo-url>
cd LLM-Agent-System
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
.\scripts\verify.cmd -SkipViewer
```

#### 2. 啟動 FastAPI 服務適配器
```powershell
uvicorn agent_workspace.api:app --host 0.0.0.0 --port 8000
```

#### 3. 啟動視覺化多重視角控制台
* **方案 A (零編譯 Vanilla HTML5 輕量面板):**
  ```powershell
  python -m http.server 8000
  # 開啟 http://localhost:8000/workspace/viewer.html
  ```
* **方案 B (Vite + React Flow Tauri 專業桌面端):**
  ```powershell
  cd viewer
  npm install
  npm run dev
  ```
  *(若要編譯為免安裝單一執行檔 `.exe`，請執行 `npm run tauri build`)*

---

### 🚥 本地開發者工具 CLI 

LAS 提供一站式開發者工具箱 (`agent_workspace/cli.py`)：

```powershell
# 列出所有註冊的本地與全域工具 (Skills)
python agent_workspace/cli.py --list-skills

# 執行零依賴的 PAP 工作區合約靜態校驗
python agent_workspace/cli.py --validate

# 執行定義於 .agent/workflows/ 的宣告式工作流腳本
python agent_workspace/cli.py --run-workflow my_workflow

# 啟動具有實時 HITL 人機審批的互動式對話
python agent_workspace/cli.py --chat
```

---

### ⚖️ License

LAS is distributed under the **Elastic License 2.0 (ELv2)**. Free to use, modify, and distribute internally, but hosting the software as a managed service is prohibited. See `LICENSE` for details.
