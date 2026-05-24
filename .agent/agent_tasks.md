# PAP Agent Task Queue (English Master Edition)
>
> **Protocol**: Portable Agent Protocol (PAP) v0.1.0  
> **Format**: PAP Task Contract v1  
> **Status legend**: `[ ]` pending · `[~]` in-progress · `[x]` done · `[!]` blocked

---

## 🛠️ PHASE 0 — Foundation & Local Tooling / 基礎與本地工具

### 0-01 Schema Formalization
- [x] Create `spec/` folder
- [x] Document `spec/agent-schema.json` defining `.agent/agent.md` frontmatter
- [x] Document `spec/skill-contract.schema.json` defining capability contract schemas
- [x] Document `spec/memory.schema.json` defining episodic and semantic schemas
- [x] Document `spec/workflow.schema.json` defining workflow step specs
- [x] Add spec metadata descriptions to README.md

---

### 0-02 Memory Landing
- [x] Create `.agent/memory/episodic/` and add design description
- [x] Create `.agent/memory/semantic/` and add description
- [x] Create `.agent/memory/handoff/` for multi-generational transition packets
- [x] Define episodic/semantic schema fields in `.agent/memory/schema.json`
- [x] Create sample memory files under `examples/`
- [x] Implement the thread-safe `MemoryBackend` (SQLite/Redis) in `agent_workspace/memory_backends.py`
- [x] Add unit tests under `agent_workspace/tests/test_memory_backend.py`

---

### 0-03 Skill Contract Standardization
- [x] Verify and populate `.agent/skills/<tool>.md` for all active tools
- [x] Standardize contract fields: `id`, `description`, `inputs`, `outputs`, `safety_notes`, `version`
- [x] Strip proprietary vendor-specific brand references from skill contracts
- [x] Introduce `schema_version` to `.agent/skills.md` registry
- [x] Validate all skill contracts match schemas via `test_skill_contracts.py`

---

### 0-04 Router Dynamic Verification
- [x] Implement runtime JSON schema validation of tool inputs before execution in `router.py`
- [x] Add `Router.list_skills()` returning a structured, validated array of tools
- [x] Add `Router.describe_skill(id)` returning parsed contract metadata
- [x] Add `Router.validate_call(id, params)` for dry-run verification
- [x] Provide precise, granular error output for validation failures
- [x] Write validation test suite in `tests/test_router_validation.py`

---

### 0-05 Elegant Developer CLI (Active DX Goal)
```
priority : HIGH
effort   : S
depends  : 0-04
```
- [x] Create `agent_workspace/cli.py` to serve as the unified local operations tool belt
- [x] Implement `cli.py --list-skills` to dynamically output registered PAP tools (including global overrides)
- [x] Implement `cli.py --describe-skill <id>` to display detailed schemas
- [x] Implement `cli.py --validate` to run structural gate checks (`pap_validate.py`)
- [x] Implement `cli.py --memory-read <key>` and `--memory-write <key> <value>`
- [x] Implement `cli.py --run-workflow <id>` (bridges to Task 1-01)
- [x] Add integration tests in `tests/test_cli.py` and update USAGE.md documentation

---

### 0-06 Open Source Skills Integration
- [x] Copy useful open-source capability patterns into local workspace
- [x] Standardize contracts and format them into `.agent/skills/`
- [x] Remove vendor lock-in references and transform them into generic local Python tools
- [x] Verify safety boundaries and ensure zero external leakage

---

## 🚀 PHASE 1 — Protocol Completeness / 協定完整性

### 1-01 Asynchronous Workflow Engine (Core Execution Goal)
```
priority : HIGH
effort   : L
depends  : 0-04, 0-05
```
- [x] Design n8n-like declarative step representation (`pending` -> `running` -> `success`/`failed`)
- [x] Implement `WorkflowEngine.load(id)` parsing YAML/Markdown steps from `.agent/workflows/<id>.md`
- [x] Implement `WorkflowEngine.run(id, payload)` executing step-by-step with dynamic JSON parameter passing
- [x] Implement `WorkflowEngine.resume(session_id)` to recover and continue from failed checkpoints
- [x] Enable workflow state serialization into `.agent/workflows/runs/<session_id>.json`
- [x] Write asynchronous concurrency and failure paths tests under `tests/test_workflow_engine.py`

