# LAS Agent Task Queue

> Protocol: Portable Agent Protocol (PAP) task contract
> Legend: `[ ]` pending, `[~]` in progress, `[x]` done, `[!]` blocked

## Token-Efficient Reading Contract

- Start here instead of reading old completed task prose.
- Completed phases are summarized only; inspect git history, docs, or evidence
  reports only when a task needs exact historical detail.
- Keep active and pending phases expanded so the next agent can execute without
  asking for context.
- Do not re-expand completed history unless the user explicitly asks.

## Current Queue State

| Phase | Total | Done | Status | Next action |
|---|---:|---:|---|---|
| 0-66 | archived | done | 100% Done | Historical summary only |
| 67 | 8 | 8 | 100% Done | Visual QA and verification gate complete |
| 68 | 8 | 8 | 100% Done | React Doctor advisory gate complete |
| 69 | 8 | 8 | 100% Done | Local knowledge base and agent memory OS complete |
| 70 | 8 | 2 | 25% In Progress | Continue `70-03` report-only context budget preflight |
| 71 | 8 | 5 | 62% In Progress | Hold `71-06` to `71-08` until queue permits |

Execution order:

1. Continue Phase 70 now that Phases 67 to 69 are closed.
2. Then continue remaining Phase 71 work unless the user
   explicitly reprioritizes.

## Completed Phase Rollup

- [x] Phases 0-31: foundation, PAP layout, async workflows, sandboxing,
  security gates, memory, model/account selection, swarm debate, dashboard,
  HITL, Docker/Tauri, org-chart agents, topology, concurrency, rate limiting,
  federated sync, context minimization, skill exchange, prompt/code generation,
  handoff balancing, and P2P storage/communications.
- [x] Phases 32-43: zero-trust sandbox/IDS, vector memory, crew orchestration,
  SaaS/admin/auth/billing foundations, Redis microservices, cryptographic audit
  consensus, enterprise admin console, and PAP v0.2 alignment.
- [x] Phases 44-58: premium control-plane cleanup, semantic frontend memory,
  settings/task/admin refinements, swarm operations UI, routing, state
  replication, mesh orchestration, billing scheduling, replay logging, ZK audit,
  governance UI, telemetry sockets, and mTLS key rotation.
- [x] Phases 59-66: production mTLS/Stripe integration, token counters and
  compaction gates, Fugu-inspired conductor layer, dependency/security baseline,
  adaptive routing memory, PAP workflow/evidence/review gates, codebase-memory
  graph tools, and PAP mainline sync/conformance/registry/runtime parity.
- [x] Phase 67 completed items: `67-01` to `67-08` shipped the premium Mission
  Control design contract, first screen, command palette, next-action rail, Task
  Flow 2.0, Intelligence Map, Governance/Security Cockpit, and final
  visual QA/verification gate.
- [x] Phase 68 completed items: `68-01` added advisory React Doctor config and
  scripts without enabling blocking CI; `68-02` added the LAS-owned bounded JSON
  report ingestion parser and focused tests; `68-03` removed browser-delivered
  admin/demo key literals from viewer source and rebuilt artifacts, leaving no
  `artifact-secret-leak` finding in the latest React Doctor output; `68-04`
  split `AdminDashboardView` graph initialization, WebSocket handling, and
  offline simulation so the latest React Doctor summary has zero errors; `68-05`
  reduced the full React Doctor accessibility baseline to one deferred
  `CommandPalette` native-dialog warning; `68-06` decomposed the remaining
  giant-component hotspots and the latest React Doctor output has zero
  `no-giant-component` findings; `68-07` added the React Health Intelligence
  Map surface backed by LAS parser output for category counts, top files,
  current errors, changed-file regressions, and next fix queue; `68-08` added
  advisory GitHub Actions React Doctor CI for `viewer` with `scope: full` and
  `blocking: none`.
- [x] Phase 71 completed items: `71-01` to `71-05` created the professional
  design-agent role, art direction packet, moodboard workflow, screen studies,
  and `viewer/DESIGN.md` implementation contract.

## Phase 67 - Premium AI Mission Control UI/UX Upgrade

Status: `[x]` 8/8 complete. Final verification/design-gate closure completed.

