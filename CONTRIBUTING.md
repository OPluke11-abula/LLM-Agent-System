# Contributing to FindAi Studio — LAS

[English](#english) | [繁體中文](#繁體中文)

---

## English

Welcome! FindAi Studio LLM Agent System (LAS) is the **first AI-Maintainable Agent framework**. Because both humans and AI agents collaborate to build and extend this repository, all contributions must strictly follow this **Contract-First Development SOP** to prevent regression, context drift, and architectural decay.

### 🔒 Core Guidelines

#### 1. Contract-First Development
Before writing any Python code for a new capability/tool:
- Create or update its PAP Skill Contract under `.agent/skills/<skill_id>.md`.
- Declare input/output schemas using standard PAP JSON properties.
- Keep proprietary references separate; write generic local Python tools.

#### 2. Dual-Track Sync
Once you have written or modified a Python skill in `agent_workspace/skills/`:
- Run the sync tool to align runtime reflection with the PAP documents:
  ```bash
  python agent_workspace/tool_manifest.py sync
  ```
- Verify manifest integrity:
  ```bash
  python agent_workspace/tool_manifest.py validate
  ```
- Run static workspace linting:
  ```bash
  python agent_workspace/cli.py lint
  ```

#### 3. Strict 100% Green Telemetry
Every contribution must maintain full unit and integration test coverage without event-loop hangs:
- Run the complete pytest suite before pushing:
  ```bash
  python -m pytest --tb=short
  ```
- Ensure zero hangs in multi-agent or HITL simulation test cases.

---

## 繁體中文

歡迎！FindAi Studio LLM Agent System (LAS) 是 **全球首個可由 AI 自主維護與演進（AI-Maintainable）的智慧體框架**。由於本專案是由人類與 AI 智慧體共同開發與維護，所有的代碼提交都必須嚴格遵循這套 **合約優先 (Contract-First) 開發規範**，以確保架構不走樣。

### 🔒 核心開發規範

#### 1. 合約優先開發 (Contract-First)
在為智慧體撰寫任何 Python 新工具（Skills）之前：
- 必須先在 `.agent/skills/<skill_id>.md` 建立或更新其 PAP 工具合約。
- 使用標準 PAP JSON 屬性宣告輸入與輸出 Schema，標註敏感度與角色權限。

#### 2. 雙軌反射同步 (Dual-Track Sync)
當您在 `agent_workspace/skills/` 寫好 Python 工具代碼後：
- 執行同步腳本，自動將代碼反射規格寫回 PAP Markdown 合約：
  ```bash
  python agent_workspace/tool_manifest.py sync
  ```
- 驗證合約與代碼是否 100% 對照：
  ```bash
  python agent_workspace/tool_manifest.py validate
  ```
- 執行工作區靜態檢查：
  ```bash
  python agent_workspace/cli.py lint
  ```

#### 3. 100% 綠燈單元測試 (Strict Pytest Validation)
任何代碼提交前，必須確保測試套件完全無報錯、無卡死：
- 在本地執行完整測試：
  ```bash
  python -m pytest --tb=short
  ```
- 確保 Multi-Agent 辯論與人機審批（HITL）模擬測試沒有任何 Async Event-Loop 死結掛起。
