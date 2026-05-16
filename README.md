# FindAi Studio LLM Agent System 🤖

A universal, enterprise-grade boilerplate template for LLM Agents. Designed to be cloned and customized by AI for any specific domain, featuring dynamic Jinja2 prompting, Pydantic tool registration, and a dual-track architecture.

這是一個為 LLM Agent 打造的通用、企業級底層框架模板。專為「讓 AI 自動為你客製化」而設計，具備動態 Jinja2 提示詞注入、Pydantic 工具自動反射註冊以及雙軌架構。

---

## 🌟 Key Features (核心特色)

- **Dual-Track Architecture (雙軌架構)**: Separates Persona knowledge (`knowledge_base/`) from executable functions (`skills/`).
- **Event-Driven CLI (事件驅動終端)**: Run interactions easily with unified `run.py` entry points.
- **Provider Abstraction (輕量模型抽象)**: Easily swap between LLM providers (currently supports Google GenAI) without heavy third-party bloat.
- **Partial Async & Streaming (局部異步與串流廣播)**: Non-blocking I/O with built-in Step-Broadcasting for ultra-smooth UI experiences.
- **Memory Isolation (多租戶記憶)**: Session-based memory storage to support multiple users simultaneously.

---

## 🚀 Quick Start (快速開始)

### 1. Install Dependencies (安裝依賴)
```powershell
pip install -r requirements.txt
```

### 2. Set API Key (設定金鑰)
Set your Gemini API key in your terminal before running:
```powershell
# Windows PowerShell
$env:GOOGLE_API_KEY="your-api-key-here"

# Linux / macOS
export GOOGLE_API_KEY="your-api-key-here"
```

---

## 💻 CLI Usage (使用說明)

The workspace uses `run.py` as the main event dispatcher.
所有的操作都透過 `run.py` 這個事件分發中心來執行。

### Check Engine Status (檢查引擎狀態)
View loaded knowledge, personas, and auto-discovered tools.
查看當前載入的知識庫、Persona 以及被自動發現的工具。
```powershell
python agent_workspace/run.py summary
```

### Run Closed-Loop Test (執行閉環測試)
Run an automated test to ensure the LLM can properly call tools and reason.
執行自動化測試，確保 LLM 能夠正確呼叫工具並完成推論。
```powershell
python agent_workspace/run.py test --session test-123
```

### Single Turn Chat (單次對話)
Send a simple text message to the agent.
發送單一訊息給 Agent。
```powershell
python agent_workspace/run.py chat --msg "Hello, what tools do you have?" --session my-session
```

### Streaming Chat (串流對話 - ✨ 新功能)
Send a message and watch the agent's thought process and tool execution in real-time.
發送訊息，並像打字機一樣即時觀看 Agent 的思考過程、工具呼叫與最終回覆。
```powershell
python agent_workspace/run.py stream --msg "計算 123 乘以 456" --session stream-test
```

---

## 📁 Project Structure (專案結構)

```text
agent_workspace/
├── config.yaml              # Static parameters (Model, Temp, Max iterations)
├── agent.jinja2             # Dynamic system prompt template
├── run.py                   # Event-Driven CLI Router (Entry point)
├── core/
│   ├── engine.py            # Dual-parser engine (Knowledge + Tools)
│   ├── router.py            # Agent execution loop & Memory hooks
│   └── providers.py         # Lightweight LLM abstraction layer
├── knowledge_base/          # [Brain] SKILL.md files defining personas
├── skills/                  # [Hands] Pydantic-based callable tools (.py)
└── memory/                  # Session-isolated memory storage (.json)
```

## 🧠 For AI Assistants (給未來 AI 助手的開發指南)

If you are an AI assistant trying to customize this boilerplate for the user, **DO NOT CHANGE THE CORE ARCHITECTURE**. 
如果您是正在幫助使用者客製化此專案的 AI 助手，**請絕對不要修改核心架構**。

Please strictly follow the rules defined in:
請嚴格遵守以下文件中的規則：
- `agent_workspace/INSTRUCTIONS_FOR_AI.md` (Universal Rules)
- `AGENTS.md` (Project-specific Instructions)