### 67-08 Visual QA and Verification Gate
- [x] **[Frontend QA]** Verify the upgraded viewer with production build, UI
  marker checks, screenshot QA at 375/768/1280px, keyboard navigation,
  hover/focus/loading/empty/error states, and reduced-motion behavior.
- Required checks before closing: `npm.cmd --prefix viewer run build`,
  `npm.cmd --prefix viewer run verify:ui:screenshots`, `git diff --check`, and
  `scripts\verify.cmd`.
- Supporting queue: `.agent/programmer/agent_tasks.md` Phase P1 covers
  deterministic visual fixtures, Playwright screenshot capture, and rendered
  copy audit.
- Design evidence: `.agent/knowledge_base/exports/phase-67-design-critique-flow-report-2026-07-07.md`
  keeps this task open until Phase 71 professional design evidence is consumed.
- Progress: consumed the Phase 71 design contract in `viewer/DESIGN.md`, expanded
  `viewer/scripts/verify-ui.mjs` with deterministic visual fixtures,
  375/768/1280px screenshots, command-palette focus/keyboard coverage,
  hover/reduced-motion states, governance cockpit captures, and zh rendered-copy
  audits for Rules/MODs/Settings. Fixed the active mission rail so long
  workspace paths wrap inside the dashboard rail instead of widening the page.

## Phase 68 - React Doctor Quality Gate and LAS Health Model

Status: `[x]` 8/8 complete. React Doctor remains advisory. Do not run
`react-doctor install`, agent hooks, or CI installer without explicit approval.
Do not print secret-like values from diagnostics.

Reference plan: `docs/architecture/react-doctor-las-adoption-plan.md`.

### 68-01 React Doctor Advisory Config
- [x] **[Frontend QA]** Added advisory-only `viewer/doctor.config.json` and
  `doctor`, `doctor:json`, and `doctor:changed` scripts. Baseline produced
  parseable JSON with no generated `dist/` diagnostics.

### 68-02 React Doctor Report Ingestion
- [x] **[Backend/Tooling Programmer]** Added `agent_workspace/react_doctor_report.py`
  with `python -m agent_workspace.react_doctor_report <react-doctor-json>` support.
  The parser writes `.agent/reports/react-doctor/react-doctor-summary.json` by
  default, captures category/severity totals, top files, bounded error findings,
  affected Phase 67 surfaces, verification commands, and redacts secret-like
  values. Covered by `agent_workspace/tests/test_react_doctor_report.py`.

### 68-03 Security Artifact Triage
- [x] **[Security/Frontend Programmer]** Removed hardcoded admin/demo key
  literals from `AdminDashboardView`, `PromptCalibrationDashboard`, and
  `SwarmGovernanceConsole`; added runtime-only admin auth helpers backed by
  `localStorage["las_admin_api_key"]`; rebuilt `viewer/dist`; regenerated
  React Doctor raw and LAS summary reports. `artifact-secret-leak` is absent;
  the remaining React Doctor error is the 68-04 state/effect finding.

### 68-04 Effect and State Correctness Fixes
- [x] **[Frontend Programmer]** Fixed the current error-class
  `AdminDashboardView` state/effect finding by moving stable graph initial state
  out of effect-driven setters and separating WebSocket lifecycle from offline
  mock playback. Regenerated React Doctor raw and LAS summary reports; the
  latest summary reports zero error findings.

### 68-05 Accessibility Control Sweep
- [x] **[Frontend QA/UX Programmer]** Resolved high-volume
  `control-has-associated-label`, keyboard handler, and focusability findings
  across `LongTermMemoryView`, `TaskFlowView`, `SettingsView`,
  `AdminDashboardView`, `ModsView`, and shared primitives. Latest full React
  Doctor accessibility output has one remaining warning: `CommandPalette`
  prefers native `<dialog>`, deferred because it is a modal behavior conversion.

### 68-06 Giant Component Decomposition
- [x] **[Frontend Architect]** Decompose React Doctor giant-component hotspots
  (`TopologyView`, `AdminDashboardView`, `TaskFlowView`, `LongTermMemoryView`,
  `SettingsView`, `SwarmGovernanceConsole`) along Phase 67 cockpit boundaries:
  shell, telemetry panels, action rail, graph canvas, inspector, and evidence
  lists.
