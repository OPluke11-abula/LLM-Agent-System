# PAP Agent Task Queue
>
> Protocol: portable-agent-protocol v0.1.0  
> Format: PAP Task Contract v1  
> Status legend: `[ ]` pending · `[~]` in-progress · `[x]` done · `[!]` blocked

---

## PHASE 0 — Foundation / 基礎建設

### 0-01 Schema 正式化

```
priority : CRITICAL
effort   : M
depends  : —
```

- [x] 建立 `spec/` 目錄
- [x] 撰寫 `spec/agent-schema.json`，定義 `.agent/agent.md` YAML front matter 的完整 JSON Schema
- [x] 撰寫 `spec/skill-contract.schema.json`，定義 capability contract 的欄位規格
- [x] 撰寫 `spec/memory.schema.json`，定義 episodic / semantic memory 的資料格式
- [x] 撰寫 `spec/workflow.schema.json`，定義 workflow 步驟結構
- [x] 在 `README.md` 加入 `spec/` 的說明段落
- [x] 驗證現有 `.agent/` 下的所有 .md 都符合新 schema

---

### 0-02 Memory 格式落地

```
priority : CRITICAL
effort   : M
depends  : 0-01
```

- [x] 建立 `.agent/memory/episodic/` 目錄，加入 `README.md` 說明格式
- [x] 建立 `.agent/memory/semantic/` 目錄，加入 `README.md`
- [x] 建立 `.agent/memory/handoff/` 目錄，用於跨 agent 交接
- [x] 撰寫 `.agent/memory/schema.json`，定義所有欄位與型別
- [x] 新增範例檔 `examples/memory_episodic_sample.jsonl`
- [x] 新增範例檔 `examples/memory_semantic_sample.json`
- [x] 新增範例檔 `examples/memory_handoff_sample.json`
- [x] 在 `agent_runtime/` 實作 `MemoryBackend` 類別，支援 read / write / query
- [x] 補充對應測試 `tests/test_memory_backend.py`

---

### 0-03 Skill Contract 標準化

```
priority : HIGH
effort   : S
depends  : 0-01
```

- [x] 為現有每個 tool 補齊 `.agent/skills/<tool>.md`（若缺漏）
- [x] 確認每個 skill contract 包含欄位：`id`, `description`, `inputs`, `outputs`, `safety_notes`, `version`
- [x] 移除任何 skill contract 中對特定 AI 廠商的參照
- [x] 在 `.agent/skills.md` registry 加入 `schema_version` 欄位
- [x] 補充測試 `tests/test_skill_contracts.py`，驗證每個 skill 都符合 schema

---

### 0-04 Router 強化

```
priority : HIGH
effort   : M
depends  : 0-03
```

- [x] `agent_runtime/router.py` 加入 schema 驗證：呼叫前檢查 inputs 是否符合 skill contract
- [x] 加入 `Router.list_skills()` 方法，回傳結構化的 skill 清單
- [x] 加入 `Router.describe_skill(skill_id)` 方法，回傳單一 skill 的 contract 內容
- [x] 加入 `Router.validate_call(skill_id, params)` 方法，呼叫前乾跑驗證
- [x] 加入 routing 失敗時的明確錯誤訊息（包含 skill_id、缺少欄位名稱）
- [x] 補充測試 `tests/test_router_validation.py`

---

### 0-05 CLI 完整化

```
priority : MEDIUM
effort   : S
depends  : 0-04
```

- [ ] `cli.py` 加入 `--list-skills` 指令，印出所有可用 skill 清單
- [ ] `cli.py` 加入 `--describe-skill <id>` 指令，印出 skill contract 詳情
- [ ] `cli.py` 加入 `--validate` 指令，檢查整個 `.agent/` 結構是否合法
- [ ] `cli.py` 加入 `--memory-read <key>` 指令
- [ ] `cli.py` 加入 `--memory-write <key> <value>` 指令
- [ ] `cli.py` 加入 `--run-workflow <id>` 指令
- [ ] 更新 `USAGE.md` 反映新 CLI 選項

---

### 0-06 Open Source Skills 引入與匿名化

```
priority : HIGH
effort   : M
depends  : 0-03
```