---

### 1-02 Knowledge Base Indexing
```
priority : MEDIUM
effort   : M
depends  : 0-01
```
- [x] Create `.agent/knowledge_base/index.json` to catalog tags, creators, and versions
- [x] Format structured frontmatter for all knowledge base documents
- [x] Add indexing helper `KnowledgeBase.query(keyword)` in `agent_workspace/core/knowledge.py`
- [x] Secure read-only access boundaries for static knowledge

---

### 1-03 Prompt Registry Executable
```
priority : HIGH
effort   : M
depends  : 0-01
```
- [x] Structure dynamic prompt snippets with `id`, `template`, `variables`, `version`
- [x] Build `PromptComposer.build(id, vars)` in `agent_workspace/core/prompt_composer.py`
- [x] Implement prompt injection validation (automatic variable escaping to prevent SSTI)
- [x] Add compositor unit tests covering validation and injection guards

---

### 1-04 Cross-Agent Handoff Engine
```
priority : HIGH
effort   : M
depends  : 0-02, 1-01
```
- [x] Define standardized Handoff Packet schema (`task_state`, `context_summary`, `memory_snapshot`, `checksum`)
- [x] Implement `AgentEngine.export_handoff()` to bundle state and write into `.agent/memory/handoff/`
- [x] Implement `AgentEngine.import_handoff(id)` to restore and onboard the next agent thread
- [x] Add packet integrity verification (hash checksum verification)
- [x] Write transition and state serialization tests under `tests/test_handoff.py`

---

### 1-05 Protocol Version Management
```
priority : HIGH
effort   : M
depends  : 0-01
```
- [x] Implement semantic version parser in core engine
- [x] Enable strict manifest requirement checks (min_runtime_version and protocol_version)
- [x] Log and raise warnings for runtime or protocol incompatibilities
- [x] Add version compatibility unit tests in `tests/test_version_compat.py`

---

## 🛠️ PHASE 2 — Developer Tooling & Operations / 開發者工具與維運

### 2-01 CLI Init Subcommand
```
priority : HIGH
effort   : M
depends  : 0-05
```
- [x] Register `init` subcommand supporting `--dry-run` and target output directory
- [x] Model standard skeletal PAP directory structure and entrypoint manifests
- [x] Safely scaffold skeletal configs and contract files
- [x] Write init test coverage in `tests/test_cli_init.py`

---

### 2-02 CLI Lint Subcommand
```
priority : HIGH
effort   : M
depends  : 0-05, 2-01
```
- [x] Implement `lint` command parser supporting `--fix`
- [x] Statically check schema integrity and semver format validation
- [x] Enable contract parity scanning (missing and orphan contracts)
- [x] Verify workflow action resolution and next_step references
- [x] Write lint verification cases in `tests/test_cli_lint.py`

---

## 🔒 PHASE 3 — Quality & Security / 品質與安全安全

### 3-01 Coverage & Pytest-Cov Configuration
```
priority : HIGH
effort   : S
depends  : 0-05
```
- [x] Create `pyproject.toml` in repository root configuring standard pytest options and coverage runs.
- [x] Omit test suites from coverage source to obtain high-precision module coverage statistics.
- [x] Verify automatic coverage report term outputs are printed seamlessly when running `pytest`.

---

### 3-02 Path Traversal Prevention & Coverage Boost
```
priority : HIGH
effort   : L
depends  : 3-01
```
- [x] Implement robust Path Traversal Prevention guards inside `SkillLoader` and `WorkflowEngine` using Path.resolve() and Path.relative_to().
- [x] Add path validation safety checks inside `AgentEngine._parse_skill_md` and `_parse_pap_doc` to secure knowledge parsing boundaries.
- [x] Write high-density unit tests in `tests/test_agent_engine.py` boosting `core/engine.py` coverage to 88% (exceeding 80% goal).
- [x] Write high-density unit tests in `tests/test_skill_loader.py` boosting `core/skill_loader.py` coverage to 94% (exceeding 80% goal).
- [x] Verify traversal violation checks raise explicit PermissionErrors and pass 100% cleanly.