- Progress: extracted `SettingsView` into a thin shell plus General, Docs, and
  AI Guide tab panels; extracted `PromptCalibrationDashboard` panel sections;
  extracted `TaskFlowView` into a controller hook plus workspace tabs, hero,
  stats, controls, timeline, canvas, intelligence, and modal sections; extracted
  `SwarmGovernanceConsole` into a controller hook plus a shell component;
  extracted `AdminDashboardView` into a controller hook plus header, billing,
  live-interceptor, and audit-ledger sections; extracted `LongTermMemoryView`
  into a controller hook plus header, stats, folder sidebar, records panel, and
  modal sections; extracted `TopologyView` into a controller hook plus control
  rail, topology canvas, inspector rail, router, collaboration, activity,
  telemetry, ledger, and sandbox sections. Latest React Doctor summary reports
  zero `no-giant-component` findings.

### 68-07 React Health Intelligence Surface
- [x] **[Frontend/Backend Programmer]** Add a `React Health` surface to the
  Intelligence Map or verification dashboard. Show category counts, top affected
  files, current errors, changed-file regressions, and next fix queue from the
  LAS parser output.
- Progress: extended `agent_workspace.react_doctor_report` with optional
  changed-scope report ingestion, `changed_file_regressions`, `next_fix_queue`,
  and `--snapshot-output`; generated `viewer/src/data/react-doctor-summary.json`
  from the LAS parser; added `ReactHealthPanel` to the Intelligence Map and
  documented the route contract in `viewer/DESIGN.md`. Verified production
  build, parser tests, UI checks, and screenshot capture. A final post-UI JSON
  refresh was blocked by the platform escalation usage limit, but the
  post-implementation changed-scope React Doctor text scan completed with the
  existing 27 warning summary.

### 68-08 CI Rollout and Gate Tightening
- [x] **[QA/DevOps]** After the advisory baseline is stable, add GitHub Actions
  React Doctor in advisory mode for `directory: viewer`, `scope: full`, and
  `blocking: none`; later switch to changed-file error blocking, then warning
  blocking only after the baseline is clean.
- Progress: added `.github/workflows/react-doctor.yml` using
  `millionco/react-doctor@v2`, full-history checkout, PR comment/status
  permissions, `directory: viewer`, `scope: full`, and `blocking: none`. This
  is advisory-only and does not install React Doctor hooks or run the CI
  installer. Validated workflow YAML and required inputs locally; no commit,
  push, PR, or remote CI run was performed.

## Phase 69 - LAS Local Knowledge Base and Agent Memory OS

Status: `[x]` 8/8 complete. Planning source:
`C:/Users/luke2/OneDrive/文件/Obsidian Vault/exports/AI Agent Development Knowledge for LAS - 2026-07-02.md`.
Use Markdown-first, report-only workflows; do not install Obsidian plugins,
background watchers, semantic retrieval, or hooks until the file contract is
proven.

### 69-01 Knowledge Base Skeleton
- [x] **[Architect/Documentation]** Add `.agent/knowledge_base/` skeleton:
  `index.md`, `log.md`, and subdirectories for `raw/`, `wiki/`, `projects/`,
  `workflows/`, `handoffs/`, `decisions/`, `known-issues/`, `exports/`, and
  `templates/`.
- Progress: confirmed the existing Markdown-first KB already had `index.md`,
  `log.md`, and all required directories except `wiki/`; added
  `.agent/knowledge_base/wiki/.gitkeep`, added the wiki section to
  `.agent/knowledge_base/index.md`, and logged the skeleton closure in
  `.agent/knowledge_base/log.md`.

### 69-02 Project Intake Workflow and Artifact
- [x] **[Backend/Documentation Programmer]** Add canonical project intake for
  `D:/GitHub/LLM-Agent-System`: path, branch/HEAD, dirty caveat, runtimes,
  verification commands, architecture pointers, high-value symbols, code graph
  pointer, and live-verification requirements.
