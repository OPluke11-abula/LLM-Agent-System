# LAS (FindAi Studio) 任務與架構進度交接文件 (LAS_stage.md)

**版本標記**：Phase 105 - 外部先進生態融合 (A~D 模組升級)  
**協議基準**：Universal Coding Agent Development Protocol v3.8.0 (`.agent/state.md`)  
**交接時間**：2026-10-01  
**治理負責**：Luke (PO / Domain Owner)  
**文件定位**：新 Agent Thread 啟動執行 A~D 模組的唯一權威交接單 (Single Source of Truth)

---

## 1. 任務背景與當前狀態 (Current Frontier)

在 Phase 104 完成系統零技術債發行驗證後，我們深入研析了社群五大前沿開源專案：
1. `lidge-jun/opencodex`（通用 Provider 轉譯與多帳號配額池）
2. `RPG-478/codex-chatgpt-bridge`（Executor vs. Advisor 委派模式與精簡封包）
3. `a252937166/codex-chatgpt-web-bridge`（Python Responses API 與會話內工具協議自癒輪次）
4. `miuuyy/codex-chatgpt-web`（桌面級多檔位調度器與 Zero Risk 合規模式）
5. `louis-cfm/coucou`（Tauri 2 邊緣伴侶與非侵入式 HITL 一鍵審批）

PO (Luke) 已正式核准實施計畫，本交接單旨在指引新 Agent Thread 依照 TDD 流程依序落實 **Task A ➔ Task B ➔ Task C ➔ Task D**。

---

## 2. 四大模組開發規格與切片 (Approved Tasks A ~ D)

```
+-----------------------------------------------------------------------------------------+
| [Task A] Presentation: Tauri 2 邊緣懸浮伴侶 (Ambient Companion) & 1-Click HITL (coucou)     |
+-----------------------------------------------------------------------------------------+
| [Task D] Protocol: OpenAI Responses API Gateway (POST /v1/responses) + 配額池 (opencodex)  |
+-----------------------------------------------------------------------------------------+
| [Task C] Cognitive: Executor vs. Advisor 結構化委派封包 (Delegation Packet) (codex-bridge)     |
+-----------------------------------------------------------------------------------------+
| [Task B] Runtime: In-Session 工具協議自癒修復輪次 (Protocol Repair Loop) (web-bridge)          |
+-----------------------------------------------------------------------------------------+
```

---

### ### Task A: Tauri 2 邊緣懸浮伴侶與輕量 HITL 審批 (Ambient Companion)
* **借鑑來源**：`louis-cfm/coucou`
* **所屬層級**：Layer 1 (Presentation & Desktop Control Plane)
* **職責負責**：Joe (`UI_UX_AGENT`)
* **目標**：在 Windows 螢幕頂部/邊緣提供常駐置頂微型伴侶，支援即時狀態微動畫（讀取、思考、測試綠燈跳躍）、非侵入式一鍵審批（Allow / Deny），並支援拖曳檔案直接注入 Context。
* **目標檔案**：
  * 修改：`viewer/src-tauri/tauri.conf.json`（新增 `companion-window` 配置：無邊框、透明背景、置頂、預設隱藏/懸浮觸發）
  * 創建：`viewer/src/components/companion/AmbientCompanion.tsx`（微型 UI 元件）
  * 創建：`viewer/src/hooks/useAmbientCompanion.ts`（狀態訂閱與審批快速呼叫 Hook）
  * 測試：`viewer/src/components/companion/__tests__/AmbientCompanion.test.tsx`
* **介面規格**：
  * 監聽 `/v1/pipeline/ws` 與 `/v1/chat/ws` 派發之 `approval_required` 事件。
  * 觸發審批時彈出迷你卡片，呼叫 `POST /v1/pipeline/tasks/{task_id}/approve`。
* **邊界條件**：
  * 多螢幕 DPI 縮放與位置鎖定；審批 Token 失效或超時的視覺回退處理。

---

### ### Task B: In-Session 工具協議自癒修復輪次 (Protocol Repair Loop)
* **借鑑來源**：`a252937166/codex-chatgpt-web-bridge`
* **所屬層級**：Layer 4 (Cognitive Router) & Layer 6 (Tool Sandbox)
* **職責負責**：Ethan (`BACKEND_INFRA_AGENT`) / Eason (`APPLICATION_FLOW_AGENT`)
* **目標**：當大模型或外部 Web 模型輸出不合規的 Tool Calling 參數（JSON 解析失敗、缺少 Required 欄位、型別不匹配）時，在同一會話內發動局部修復輪次（最多 2 次），避免任務中斷失敗。
* **目標檔案**：
  * 創建：`agent_workspace/core/protocol_repair.py`（定義 `ProtocolRepairManager`、`RepairResult`、Schema 驗證與修復提示生成器）
  * 修改：`agent_workspace/core/agent_executor.py`（在 `execute_tool` 呼叫前嵌入自癒修復攔截）
  * 修改：`agent_workspace/core/workflow_engine.py`（強化參數驗證錯誤時的局部修復流）
  * 測試：`agent_workspace/tests/test_protocol_repair.py`
* **介面規格**：
  * `ProtocolRepairManager.validate_and_repair(tool_name: str, raw_arguments: Any, schema: dict, session_context: dict) -> tuple[bool, dict, str]`
* **邊界條件**：
  * 遞歸死循環防護（嚴格 `max_turns=2`）；修復 Prompt 防止惡意指令注入逃逸。

