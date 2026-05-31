# PAP Agent Task Queue (English Master Edition)
>
> **Protocol**: Portable Agent Protocol (PAP) v0.1.0  
> **Format**: PAP Task Contract v1  
> **Status legend**: `[ ]` pending · `[~]` in-progress · `[x]` done · `[!]` blocked

---

## 🛠️ COMPLETED PHASES (Phases 0 - 14 Summarized Archive)

- [x] **PHASE 0 — Foundation & Local Tooling**: Schemas, memory backend, skill contracts, dynamic routing & DX CLI.
- [x] **PHASE 1 — Protocol Completeness**: n8n-like Asynchronous Workflow Engine and dynamic knowledge base indexing.
- [x] **PHASE 2 — Local Sandboxing & Virtual Env Execution**: Python execution context safety sandboxing and standard CLI tools.
- [x] **PHASE 3 — Advanced Static Analysis & Dynamic Security Verification**: Static linting gates and dynamic security audits.
- [x] **PHASE 4 — Asynchronous Workflow Designer Canvas UI**: Interactive node DAG rendering and visual canvas.
- [x] **PHASE 5 — Semantic Retrieval & Episode Summarization**: Dense memory search and compact milestone summaries.
- [x] **PHASE 6 — Multi-Account Configuration & Model Selection Adapter**: accounts.json loading and dynamic LLM provider factory.
- [x] **PHASE 7 — Multi-Agent Swarm Debate Consensus Engine**: Discussion room sequential debate loops.
- [x] **PHASE 8 — Sleek Real-Time Dashboard UI/UX**: Node runtime flow visual tracking dashboards.
- [x] **PHASE 9 — Human-In-The-Loop (HITL) Gateways**: Dynamic approval hooks and role-based access control.
- [x] **PHASE 10 — Production Dockerization & Tauri Desktop Edge**: Containerized backend and edge UI control windows.
- [x] **PHASE 11 — Multi-Agent Swarm Corporate Org-Chart**: Org roles (CEO, CTO, Dev, QA, CFO) and audit suites.
- [x] **PHASE 12 — Mind-Map Edge Topology & Dynamic Guides**: Categorized mind-map edge links and dynamic `.agent` detection.
- [x] **PHASE 13 — High-Throughput Concurrency & Log Compactor**: Class-level SQLite lock isolation and logging.
- [x] **PHASE 14 — Rate Limiting & Federated Lessons Learned Sync**: Sliding window limiters and decentralized lesson sync.

---

## 🏢 PHASE 15 — Advanced Multi-Agent Self-Evolutions & Self-Healing Swarms / 進階多智慧體自我演化與自我修復群落

### 15-01 Declarative Swarm Workspace & Dynamic Role Guide Injection
- [x] Scaffold standard role prompt contract files under `.agent/prompts/roles/dev.md`, `qa.md`, `cfo.md` etc. / 在 `.agent/prompts/roles/` 下建立宣告式角色合約檔案
- [x] Refactor `DiscussionRoom` to dynamically load participant persona templates from markdown / 重構 `DiscussionRoom` 自宣告式 markdown 檔案動態載入系統提示詞
- [x] Dynamically read and append role-specific guides (e.g. `programmer_learning_guide.md`, `qa_learning_guide.md`) as self-learning directives / 根據智慧體角色動態載入並追加對應的學習指南
- [x] Write integration test coverage asserting correct dynamic system prompt injections / 撰寫單元測試驗證宣告式提示詞動態注入的正確性

---

### 15-02 Auto-Diagnosis & Error Self-Healing Loop
- [ ] Implement self-healing logic inside `WorkflowEngine` and `DiscussionRoom` to intercept task/QA failures / 在工作流與辯論引擎中實作錯誤攔截自我修復機制
- [ ] Trace stderr traceback messages and match best practice policies from `lessons_learned.md` / 解析錯誤訊息並媒合 `lessons_learned.md` 中最佳實踐政策
- [ ] Generate and re-apply correction patch files automatically up to 3 retry attempts / 自動生成並套用修正程式碼，支援最多 3 次嘗試
- [ ] Write pytest verification suite asserting a successful self-healing cycle / 撰寫 pytest 單元測試驗證自動修復環路

---

### 15-03 CFO Account Failover Swapping Middleware
- [ ] Refactor `AccountManager` and `api.py` connection stream adapters to support dynamic client swapping / 重構 API 連線適配器以支援動態備用帳戶切換
- [ ] Intercept token budget exhaustion blocks and API rate limits (HTTP 429) inside swarm debate loops / 在 Swarm 併發執行中攔截限流與 Token 超限錯誤
- [ ] Swap active LLM account to backup accounts and retry request without dropping WebSocket connections / 自動無縫切換至備援帳戶重試請求而不中斷 WebSocket 串流連線

---

### 15-04 Telemetry Latency & Cost Alerting
- [ ] Calculate real-time duration and token accumulation chunk-by-chunk for active node executions / 實作節點執行時間與 Token 累計之即時計量
- [ ] Inject dynamic warning telemetry flags `active_latency_alert=true` or `cost_alert=true` when exceeding thresholds / 當效能或成本超標時動態注入效能警報標記
- [ ] Broadcast performance telemetry alerts over `/v1/dashboard/` WS adapters in real-time / 透過 `/v1/dashboard/` WS 廣播即時效能 telemetry 警報

---

## 📈 Queue Summary & Progress

| Phase | Total Tasks | Completed Tasks | Status |
|---|---|---|---|
| **Phase 0 - 14** | 46 tasks | 46 tasks | 100% Done |
| **Phase 15** | 4 tasks | 1 task | 25% In Progress |

*This queue is managed dynamically by the active LAS Developer Agent. All task updates, outcome logs, and progress status updates are written directly to this file before turn conclusion.*