- Progress: refreshed `.agent/knowledge_base/projects/LLM-Agent-System.md`
  with live branch/HEAD/dirty state, active runtime versions, main source
  areas, runtime entrypoints, verification commands, Codebase Memory MCP index
  status, route/API pointers, architecture pointers, high-value symbols, and
  explicit live-verification caveats.

### 69-03 Query Memory Contract
- [x] **[Backend/Agent UX Programmer]** Add query-memory workflow/report with
  `Memory-Derived`, `Verified Now`, `Not Verified`, and `Next Checks` sections.
  Require live checks before current-state claims.
- Progress: updated `.agent/knowledge_base/workflows/query-memory.md` to require
  live checks before current-state claims, separate memory-derived facts from
  verified facts, use `Next Checks` for unverified claims, and link a reusable
  `.agent/knowledge_base/templates/query-memory-report.md` report template.

### 69-04 Handoff Generator Contract
- [x] **[Backend/Workflow Programmer]** Add handoff workflow/command gathering
  goal, current state, changed files, checks run, memory notes, decisions,
  unverified items, and next-read links.
- Progress: updated `.agent/knowledge_base/workflows/handoff.md` with a
  section-by-section handoff generator contract, memory-note handling,
  repo-local versus temp handoff boundary, exact verification evidence rules,
  next-read links, next action, suggested skills, and linked
  `.agent/knowledge_base/templates/handoff-report.md`.

### 69-05 Knowledge Base Maintenance Gate
- [x] **[QA/Tooling Programmer]** Add report-only maintenance checks for missing
  links, orphan/empty notes, unresolved note links, weak handoffs, weak
  decisions/known issues, and possible secret-like values.
- Progress: extended the shared read-only health linter and maintenance workflow
  with required-file/directory, orphan/empty note, wikilink, handoff read-order,
  decision revisit, known-issue verification, and credential-pattern checks.
  The JSON and Markdown audit surfaces both returned zero findings.

### 69-06 Evidence Memory Bridge
- [x] **[Backend Programmer]** Bridge knowledge notes with LAS evidence memory:
  keep raw output in evidence refs/canonical artifacts and compact summaries in
  notes with citations.
- Progress: added [[workflows/evidence-memory-bridge]] and
  [[templates/evidence-memory-summary]] to connect redacted knowledge-base
  evidence to the existing explicit `memory_pack.py` artifacts without enabling
  watchers, automatic capture, or long-term-memory writes.

### 69-07 Code Graph Bridge in Project Notes
- [x] **[Backend/Architect]** Store bounded code graph pointers and high-value
  symbols in project notes. Require graph refresh or live source lookup before
  edits.
- Progress: added [[workflows/code-graph-bridge]] and updated the canonical
  project intake with bounded change-area symbol groups, narrow graph-query
  guidance, caller tracing at sensitive boundaries, and an explicit refresh or
  live-source requirement before edits.

### 69-08 Workflow Manifests and Agent Report Contract
- [x] **[Protocol Architect/QA]** Convert repeated Markdown workflows into PAP
  workflow manifests where useful and standardize reports with `Changed On
  Disk`, `Verified`, `Not Verified`, `Memory Used`, `Decisions`, and `Next`.
- Progress: added the stage-based, report-only
  `.agent/workflows/knowledge-base-report.yaml` manifest plus
  [[workflows/agent-report-contract]] and [[templates/agent-report]]. The
  contract preserves specialized templates while requiring a common compact
  report core.

## Phase 70 - Token-Efficient Agent Work Mode

Status: `[~]` 2/8 complete. Apply the token-saving operating model to LAS as an
advisory/report-only work mode. Do not archive, delete, compact, or mutate
session state automatically.

### 70-01 Work Mode Policy Contract
- [x] **[Protocol Architect]** Define `standard`, `token_efficient`, and
  `deep_research` modes with read budgets, tool-output budgets, broad-scan
  rules, verification ladder, screenshot policy, and escalation rules.
- Progress: added [[workflows/token-efficient-work-mode]] as an advisory
  Markdown-first policy with soft retrieval/output ceilings, narrow-lookup-first
  rules, verification/screenshot ladders, escalation triggers, and no automatic
  session-state mutation.

