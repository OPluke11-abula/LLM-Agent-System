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

## 📈 Queue Summary & Progress

| Phase | Total Tasks | Completed Tasks | Status |
|---|---|---|---|
| **Phase 0: Foundation** | 6 tasks | 6 tasks | 100% Done |
| **Phase 1: Protocol** | 5 tasks | 5 tasks | 100% Done |
| **Phase 2: Tooling** | 2 tasks | 2 tasks | 100% Done |
| **Phase 6: Multi-Account** | 3 tasks | 3 tasks | 100% Done |

*This queue is managed dynamically by the active LAS Developer Agent. All task updates, outcome logs, and progress status updates are written directly to this file before turn conclusion.*
