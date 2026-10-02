# React Doctor Adoption Plan for LAS

Date: 2026-07-02

## Source Summary

React Doctor is a deterministic React scanner from `millionco/react-doctor`. Its documented scope is state and effects, performance, architecture, security, and accessibility across React frameworks including Vite. It supports local CLI scans, JSON output, configurable `doctor.config.*`, agent skill installation, and pull-request CI review. Official docs recommend starting locally, then moving to CI with changed-file gating and optional advisory mode.

Primary sources:

- https://github.com/millionco/react-doctor
- https://www.react.doctor/docs
- https://www.react.doctor/docs/reference/cli-reference
- https://www.react.doctor/docs/configuration/config-files
- https://www.react.doctor/docs/ci-and-prs/github-actions-setup
- https://www.react.doctor/docs/rules

## Local LAS Audit

Command run from `viewer/`:

```bash
npx.cmd --yes react-doctor@latest . --json --no-score --no-telemetry --blocking none
```

Result:

- React Doctor version: `0.5.8`
- Project detected: Vite, React `^19.1.0`, TypeScript, Tailwind `^4.3.1`
- Source files scanned: 47
- Diagnostics: 3 errors, 111 warnings, 21 affected files
- Categories: Bugs 37, Accessibility 35, Maintainability 32, Performance 9, Security 1

Top LAS findings:

| Area | Evidence | LAS impact |
|---|---|---|
| Accessibility labels | 22 `control-has-associated-label` findings | Phase 67 command surfaces, icon buttons, topology controls, and dense cockpit controls need systematic accessible names. |
| Oversized components | `TopologyView`, `AdminDashboardView`, `TaskFlowView`, `LongTermMemoryView`, `SettingsView`, `SwarmGovernanceConsole` | Current UI architecture resists premium UX changes because route components own too many states, effects, and sections. |
| Effect/state correctness | `no-adjust-state-on-prop-change`, `no-cascading-set-state`, `exhaustive-deps`, `prefer-useReducer` | Several cockpit views can show stale intermediate state or fan out render updates during live telemetry. |
| Data fetching in effects | 7 `no-fetch-in-effect` findings, especially `TopologyView` and `SettingsView` | Backend integration should move toward typed frontend service adapters and reusable query hooks rather than route-local fetch loops. |
| Security artifact | `artifact-secret-leak` in built `dist/assets/AdminDashboardView-*.js` | The viewer currently ships admin-like literal demo keys such as `key-admin`; even if local/mock, React Doctor treats browser artifacts as untrusted delivery. |
| Performance | repeated `Intl` formatter creation and array-index keys | Easy wins before Phase 67 visual polish: hoist formatters and use stable ids in high-frequency lists. |

## Applicability to LAS

### Directly Useful

React Doctor should become an advisory quality gate for the React/Tauri viewer before Phase 67 implementation continues. LAS already has `viewer` build and UI marker checks, so React Doctor fits beside `npm.cmd --prefix viewer run build`, `verify:ui`, and screenshot QA.

Recommended local command:

```bash
npm.cmd --prefix viewer exec -- react-doctor . --no-telemetry --no-score --blocking none
```

Recommended JSON command for automation:

```bash
npm.cmd --prefix viewer exec -- react-doctor . --json --no-telemetry --no-score --blocking none
```

Do not enable blocking CI immediately. The current full scan has 114 diagnostics. Start with an advisory baseline, fix highest-risk issues, then gate changed files only.

### Useful After LAS Wrapping

React Doctor's JSON output should feed a LAS-owned parser that writes a bounded report under `.agent/reports/` or `workspace/reports/`. That parser can map findings to:

- task IDs in `.agent/agent_tasks.md`
- files and line numbers in viewer source
- risk category: Security, Bugs, Accessibility, Performance, Maintainability
- Phase 67 surface ownership: Mission Control, Task Flow, Intelligence Map, Governance, Settings
- verification commands and expected gates

This keeps React Doctor as an external scanner while LAS owns planning, evidence retention, and agent handoff semantics.

### Not Recommended Yet

Do not run `npx react-doctor@latest install` or `react-doctor ci install` in the repo yet. The installer can add agent skills, hooks, and workflows. That should be a separate approved external-state change after the advisory baseline is accepted.

Do not blindly suppress findings. The config docs support ignores and inline disables, but LAS should use them only for narrow, documented exceptions. The first pass should fix true positives in source and ignore only generated output or known false positives.

## UI/UX Upgrade Concepts for LAS

React Doctor reinforces the Phase 67 direction:

1. Split giant route components into composable cockpit panels before adding premium visuals. This reduces state coupling and makes visual QA more reliable.
2. Treat accessibility labels as part of the premium UX, not a compliance afterthought. Every icon-only or compact control must have visible text or `aria-label`.
3. Replace route-local fetch/effect loops with typed service adapters and view models. Mission Control should render stable state, not coordinate backend polling in the same component as layout.
4. Add a `React Health` surface to the Intelligence Map: category counts, top affected files, changed-file regressions, and next fix queue.
5. Promote "deterministic scanner output" into the agent workflow: React Doctor findings become task evidence, not free-form reviewer prose.

## Backend and Core LAS Concepts

React Doctor is frontend-specific, but its operating model applies to LAS core:

- Deterministic health scanners should produce structured JSON that LAS can ingest as evidence.
- Gates should start advisory, then become changed-file blocking after the baseline is known.
- Findings should map to tasks, owners, verification commands, and affected surfaces.
- Security findings from browser artifacts should be treated as report-only until triaged, then converted to concrete remediation tasks.
- The same pattern can generalize beyond React: `tool_manifest.py validate`, PAP conformance, security review schemas, and code graph impact can all emit structured "doctor" reports into the same LAS Health model.

## Rollout Plan

1. Add a checked-in `doctor.config.json` for `viewer/` with telemetry-safe defaults, generated-output ignores, and no global suppressions.
2. Add `viewer` scripts:
   - `doctor`: local human scan, advisory
   - `doctor:json`: structured JSON output for LAS ingestion
   - `doctor:changed`: changed-file advisory scan
3. Add a LAS parser for React Doctor JSON reports and store bounded summaries under `.agent/reports/react-doctor/`.
4. Fix the three current error-class findings first:
   - remove or server-wrap browser-delivered admin/demo key literals
   - refactor `AdminDashboardView` prop/state sync effects
5. Fix high-volume accessibility controls next, especially icon and compact buttons in `LongTermMemoryView`, `TopologyView`, `TaskFlowView`, and `SettingsView`.
6. Split giant route components as part of Phase 67 implementation, not as a separate cosmetic refactor.
7. Add advisory CI using `millionco/react-doctor@v2` with `directory: viewer`, `scope: full`, and `blocking: none`.
8. After baseline is below an agreed threshold, switch CI to changed-file gating and block errors first, warnings later.

## Initial Acceptance Criteria

- `npm.cmd --prefix viewer run doctor:json` produces parseable JSON with no telemetry and no score upload.
- LAS report parser emits category totals, top files, and error findings without printing secret-like values.
- `.agent/agent_tasks.md` has React Doctor tasks mapped to Phase 67 or a follow-up quality gate phase.
- Existing verification still passes: `npm.cmd --prefix viewer run build`, `npm.cmd --prefix viewer run verify:ui`, `git diff --check`, and `scripts\verify.cmd`.
