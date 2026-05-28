# PAP Programmer Job Prompt: Phase 12 — LAS Evolution: Multi-Dimensional Swarms, Self-Learning & Log Compaction

請先閱讀並理解 `ai_programmer_learning_guide.md` 手冊。剩下的引導詞如下：

---

## 📌 任務背景與目標
你是一位頂尖的 AI 系統架構師與全端資深開發者。你的目標是實現 **Portable Agent Protocol (PAP)** 任務規格中的 **Phase 12 — LAS Evolution (LAS 系統深度進化)**。

請嚴格遵守 `ai_programmer_learning_guide.md` 手冊中所定義的六大進化支柱，將本系統從簡單的「單向任務流程圖」進化為「多維度有向心智圖（分類拓撲連線）、里程碑日誌自動壓縮壓縮、自我學習錯誤資料庫、非同步平行多智慧體協作小公司」的終極完整體。

---

## 🗂️ 核心關聯檔案與路徑
- **自我學習手冊**：[.agent/ai_programmer_learning_guide.md](file:///d:/GitHub/LLM-Agent-System/.agent/ai_programmer_learning_guide.md)
- **錯誤與經驗資料庫**：[.agent/knowledge_base/lessons_learned.md](file:///d:/GitHub/LLM-Agent-System/.agent/knowledge_base/lessons_learned.md)
- **任務規格清單**：[.agent/agent_tasks.md](file:///d:/GitHub/LLM-Agent-System/.agent/agent_tasks.md)
- **有向圖引擎與記憶體**：
  - `agent_workspace/core/engine.py`
  - `agent_workspace/core/workflow_engine.py`
  - `agent_workspace/core/discussion_room.py`
  - `agent_workspace/memory_backends.py`
- **視覺拓撲元件**：
  - `viewer/src/components/edges/`
  - `viewer/src/components/TopologyView.tsx`
  - `viewer/src/components/TaskFlowView.tsx`
  - `viewer/src/index.css`

---

## 🛠️ 具體執行步驟與驗收標準

### 1️⃣ Task 12-01: Multi-Dimensional Categorized Mind-Map Edges (多項心智圖拓撲連線)
* **後端資料結構擴展**：
  - 修改 `workspace.json` 及核心有向圖解析器，使連線 (Edges) 除了支援 `source` 和 `target`，亦支援 `category` 欄位（列舉值：`dependency`, `data_flow`, `feedback_loop`, `parallel_trigger`）。
* **前端 React Flow 渲染優化**：
  - 在 `viewer/src/components/edges/` 中客製多種樣式的連線元件：
    - `dependency`：實線藍色/青色，代表常規依賴。
    - `data_flow`：實線流動粒子（利用 SVG `stroke-dasharray` 加上 `animate-flow-particles` 粒子動畫），代表資料管線傳輸。
    - `feedback_loop`：虛線橘黃色/紅色脈衝，代表審查重試環路。
    - `parallel_trigger`：金色光點流，代表多智慧體並行觸發。
  - 圖表佈局支援像心智圖一樣向外分支，按類別 (backend, mobile, quality, testing) 在不同維度上延展開來，告別單一流程圖既視感。

### 2️⃣ Task 12-02: Structured Log Compaction & Milestone Integration (日誌里程碑壓縮與整合)
* **日誌壓縮引擎實作**：
  - 撰寫 `agent_workspace/core/log_compactor.py`（或直接整合至 `core/engine.py`），當檢測到 Phase/Milestone 完成（所有節點 status 轉為 completed）時，自動執行壓縮流程。
  - 將大量重複、瑣碎的執行細節與交易日誌，以 LLM 進行摘要，生成不低於 **75% 壓縮率** 的高階語意里程碑 summary (Milestone Token)。
  - 將詳細的歷史 Transaction 寫入 `.agent/memory/archive/` 進行冷歸檔，並將活動記憶體 (Active JSON) 的歷史欄位替換為該 Milestone Summary，確保 LLM 的 context window 始終極度乾淨。

### 3️⃣ Task 12-03: Self-Learning & Self-Correction Database (自我學習與糾錯資料庫)
* **經驗資料庫建立**：
  - 建立並維護 [.agent/knowledge_base/lessons_learned.md](file:///d:/GitHub/LLM-Agent-System/.agent/knowledge_base/lessons_learned.md)。
* **自動分析與注入**：
  - 在執行 CLI 驗證或 `pytest` 出錯時，架構內置一個攔截器，自動格式化記錄錯誤：`[Lesson ID -> Mistake -> Root Cause -> Resolution -> Best Practice Policy]`。
  - 修改 `core/prompt_composer.py`。在每次合成系統 Prompt 時，自動載入 `lessons_learned.md` 中的最佳實踐規則，使 Agent Swarm 在下一次規劃或寫代碼時自動避開踩過的坑，實現系統自我學習與自動進化。

### 4️⃣ Task 12-04: Parallel Multi-Agent Team Execution (平行多智慧體協同執行)
* **異步併發派發實作**：
  - 擴展 `core/workflow_engine.py`，使處於 pending 且滿足前置依賴的多個任務節點能夠**非同步平行派發**。
  - 結合 Python `asyncio.gather` 或多執行緒機制，同時啟動多個獨立的子智慧體進程（例如：平行讓 A 智慧體處理多國語言翻譯，B 智慧體優化 Tauri 打包配置，C 智慧體打磨 CSS 樣式），提升 Swarms 的執行效率。

### 5️⃣ Task 12-05: Corporate Swarm - Company Org-Chart Roles (智慧體公司化小團隊)
* **角色與 Profile 定義**：
  - 在 `.agent/` 中正式建立 `CEO` (決策協調者)、`CTO` (架構規劃者)、`Dev` (代碼編程者)、`QA` (代碼審計與測試者)、`CFO` (Token 審計與成本控制者) 的 Profile。
* **交接與驗證閘道 (Gateways)**：
  - 實作智慧體之間的鏈式交接合約。Dev 智慧體完成代碼後，必須通過 `QA` 智慧體執行靜態語法檢查與 `pytest` 測試；測試 100% 通過後方可將狀態寫回 `completed`，否則退回 `feedback_loop` 重新優化，完成完美的公司化運作閉環。

---

## 🚦 自動化與合約維護
1. 實現所有功能後，必須執行全量 pytest 單元測試套件，確保 100% 通過。
2. 更新 [agent_tasks.md](file:///d:/GitHub/LLM-Agent-System/.agent/agent_tasks.md) 中的 `PHASE 12` 勾選狀態。
3. 使用 `git add .` 暫存所有變更，並提交 semantic commit。