- [x] 從 `https://github.com/anthropics/skills` 拷貝有用的開源技能（如文件處理、網頁搜尋等）
- [x] 將這些技能合約手動存放至 `.agent/skills/`
- [x] 移除這些合約與程式碼中的 "Anthropic" 相關字眼與商標
- [x] 修改內部邏輯，使其完全相容於我們純本地端的 Python 執行器 (Router)
- [x] 確認這些被「挪用」的技能不再發送任何外部 API 請求，或已將其轉換為通用的 LLM 呼叫

---

## PHASE 1 — Protocol Completeness / 協定完整性

### 1-01 Workflow 引擎實作

```
priority : HIGH
effort   : L
depends  : 0-04
```

- [ ] 設計 workflow 狀態機格式（states: pending / running / success / failed / skipped）
- [ ] 在 `agent_runtime/` 新增 `workflow_engine.py`
- [ ] 實作 `WorkflowEngine.load(workflow_id)` —— 從 `.agent/workflows/<id>.md` 載入定義
- [ ] 實作 `WorkflowEngine.run(workflow_id, payload)` —— 依序執行步驟
- [ ] 實作 `WorkflowEngine.resume(workflow_id, step_id)` —— 從中斷點繼續
- [ ] 實作失敗步驟自動寫入 memory（不可靜默失敗）
- [ ] 補充測試 `tests/test_workflow_engine.py`（含失敗路徑測試）
- [ ] 新增範例 `examples/workflow_run_sample.py`

---

### 1-02 Knowledge Base 索引

```
priority : MEDIUM
effort   : M
depends  : 0-01
```

- [ ] 建立 `.agent/knowledge_base/index.json`，記錄所有知識條目的 id、標題、路徑、標籤
- [ ] 定義知識條目的 front matter 格式（`id`, `title`, `tags`, `created`, `updated`）
- [ ] 為現有 `knowledge_base/` 下的所有文件補充 front matter
- [ ] 在 `agent_runtime/` 新增 `knowledge.py`，實作 `KnowledgeBase.query(keyword)` 方法
- [ ] 實作 `KnowledgeBase.get(id)` 方法，回傳單一知識條目
- [ ] 補充測試 `tests/test_knowledge_base.py`
- [ ] 知識庫唯讀保護：任何寫入操作需走 T-04 Protocol Evolution 流程

---

### 1-03 Prompt Registry 可執行化

```
priority : MEDIUM
effort   : M
depends  : 0-01
```

- [ ] 定義 prompt snippet 的結構格式（`id`, `template`, `variables`, `usage`, `version`）
- [ ] 將 `.agent/prompts/` 下的文件轉換為符合新格式的 prompt contract
- [ ] 在 `agent_runtime/` 新增 `prompt_composer.py`，實作 `PromptComposer.build(id, vars)` 方法
- [ ] 加入 prompt injection 安全驗證（拒絕未經驗證的外部字串進入 system prompt）
- [ ] 補充測試 `tests/test_prompt_composer.py`（含 injection 防護測試）
- [ ] 新增範例 `examples/prompt_composition_sample.py`

---

### 1-04 Cross-Agent Handoff 機制

```
priority : HIGH
effort   : M
depends  : 0-02, 1-01
```

- [ ] 設計 handoff packet 格式（task_state, pending_steps, context_summary, memory_snapshot）
- [ ] 實作 `AgentEngine.export_handoff()` —— 產生 handoff packet 並寫入 `.agent/memory/handoff/`
- [ ] 實作 `AgentEngine.import_handoff(handoff_id)` —— 讀取並還原 handoff 狀態
- [ ] 加入 handoff packet 的完整性驗證（checksum 或 hash）
- [ ] 補充測試 `tests/test_handoff.py`
- [ ] 新增範例 `examples/handoff_export_import.py`
- [ ] 在 `USAGE.md` 補充跨 agent 交接的使用說明

---

### 1-05 Protocol Version Management

```
priority : MEDIUM
effort   : S
depends  : 0-01
```

- [ ] 在 `spec/` 建立 `CHANGELOG.md`，從 v0.1.0 開始記錄
- [ ] 定義版本號規則（major.minor.patch，破壞性變更需 major 遞增）
- [ ] 在 `agent_runtime/engine.py` 加入版本相容性檢查（runtime version vs. manifest version）
- [ ] 版本不相容時輸出明確警告，不直接報錯崩潰
- [ ] 建立 `spec/migration/` 目錄，放置版本遷移指南
- [ ] 補充測試 `tests/test_version_compat.py`