---

### ### Task C: Executor vs. Advisor 結構化委派封包 (Delegation Packet)
* **借鑑來源**：`RPG-478/codex-chatgpt-bridge` & `miuuyy/codex-chatgpt-web`
* **所屬層級**：Layer 3 (Swarm Governance) & Layer 4 (Cognitive Engine)
* **職責負責**：Luke (`DOMAIN_LOGIC_AGENT`) / Ethan (`BACKEND_INFRA_AGENT`)
* **目標**：將本地執行與高難度思考解耦。本地由廉價/快速模型（Gemini Flash/Ollama）執行 Shell/檔案變更；高難度架構規劃、辯論與審查則封裝為脫敏精簡的 `DelegationPacket`（< 2000 tokens），透過 MCP 工具調用外部顧問（Advisor），大幅節省 API 成本。
* **目標檔案**：
  * 創建：`agent_workspace/core/delegation_packet.py`（定義 `DelegationPacket`、`AdvisorMode`、`SanitizedContextExtractor`、`AdvisorResponse`）
  * 修改：`agent_workspace/core/reasoning_router.py`（擴充 `ModelTier.ADVISOR_DELEGATION` 路由策略）
  * 創建：`.agent/skills/delegate_to_advisor/` 技能合約與 Python 工具實現
  * 測試：`agent_workspace/tests/test_delegation_packet.py`
* **介面規格**：
  * 整合 `context_budget_preflight.py` 進行機密 Token/金鑰脫敏。
  * 支援手動複製貼上確認之「Zero Risk 模式」與自動化 MCP 委派模式。
* **邊界條件**：
  * 外部 Advisor 響應超時或結構不合規時，優雅降級回內部預設模型。

---

### ### Task D: Responses API 閘道與多帳號配額感知路由 (Quota-Aware Routing)
* **借鑑來源**：`lidge-jun/opencodex` & `a252937166/codex-chatgpt-web-bridge`
* **所屬層級**：Layer 2 (Protocol Gateway) & Layer 4 (Cognitive Router)
* **職責負責**：Ethan (`BACKEND_INFRA_AGENT`)
* **目標**：
  1. 在 FastAPI Gateway 暴露相容於 OpenAI 的 `POST /v1/responses` SSE 串流端點，使外部開發工具（Cursor, Codex CLI, Claude Code）可直接將 LAS 當作具備 Swarm 辯論與沙箱防護的智能後端。
  2. 強化 `AccountManager`，新增配額感知（Quota-Aware）、429 指數退避冷卻與多帳號平滑切換。
* **目標檔案**：
  * 創建：`agent_workspace/routes/responses.py`（實作 Responses SSE 事件流：`response.created`, `output_item.added`, `function_call`, `response.completed`）
  * 修改：`agent_workspace/routes/chat.py` / `agent_workspace/api.py`（掛載 Responses 路由）
  * 修改：`agent_workspace/core/account_manager.py`（新增 `QuotaAwareRouter`、RPM/TPM 即時監控計時器、429 冷卻維護池）
  * 測試：`agent_workspace/tests/test_responses_api.py`、`agent_workspace/tests/test_quota_router.py`
* **邊界條件**：
  * 用戶端斷線 (Client Disconnect) 的背景資源回收；全帳號配額耗盡時的型別化錯誤模型 (`QuotaExhaustedError`)。

---

## 3. 核心作業規範與治理約束 (Invariants & Rules)

在新 Thread 中，執行 Agent **必須嚴格遵守以下規範**：

1. **0.1 Anti-Summary Invariant (調研先行)**：
   * 嚴格禁止僅憑本交接文件的文字推論，每次改動前必須實際 `view_file` 查閱真實代碼與精確行號。
2. **0.2 Stop-and-Wait Architecture Gate (架構審批閘門)**：
   * 進入具體任務實作前，明確提出 Structural Diff、測試清單，等待 Human PO 確認後方可編輯檔案。
3. **一人一功能責任切片 (`.agent/ownership.md`)**：
   * UI 元件變更限於 `viewer/`，嚴禁在 UI 中寫入原生 SQL 或直接修改後端。
   * 後端 Runtime 變更限於 `agent_workspace/core/`、`agent_workspace/routes/`。
4. **七大反腐敗原則 (Anti-Corruption Principles)**：
   * 零死代碼 (Zero Dead Code)、極致職責分離、消除競態條件、嚴禁吞掉異常（必須使用 Typed Failure）、Contract-First、零魔術數字。
5. **每次工作結束自我檢核 (`AGENT.md`)**：
   * 冗餘清理、架構合約檢查、更新 `.agent/` 與 `README.md`（中英文獨立）、測試 100% 通過（`verify.cmd` / `pytest`）。

---

## 4. 推薦執行順序

建議新 Thread 依照以下順序推進：
1. **第一波**：Task B (工具協議修復輪次) ── 純 Python 核心邏輯，打底 Tool Calling 穩定度。
2. **第二波**：Task C (Executor vs. Advisor 委派模式) ── 依託 Task B 的自癒能力，實現結構化思考委派。
3. **第三波**：Task D (Responses API 閘道 & 配額路由) ── 開放對外協議與多帳號負載均衡。
4. **第四波**：Task A (Tauri 2 邊緣伴侶與 HITL 審批) ── 串聯上述後端能力至桌面輕量呈現。