---

## 📊 PHASE 6 — Multi-Account & Token Management / 帳號與額度管理

### 6-01 Account Management Core
- [x] Implement thread-safe `AccountManager` managing model and credential mapping in `accounts.json`
- [x] Support secure add, remove, list, and switch active account operations
- [x] Protect multi-threaded dynamic swaps with concurrency lock guards
- [x] Write core tests under `tests/test_account_manager.py`

---

### 6-02 Dynamic Provider Integration & Token Auditing
- [x] Modify `providers.py` to support dynamic instantiation via runtime keys and custom base URLs
- [x] Auditing: Intercept LLM prompt and completion token usage and log them in real-time
- [x] Support automatic failover to fallback accounts when token budget is exceeded
- [x] Add test verifying real-time token budgeting and failovers

---

### 6-03 API Endpoints & Developer DX
- [x] Expose `GET /v1/accounts` returning list of active credentials and token statistics
- [x] Expose `POST /v1/accounts` and `POST /v1/accounts/active` allowing runtime switches
- [x] Extend `/v1/chat` and `/v1/stream` supporting optional `account_id` payload mapping
- [x] Validate end-to-end WebSocket bidirectional streaming and token statistics writing

---

## 🤝 PHASE 7 — Multi-Agent Consensus & Debate / 多智慧體共識與辯論

### 7-01 Discussion Room Coordinator
```
priority : HIGH
effort   : M
depends  : 6-01
```
- [x] Create core coordinator `agent_workspace/core/discussion_room.py`
- [x] Implement round-robin dialogue loops with context-aware cumulative transcripts
- [x] Conclude with Moderator-led final Consensus Summary compilation
- [x] Add automated unit tests under `tests/test_discussion_room.py`

---

### 7-02 CLI Subcommand Integration
```
priority : HIGH
effort   : M
depends  : 0-05, 7-01
```
- [x] Expose consensus debate feature in `cli.py` via `run-debate` subcommand
- [x] Support custom topic, agent roles, and rounds parameter mapping
- [x] Format transcript prints and print final synthesized Consensus Summary

---

## 🎨 PHASE 8 — Visual Topology Workspace & UI/UX / 視覺拓撲工作區與 UI/UX

### 8-01 Zero-Build Viewer Polish & Aesthetic Refinement
```
priority : HIGH
effort   : M
depends  : 0-04, 1-01
```
- [x] Optimize `workspace/viewer.html` to support dynamically adjustable Dagre node spacing and rank separation.
- [x] Refine the dark-mode layout with transparent glassmorphism panels and vibrant HSL status borders.
- [x] Display live latency gauges, cost summaries, and active token counters on the selected node detail card.
- [x] Write integration test verification for browser state pooling.

---

### 8-02 React Flow & Tauri Desktop Client Styling
```
priority : HIGH
effort   : L
depends  : 8-01
```
- [x] Stylize custom node components under `viewer/src/` with premium glassmorphism layouts.
- [x] Dynamically map different border color schemes for active models (Gemini-blue, Claude-orange, GPT-green).
- [x] Implement real-time mini charts inside the node card displaying cumulative token cost per generation chunk.
- [x] Enable drag-and-drop workflow step generation on the canvas.

---

### 8-03 Bidirectional Real-Time Streaming Visuals
```
priority : HIGH
effort   : M
depends  : 6-03, 8-02
```
- [x] Implement WebSocket or Server-Sent Events (SSE) connection listeners in the frontend to capture active stream payloads.
- [x] Animate running nodes dynamically with pulsing borders and sliding typing micro-animations as tokens stream in.
- [x] Animate handoff edges with glowing flow particles traveling from source to target agent upon active transfer.

---

## 🔒 PHASE 9 — Human-in-the-Loop & Dynamic RBAC / 人機協同與動態角色存取控制

