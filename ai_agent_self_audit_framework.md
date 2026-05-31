# 🌌 通用型 AI 開發智慧體防錯與自我稽核指南 (Generic AI Coding Agent Self-Audit Framework)

> **適用對象**：所有參與軟體開發、重構、測試與架構設計的 AI 智慧體（Coding Agents）。
> **核心目的**：建立跨專案的通用工程邊界，防範智慧體在「通過單元測試」後產生過度樂觀的認知盲點，進而遺漏版本控制、自學知識沉澱及規格書同步等必要交付步驟。

---

## ⚠️ 1. 跨專案智慧體常見之「最後一哩路疏漏」 (The Universal Agent DoD Gap)

在許多軟體開發專案中，AI Agent 往往展現出優異的代碼編寫能力，甚至能自主運行複雜的測試套件並獲得綠燈。然而，在「宣告任務完成」的最後階段，智慧體常因以下三個共性原因導致專案整合不完整：

1. **版本控制「只看不做」 (Git Staging & Commit Neglect)**：
   - **現象**：Agent 修改或新增了多個檔案，並使用 `git status` 或 `git diff` 進行確認，但未實施 `git add` 與 `git commit`。
   - **後果**：工作變更未被安全固化，一旦環境發生重置、網絡中斷或容器重啟，未暫存的代碼將全部遺失。

2. **自學經驗未能跨執行緒傳承 (Lessons Learned Siloed)**：
   - **現象**：在解決複雜的環境變數衝突、路徑遍歷或模擬死鎖（Mock Deadlocks）等 Trick Bug 後，僅在對話中回覆人類，卻沒有將該經驗寫入專案的動態經驗數據庫（Lessons Learned Registry）。
   - **後果**：當新的一輪對話啟動（Cold Thread），或另一個 Agent 被喚醒時，會因為沒有共享此脈絡而重複踩坑。

3. **系統指標與說明文件失修 (Documentation & Telemetry Decay)**：
   - **現象**：重構了核心 API 或調整了 CLI 參數，但沒有同步更新根目錄的 `README.md`、專案規格書（Developer Specifications） or 對應的測試數量徽章（Badges）。
   - **後果**：導致人類開發者或其他並行的智慧體讀取到過時的系統狀態，破壞了「單一事實來源（Single Source of Truth, SSoT）」原則。

---

## 🚦 2. 通用型智慧體開發五大黃金準則 (The 5-Step Agent DoD Protocol)

為確保交付代碼的完整性，所有 Coding Agents 在宣告任何任務完成前，必須強制執行以下五大步驟檢核：

### ☐ [Step 1] 代碼防禦性與解耦檢查 (Clean Code & Defensiveness)
* **防禦性設計**：所有非同步操作、外部 API 調用、網絡請求及磁碟 I/O 是否皆已封裝於適當的 `try-except` 或錯誤攔截機制中，避免單點崩潰？
* **代碼精簡**：是否已主動移除未使用的引入（Imports）、暫時性的 debug 代碼及無效註解，確保代碼無膨脹（Bloat）？

### ☐ [Step 2] 動態知識庫與自學更新 (Lessons Learned Capture)
* **經驗沉澱**：在本次開發中，是否解決了任何具備參考價值的錯誤、死鎖或環境衝突？
* **同步機制**：若有，必須主動定位專案內的「自學紀錄檔」（如 `lessons_learned.md` 或 `lessons/` 目錄），以結構化格式（錯誤現象、根本原因、防範政策）補登此 Lesson。

### ☐ [Step 3] 任務清單與進度同步 (Task Registry Alignment)
* **看板更新**：是否已在專案的看板檔案（如 `task.md`、`TODO.md` 或 issue trackers）中，將您負責的 subtasks 標記為完成？
* **數據同步**：專案總體進度百分比與狀態表格是否已更新至最新？

### ☐ [Step 4] 規格書與指示牌同步 (Specs & Readme Sync)
* **接口對齊**：本次新增或修改的 API 端點、CLI 命令參數、數據庫 Schema，是否已同步更新至專案的規格說明書中？
* **徽章與看板**：根目錄的 `README.md` 中，如測試通過數量徽章（Build Status Badges）、版本號等指示指標，是否已同步為最新數據？

### ☐ [Step 5] 自動化校驗與 Git Commit 提交 (Verify, Stage & Commit)
* **最終校驗**：是否已在當前環境中完整跑過一次專案的測試套件（如 `pytest`, `npm test` 等）並確保 100% 綠燈？
* **安全固化**：執行 `git add .`（或指定的暫存命令）將所有變更暫存。
* **語意提交**：使用符合規範之語意化 Commit 訊息（如 `feat(...)`, `fix(...)`）執行 `git commit`，正式將成果寫入歷史紀錄。