---

## PHASE 2 — Developer Experience / 開發者體驗

### 2-01 Init 指令

```
priority : HIGH
effort   : M
depends  : 0-05, 1-05
```

- [ ] `cli.py` 加入 `init` 子指令：在任意專案目錄建立完整的 `.agent/` 骨架
- [ ] init 流程詢問：project name、agent name、啟用的 skill 清單
- [ ] init 自動產生：`agent.md`、`skills.md`、`prompts.md`、`memory.md`、`workflows.md`、`knowledge_base/`
- [ ] init 產生的所有檔案都帶有正確的 YAML front matter 與 schema 版本
- [ ] 加入 `--dry-run` 選項，只顯示會產生的檔案，不實際寫入
- [ ] 補充測試 `tests/test_cli_init.py`
- [ ] 更新 `USAGE.md` 和 `README.md`

---

### 2-02 Lint 指令

```
priority : MEDIUM
effort   : M
depends  : 0-01, 2-01
```

- [ ] `cli.py` 加入 `lint` 子指令：檢查 `.agent/` 所有檔案的格式合規性
- [ ] 檢查項目：schema 欄位完整性、版本號格式、skill contract 與 registry 一致性、workflow 步驟引用合法性
- [ ] 輸出格式：每個問題顯示 severity（error / warning / info）、檔案路徑、行號（若適用）、修復建議
- [ ] 加入 `--fix` 選項，自動修復可自動化處理的問題
- [ ] 補充測試 `tests/test_cli_lint.py`

---

### 2-03 多語言 Runtime 規格文件

```
priority : MEDIUM
effort   : L
depends  : 0-01
```

- [ ] 在 `spec/` 撰寫 `runtime-interface.md`：定義任何語言的 runtime 必須實作的介面
- [ ] 必要介面清單：`load_manifest()`, `list_skills()`, `call_skill()`, `read_memory()`, `write_memory()`, `run_workflow()`
- [ ] 為每個介面定義輸入/輸出的 JSON 格式
- [ ] 撰寫 JavaScript/TypeScript reference implementation 的 stub（`spec/stubs/ts/`）
- [ ] 撰寫 Go reference stub（`spec/stubs/go/`）
- [ ] 確保 Python runtime 完全符合此規格文件

---

### 2-04 範例庫擴充

```
priority : LOW
effort   : M
depends  : 1-01, 1-02, 1-03
```

- [ ] `examples/` 新增：`00_quickstart.py` —— 5 分鐘上手範例
- [ ] `examples/` 新增：`01_skill_call.py` —— 完整的 skill 呼叫流程
- [ ] `examples/` 新增：`02_memory_session.py` —— session 記憶讀寫
- [ ] `examples/` 新增：`03_workflow_run.py` —— 執行一個多步驟 workflow
- [ ] `examples/` 新增：`04_knowledge_query.py` —— 查詢知識庫
- [ ] `examples/` 新增：`05_multi_agent.py` —— 模擬兩個 agent 交接任務
- [ ] `examples/` 新增：`06_prompt_compose.py` —— 組裝 prompt 並注入變數
- [ ] 每個範例都要能獨立執行，有完整的 inline 說明註解

---

### 2-05 文件網站結構

```
priority : LOW
effort   : L
depends  : 2-03, 2-04
```

- [ ] 建立 `docs/` 目錄
- [ ] `docs/getting-started.md` —— 安裝、init、第一個 skill call
- [ ] `docs/protocol-spec.md` —— 完整協定規格（從 spec/ 整合）
- [ ] `docs/skill-authoring.md` —— 如何撰寫 capability contract
- [ ] `docs/memory-guide.md` —— memory 策略與最佳實踐
- [ ] `docs/workflow-guide.md` —— workflow 設計模式
- [ ] `docs/multi-agent.md` —— 多 agent 協作與 handoff 指南
- [ ] `docs/migration/` —— 各版本遷移指南

---

## PHASE 3 — Quality & Security / 品質與安全

### 3-01 測試覆蓋率提升

```
priority : HIGH
effort   : M
depends  : PHASE 0, PHASE 1
```

