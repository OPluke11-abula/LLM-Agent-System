# FindAi Studio LLM Agent System 🤖

[English](#english) | [繁體中文](#繁體中文)

---

# English

A universal, enterprise-grade boilerplate template for LLM Agents. Designed to be cloned and customized by AI for any specific domain, featuring dynamic Jinja2 prompting, Pydantic tool registration, and a dual-track architecture.

## 🌟 Key Features

- **Dual-Track Architecture**: Separates Persona knowledge (`knowledge_base/`) from executable functions (`skills/`).
- **Event-Driven CLI**: Run interactions easily with unified `run.py` entry points.
- **Provider Abstraction**: Easily swap between LLM providers (currently supports Google GenAI) without heavy third-party bloat.
- **Partial Async & Streaming**: Non-blocking I/O with built-in Step-Broadcasting for ultra-smooth UI experiences.
- **Memory Isolation**: Session-based memory storage to support multiple users simultaneously.
- **Enterprise Defenses**: Includes Role-Based Access Control (RBAC) for tools, Semantic Routing for chat vs. task intents, and Self-Correction fallback to break out of hallucination loops.

## 🚀 Quick Start

### 1. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 2. Set API Key
Set your Gemini API key in your terminal before running:
```powershell
# Windows PowerShell
$env:GOOGLE_API_KEY="your-api-key-here"

# Linux / macOS
export GOOGLE_API_KEY="your-api-key-here"
```

## 💻 CLI Usage

The workspace uses `run.py` as the main event dispatcher.

### Check Engine Status
View loaded knowledge, personas, and auto-discovered tools.
```powershell
python agent_workspace/run.py summary
```

### Run Closed-Loop Test
Run an automated test to ensure the LLM can properly call tools and reason.
```powershell
python agent_workspace/run.py test --session test-123
```

### Single Turn Chat
Send a simple text message to the agent.
```powershell
python agent_workspace/run.py chat --msg "Hello, what tools do you have?" --session my-session
```

### Streaming Chat (✨ Next-Gen)
Send a message and watch the agent's thought process and tool execution in real-time.
```powershell
python agent_workspace/run.py stream --msg "Calculate 123 * 456" --session stream-test
```

## 🧠 For AI Assistants

If you are an AI assistant trying to customize this boilerplate for the user, **DO NOT CHANGE THE CORE ARCHITECTURE**. 

Please strictly follow the rules defined in:
- `agent_workspace/INSTRUCTIONS_FOR_AI.md` (Universal Rules)
- `AGENTS.md` (Project-specific Instructions)

---

# 繁體中文

這是一個為 LLM Agent 打造的通用、企業級底層框架模板。專為「讓 AI 自動為你客製化」而設計，具備動態 Jinja2 提示詞注入、Pydantic 工具自動反射註冊以及雙軌架構。

## 🌟 核心特色

- **雙軌架構 (Dual-Track Architecture)**: 將 Persona 知識庫 (`knowledge_base/`) 與可執行的功能工具 (`skills/`) 職責分離。
- **事件驅動終端 (Event-Driven CLI)**: 所有的操作都透過 `run.py` 這個統一的事件分發中心來執行。
- **輕量模型抽象 (Provider Abstraction)**: 輕鬆切換不同的 LLM 供應商 (目前支援 Google GenAI) 而不需引入沉重的第三方依賴。
- **局部異步與串流廣播 (Partial Async & Streaming)**: 不阻塞的 I/O 搭配內建的狀態廣播，打造極致流暢的使用者體驗。
- **多租戶記憶 (Memory Isolation)**: 基於 Session 的記憶隔離機制，支援多使用者同時對話。
- **企業級防護**: 內建工具權限控管 (RBAC)、意圖分流路由 (自動過濾純聊天)，以及錯誤自癒機制 (連續報錯 3 次主動中斷)。

## 🚀 快速開始

### 1. 安裝依賴
```powershell
pip install -r requirements.txt
```

### 2. 設定金鑰
在執行前，請先於終端機設定您的 Gemini API Key：
```powershell
# Windows PowerShell
$env:GOOGLE_API_KEY="your-api-key-here"

# Linux / macOS
export GOOGLE_API_KEY="your-api-key-here"
```

## 💻 使用說明

所有的操作都透過 `run.py` 執行。

### 檢查引擎狀態
查看當前載入的知識庫、Persona 以及被自動發現的工具。
```powershell
python agent_workspace/run.py summary
```

### 執行閉環測試
執行自動化測試，確保 LLM 能夠正確呼叫工具並完成推論。
```powershell
python agent_workspace/run.py test --session test-123
```

### 單次對話
發送單一訊息給 Agent。
```powershell
python agent_workspace/run.py chat --msg "你好，請問你有什麼功能？" --session my-session
```

### 串流對話 (✨ 新功能)
發送訊息，並像打字機一樣即時觀看 Agent 的思考過程、工具呼叫與最終回覆。
```powershell
python agent_workspace/run.py stream --msg "幫我計算 123 乘以 456" --session stream-test
```

## 🧠 給未來 AI 助手的開發指南

如果您是正在幫助使用者客製化此專案的 AI 助手，**請絕對不要修改核心架構**。

請嚴格遵守以下文件中的規則：
- `agent_workspace/INSTRUCTIONS_FOR_AI.md` (全局通用規則)
- `AGENTS.md` (專案特定規則)