### 9-01 Intercept & Paused Loop in AgentRouter / 路由器攔截與暫停迴圈
- [x] Implement global approval registry and custom exception `ApprovalDeniedError` / 實作全域核准註冊表與自訂異常 `ApprovalDeniedError`
- [x] Intercept sensitive tools or `interactive-approval` authorization limits / 攔截敏感工具或 `interactive-approval` 授權限制
- [x] Emit `hitl_gate` topology event with status `awaiting_approval` / 發送狀態為 `awaiting_approval` 的 `hitl_gate` 拓撲事件
- [x] Write `test_hitl.py` unit tests with SQLite locks prevention / 撰寫 `test_hitl.py` 單元測試並防止 SQLite 鎖定

---

### 9-02 RBAC Static Guard / 角色型存取控制靜態防禦
- [x] Parse and validate `required_role` contract property / 解析並驗證 `required_role` 合約屬性
- [x] Enforce role permission hierarchy (`admin` > `developer` > `standard`) / 強制執行角色權限階級 (`admin` > `developer` > `standard`)
- [x] Raise `PermissionError` and emit `rbac` edge event with status `error` on violation / 違規時引發 `PermissionError` 並發送 `error` 狀態的 `rbac` 邊緣事件
- [x] Write `test_rbac.py` unit tests / 撰寫 `test_rbac.py` 單元測試

---

### 9-03 API Endpoints & Interactive CLI / API 端點與互動式 CLI
- [x] Expose `POST /v1/sessions/{session_id}/approve` and `/reject` in `api.py` / 在 `api.py` 中公開 `POST /v1/sessions/{session_id}/approve` 與 `/reject`
- [x] Update `cli.py` to support `--chat` and `--stream` commands / 更新 `cli.py` 支援 `--chat` 與 `--stream` 指令
- [x] Handle interactive prompt approvals `[y/N]` without blocking asyncio loops / 處理互動式提示核准 `[y/N]` 且不阻塞 asyncio 迴圈

---

### 9-04 Pulsing Visuals & Zero-Build Dashboard / 脈動視覺與零編譯儀表板
- [x] Style goldPulse amber border for awaiting_approval nodes in `viewer.html` / 在 `viewer.html` 中為等待核准的節點設計金黃脈動邊框
- [x] Style dynamic glowing edge flow colors based on status (gold for HITL, red for RBAC errors) / 根據狀態動態調整流動粒子邊緣色彩 (核准路徑為金色，錯誤路徑為紅色)
- [x] Render glassmorphic card Approve/Reject action buttons in `viewer.html` / 在 `viewer.html` 的卡片中渲染玻璃擬態核准/拒絕按鈕
- [x] Enable flow particles for React Flow `hitl` / `rbac` edge types in `TopologyEdgeBase.tsx` / 在 `TopologyEdgeBase.tsx` 中為 React Flow 的 `hitl`/`rbac` 邊緣啟用粒子流
- [x] Integrate interactive sidebar card actions in `TopologyView.tsx` / 在 `TopologyView.tsx` 中整合互動式側邊欄卡片操作

---

## 📈 Queue Summary & Progress

| Phase | Total Tasks | Completed Tasks | Status |
|---|---|---|---|
| **Phase 0: Foundation** | 6 tasks | 6 tasks | 100% Done |
| **Phase 1: Protocol** | 5 tasks | 5 tasks | 100% Done |
| **Phase 2: Tooling** | 2 tasks | 2 tasks | 100% Done |
| **Phase 3: Quality & Security** | 2 tasks | 2 tasks | 100% Done |
| **Phase 6: Multi-Account** | 3 tasks | 3 tasks | 100% Done |
| **Phase 7: Consensus** | 2 tasks | 2 tasks | 100% Done |
| **Phase 8: UI/UX & Visuals** | 3 tasks | 3 tasks | 100% Done |
| **Phase 9: HITL & RBAC** | 4 tasks | 4 tasks | 100% Done |

*This queue is managed dynamically by the active LAS Developer Agent. All task updates, outcome logs, and progress status updates are written directly to this file before turn conclusion.*