- [ ] 設定測試覆蓋率目標：核心 runtime 80% 以上
- [ ] 補充 `tests/test_engine.py`：涵蓋邊界條件（缺少欄位、格式錯誤、版本不符）
- [ ] 補充 `tests/test_router.py`：涵蓋不存在的 skill、參數型別錯誤
- [ ] 補充 `tests/test_memory.py`：涵蓋 scope 隔離、大量資料、concurrent write
- [ ] 加入整合測試 `tests/integration/`：模擬完整的 session 流程
- [ ] 在 `pyproject.toml` 加入覆蓋率設定（pytest-cov）
- [ ] CI 設定：覆蓋率低於門檻時 fail

---

### 3-02 安全審查

```
priority : HIGH
effort   : M
depends  : 1-03
```

- [ ] 審查所有可接受外部輸入的路徑，加入輸入驗證
- [ ] Prompt injection 防護：確認 `prompt_composer.py` 的 variable 注入有 escaping
- [ ] Memory key 注入防護：驗證 key 格式，拒絕含有路徑分隔符號的 key
- [ ] Skill call 權限模型：定義哪些 skill 需要明確的使用者授權才能執行
- [ ] 撰寫 `spec/security.md`，記錄威脅模型與防護措施
- [ ] 補充 `tests/test_security.py`，包含 injection 攻擊的測試案例

---

### 3-03 效能基準測試

```
priority : LOW
effort   : S
depends  : 3-01
```

- [ ] 建立 `benchmarks/` 目錄
- [ ] 基準測試：manifest 載入時間（目標 < 50ms）
- [ ] 基準測試：skill registry 查詢時間（目標 < 10ms）
- [ ] 基準測試：memory 讀寫時間（目標 < 100ms for 1000 entries）
- [ ] 基準測試：workflow 步驟 routing 時間
- [ ] 建立效能回歸測試，合併前自動執行

---

### 3-04 Dependency 最小化

```
priority : MEDIUM
effort   : S
depends  : PHASE 1
```

- [ ] 審查 `pyproject.toml` 的所有依賴，移除非必要套件
- [ ] 區分 runtime 必要依賴 vs. dev 依賴
- [ ] 確認 core runtime（無 dev 依賴）可在純 Python 標準函式庫下運作
- [ ] 若需要第三方套件，在 `spec/` 中說明理由

---

## PHASE 4 — Ecosystem / 生態系

### 4-01 GitHub Actions CI

```
priority : HIGH
effort   : S
depends  : 3-01
```

- [ ] 建立 `.github/workflows/ci.yml`
- [ ] CI 流程：lint → compile check → pytest → coverage report
- [ ] 測試矩陣：Python 3.10 / 3.11 / 3.12，Ubuntu / macOS / Windows
- [ ] 加入 badge 至 README（CI status、coverage、license）
- [ ] PR 自動執行 `cli.py --validate` 檢查 `.agent/` 結構

---

### 4-02 Package 發布準備

```
priority : MEDIUM
effort   : M
depends  : 2-05, 4-01
```

- [ ] 確認 `pyproject.toml` 的 metadata 完整（name, version, description, author, license, classifiers）
- [ ] 建立 `CHANGELOG.md`（根目錄，面向使用者）
- [ ] 建立 `CONTRIBUTING.md`，說明如何貢獻 skill contract 或 runtime 實作
- [ ] 測試 `pip install -e .` 在乾淨環境的安裝流程
- [ ] 準備 PyPI 發布（若決定公開發布）
- [ ] 建立 GitHub Release 流程（tag-based）

---

### 4-03 PAP Registry（選用）

```
priority : LOW
effort   : XL
depends  : 4-02
```

- [ ] 設計 public skill registry 的 API 格式
- [ ] 建立 `registry/` 目錄，放置社群貢獻的 skill contract
- [ ] 定義 skill 發布與審查流程
- [ ] CLI 加入 `--install-skill <id>` 指令，從 registry 安裝 skill
- [ ] CLI 加入 `--publish-skill <path>` 指令，發布 skill 至 registry

---

## PHASE 5 — Self-Evolution / 自我演進

### 5-01 Agent Self-Audit

```
priority : MEDIUM
effort   : M
depends  : 1-02, 3-01
```

