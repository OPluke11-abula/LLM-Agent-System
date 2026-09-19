# Changelog

## 0.5.0 - 2026-09-19

### Autonomous Software Factory Swarm (Phases 101 ~ 103)

- **Factory Task Decomposition & Mesh Routing**:
  - Added AST decision branch complexity analyzer (`CodeComplexityAnalyzer`) measuring McCabe cyclomatic complexity, coupling, and composite risk scores.
  - Added Kahn's DAG topological task decomposer (`RefactoringTaskDAG`) guaranteeing 100% disjoint mutable scopes for parallel execution waves.
  - Added capability-aware mesh dispatcher routing tasks across reasoning, sandbox mutation, and test execution nodes.
- **Red/Blue Adversarial Committee & Self-Healing Contracts**:
  - Implemented structured adversarial debate (`AdversarialCommitteeEngine`) among Refactoring Architect, Security Attacker, Regression Guardian, and Quorum Arbiter.
  - Added `SelfHealingContract` binding mandatory test assertions and auto-rollback triggers directly to task units with a 70+ Quorum threshold.
- **Closed-Loop Experience Distillation & Factory Cockpit**:
  - Added `PatternDistillationEngine` distilling completed tasks into patterns and lessons stored in federated vector memory with Merkle root validation.
  - Added `LivingArchitectureSynapse` maintaining living Markdown architecture notes with bidirectional Wikilinks.
  - Added real-time Factory Cockpit UI (`/factory`) with KPI banners, wave execution steppers, adversarial transcript panels, and pattern cards.

### Production Zero-Debt Hardening & Modular Decoupling (Phase 104)

- **Frontend Pure Deconstruction**:
  - Eliminated all 6 React Doctor maintainability warnings (**0 issues remaining**).
  - Extracted pure computation helpers outside component boundaries in `IntelligenceMapView`, `MissionControlView`, and `SwarmGovernanceConsole`.
  - Extracted `ConductorTracePanel` into a dedicated subcomponent in `viewer/src/components/topology/`.
- **Backend Core Decoupling**:
  - Decomposed `agent_workspace/core/router.py` (-433 LOC, -28 CC) into `agent_workspace/core/routing/` (`registry.py`, `memory.py`, `template_watcher.py`).
  - Decomposed `agent_workspace/core/discussion_room.py` (-432 LOC, -32 CC) into `agent_workspace/core/discussion/` (`ids.py`, `consensus.py`).
  - Maintained 100% backward-compatible symbol re-exports across both modules.
- **Concurrency & Typed Failure Hardening**:
  - Wrapped synchronous `.env` disk I/O in `agent_workspace/routes/chat.py` with `asyncio.to_thread` to eliminate FastAPI event loop blocking.
  - Replaced all untyped `except Exception: pass` swallows in `api.py` and `long_term_memory.py` with typed exceptions and structured diagnostic logging.
- **Knowledge Base & Obsidian Index Topology**:
  - Added transitive hierarchical BFS indexing to `lint_obsidian_vault.ps1`, eliminating all 249 `not-linked-from-index` warnings across skill notes.
  - Confirmed 100% SHA-256 bitwise parity across all 62 canonical Obsidian notes.

## Unreleased

### Security

- Hardened runtime authentication, secret handling, provider URL validation,
  filesystem containment, task lifecycle limits, and Docker exposure defaults.

### Developer Beta Productization P1

- Added the authenticated System Check and protected Mission control-plane API
  with durable SQLite persistence, optimistic revisions, bounded history, and
  owner isolation.
- Added the generated Python-to-TypeScript Mission contract seam, browser-only
  Mission session-auth boundary, first-run Mission intake, deterministic plan
  approval, and schema-mismatch blocking based on the actual backend version.
- Added an explicit production evidence form and gate-level Review metadata;
  production evidence is recorded through the normal API one gate at a time.
  The `test_fixture` evidence route is authenticated and disabled by default.
- Added a real FastAPI + SQLite + built Viewer Playwright Golden Path with
  authentication, ownership, stale-revision, immutable-approval, missing-ref,
  fixture-disabled, and Review linkage checks, plus offline/store/schema/abort
  and Tauri-unavailable UI checks.

### Runtime efficiency

- Added bounded token-encoding cache reuse, concurrent bounded WebSocket
  fan-out, and request-scoped provider token-count reuse.

### Reliability and cost bounds

- Bounded memory queries and debate provider calls, retries, healing calls,
  nested depth, and provider concurrency.
- Added permanent-error classification, cancellation propagation, and cleanup
  for nested and broker-delegated work.
- Safety defaults are 64 provider calls, 12 retries, 8 healing calls, nested
  depth 1, provider concurrency 3, 100 memory results, and 300 backend fetches;
  these are safety defaults, not benchmark guarantees.

## 0.1.1

- Published the Windows NSIS viewer installer tracked in `releases/`.
- Added the React/Tauri topology, task-flow, governance, memory, and telemetry
  surfaces described in the viewer documentation.
- Added repository verification through `scripts/verify.cmd`.

Unreleased changes are tracked in Git history and the project task queue.