### 70-02 Conductor Token-Efficient Plan Profile
- [x] **[Backend Programmer]** Extend `ConductorPlan` or metadata with optional
  token-efficient profile fields: bounded memory scope, preferred code graph
  lookup, max tool payload size, staged verification, and handoff thresholds.
- Progress: added typed optional `TokenEfficientProfile` and
  `HandoffThresholds` models, wired them into `ConductorPlan` and
  `build_default_conductor_plan`, and preserved default plan serialization and
  routing selection.

### 70-03 Report-Only Context Budget Preflight
- [ ] **[Backend Programmer]** Add preflight cost estimates using existing token
  counters, tool schemas, memory refs, task context, and code graph refs. Output
  totals and reductions without trimming automatically.

### 70-04 Structural Lookup First Router
- [ ] **[Backend/Tooling Programmer]** Add workflow/helper rules that prefer
  code graph lookup, bounded snippets, and narrow search before broad file reads;
  record broad-read justification.

### 70-05 Layered Verification Profiles
- [ ] **[QA/Tooling Programmer]** Define `focused`, `surface`, `full`, and
  `release` verification profiles mapped to focused pytest, viewer build,
  screenshot QA, `git diff --check`, and `scripts\verify.cmd`.

### 70-06 Handoff-First Long Session Gate
- [ ] **[Workflow Programmer]** Add report-only handoff recommendation when
  history, changed-file count, evidence refs, or estimated context cost exceeds
  thresholds.

### 70-07 Viewer Token Mode Surface
- [ ] **[Frontend Programmer]** Surface work mode, context estimate, largest
  contributors, recommended next action, verification profile, and handoff
  recommendation in Mission Control or Intelligence Map.

### 70-08 Governance, Tests, and Rollout
- [ ] **[QA/Architect]** Add tests for report-only preflight, profile selection,
  broad-read justification, verification-profile mapping, and handoff thresholds.
  Roll out advisory-only first.

## Phase 71 - Professional Design Agent and Art Direction Pipeline

Status: `[~]` 5/8 complete. Design-first work is partially advanced but should
not displace Phase 68 unless explicitly reprioritized.

### 71-01 Professional Design Agent Role Contract
- [x] **[Design Director/Protocol Architect]** Added
  `.agent/prompts/roles/professional_design_agent.md` with responsibilities,
  activation conditions, critique/art-direction outputs, boundaries, and success
  criteria.

### 71-02 Design Brief and Art Direction Packet
- [x] **[Professional Design Agent]** Added
  `.agent/knowledge_base/exports/phase-71-las-viewer-art-direction-packet-2026-07-07.md`
  with the `Cognitive Operations Atlas` metaphor and reusable art direction.

### 71-03 Visual Reference and Moodboard Workflow
- [x] **[Professional Design Agent]** Added
  `.agent/knowledge_base/workflows/visual-reference-moodboard.md` and linked it
  from the knowledge-base index.

### 71-04 Screen-by-Screen Composition Studies
- [x] **[Product Designer/UX Architect]** Added
  `.agent/knowledge_base/exports/phase-71-screen-composition-studies-2026-07-07.md`
  with first-viewport hierarchy, scan path, density, responsive behavior, and
  required visual assets per viewer surface.

### 71-05 Design Packet to Implementation Contract
- [x] **[Frontend Architect]** Updated `viewer/DESIGN.md` into the Phase 71
  `Cognitive Operations Atlas` implementation contract.

### 71-06 Visual Asset and Illustration Pipeline
- [ ] **[Visual Designer/Asset Pipeline]** Define when LAS should use generated
  bitmap assets, diagrams, screenshots, SVG/canvas compositions, or Figma mockups.
  Add local storage, accessibility, responsive cropping, optimization, and
  screenshot verification constraints.

### 71-07 Independent Design Review Gate
- [ ] **[Design QA]** Add review gate scoring coherence, craft, hierarchy,
  typography, color, spacing, motion, accessibility, and vibe-coded risk. Track
  findings as tasks.

### 71-08 Design-Agent Viewer Integration
- [ ] **[Frontend/Design Systems Programmer]** Surface current art direction,
  approved design packet, open design findings, screenshot evidence, unresolved
  taste debt, and next design-first task inside LAS.

---

Managed by the LAS Developer Agent. Keep completed history compact and pending
work executable.