- [ ] 定義 self-audit workflow：agent 定期檢查自身 `.agent/` 狀態
- [ ] 檢查項目：skill 版本是否過時、memory 是否達到清理閾值、workflow 是否有長期 pending 任務
- [ ] 自動產生 audit report 寫入 `.agent/memory/semantic/audit_log.json`
- [ ] 在發現問題時產生 task recommendation（建議人類執行哪個 task）

---

### 5-02 Knowledge Base 自動更新

```
priority : LOW
effort   : L
depends  : 1-02, 5-01
```

- [ ] 定義 knowledge extraction 規則：什麼樣的 episodic memory 值得升級為 semantic knowledge
- [ ] 實作 `KnowledgeBase.promote(episodic_entry_id)` —— 將 episodic 轉為 semantic
- [ ] 加入人工確認步驟：自動升級的條目需標記 `status: draft`，等待確認後才變 `stable`
- [ ] 補充測試與範例

---

### 5-03 Skill 自動生成草稿

```
priority : LOW
effort   : L
depends  : 0-03, 5-01
```

- [ ] 當 agent 呼叫了一個不在 registry 的 tool 時，自動產生 capability contract 草稿
- [ ] 草稿放入 `.agent/skills/drafts/`，標記 `status: draft`
- [ ] 草稿包含：根據呼叫行為推斷的 inputs / outputs / description
- [ ] 需人工審查確認後，才能移至正式 `.agent/skills/`

---

## PHASE 6 — Account & Token Management / 帳號與 Token 管理

### 6-01 Account Management Core / 多帳號管理核心

```
priority : HIGH
effort   : M
depends  : 0-02
```

- [x] 實作 `agent_workspace/core/account_manager.py`，支援讀寫 `accounts.json`
- [x] 支援新增、刪除、查詢帳號，並支援每個帳號之 Model、Provider、API Key、Token 額度設定
- [x] 實作動態切換 active_account 核心邏輯
- [x] 撰寫對應之單元測試 `tests/test_account_manager.py`

---

### 6-02 Router & Provider Integration / 路由與 Provider 整合

```
priority : HIGH
effort   : M
depends  : 6-01
```

- [x] 修改 `agent_workspace/core/providers.py`，支援傳入 dynamic `api_key` 與 `base_url`
- [x] 修改 `agent_workspace/core/router.py`，於每一次呼叫 LLM 前自 active account 讀取設定
- [x] 在呼叫成功後，將 Prompt 與 Completion Token 的用量即時累加並寫回 `accounts.json`
- [x] 實作額度檢查邏輯，若 token 用盡則拋出異常或自動 fallback 到下一個可用帳號
- [x] 撰寫測試驗證 Router token 即時扣款與阻斷行為

---

### 6-03 API Endpoints & DX / API 端點與開發體驗

```
priority : HIGH
effort   : S
depends  : 6-02
```

- [x] 在 `agent_workspace/api.py` 中新增 `GET /v1/accounts` 查詢所有帳號與剩餘 tokens 餘額
- [x] 新增 `POST /v1/accounts` 用於新增或更新帳號與 API 金鑰
- [x] 新增 `POST /v1/accounts/active` 動態切換目前作用的帳號，不中斷 Vibe Coding 流程
- [x] 擴充 `/v1/chat` 與 `/v1/stream` payload，使其支援可選之 `account_id` 欄位進行 Session 隔離
- [x] 測試 API 介面之完整運作

---

## Task Summary

| Phase | 任務數 | 預估規模 |
|-------|--------|----------|
| PHASE 0 Foundation | 5 tasks, 32 items | 基礎，優先完成 |
| PHASE 1 Protocol | 5 tasks, 37 items | 核心功能 |
| PHASE 2 DX | 5 tasks, 33 items | 開發者體驗 |
| PHASE 3 Quality | 4 tasks, 23 items | 品質保證 |
| PHASE 4 Ecosystem | 3 tasks, 16 items | 生態建設 |
| PHASE 5 Self-Evolution | 3 tasks, 12 items | 長期目標 |
| PHASE 6 Account & Token | 3 tasks, 13 items | 帳號與 Token 管理 |
| **Total** | **28 tasks** | **166 items** |

---

*此文件由 PAP Core Agent 管理。任何新增任務需符合 T-04 Protocol Evolution 流程。*  
*定期執行 5-01 Self-Audit 以更新各任務狀態。*
*當所有任務皆已完成，該檔案可以刪除*
