# Phase 71 Screen-by-Screen Composition Studies

## Purpose

This document completes Phase 71-04. It translates the `Cognitive Operations Atlas` art direction into screen-level composition studies for the LAS Viewer before implementation contracts or UI code changes.

This is a design study, not a JSX/CSS implementation plan. Phase 71-05 should convert the approved studies into `viewer/DESIGN.md`, tokens, primitives, layout grids, motion rules, and screenshot acceptance checks.

## Evidence Reviewed

- `.agent/knowledge_base/exports/phase-67-design-critique-flow-report-2026-07-07.md`
- `.agent/knowledge_base/exports/phase-71-las-viewer-art-direction-packet-2026-07-07.md`
- `.agent/knowledge_base/workflows/visual-reference-moodboard.md`
- `viewer/output/ui-regression-67-07/dashboard-desktop.png`
- `viewer/output/ui-regression-67-07/dashboard-mobile.png`
- `viewer/output/ui-regression-67-07/task-flow-desktop.png`
- `viewer/output/ui-regression-67-07/intelligence-map-desktop.png`
- `viewer/output/ui-regression-67-07/governance-cockpit-desktop.png`
- `viewer/output/ui-regression-67-07/settings-desktop.png`
- `viewer/output/ui-regression-67-07/admin-desktop.png`
- `viewer/src/components/MissionControlView.tsx`
- `viewer/src/components/TaskFlowView.tsx`
- `viewer/src/components/IntelligenceMapView.tsx`
- `viewer/src/components/SwarmGovernanceConsole.tsx`
- `viewer/src/components/LongTermMemoryView.tsx`
- `viewer/src/components/SettingsView.tsx`
- `viewer/src/components/AdminDashboardView.tsx`

Memory Manager note: no Phase 67-07 screenshot artifact exists for Memory Manager, so that study is source-informed and requires screenshot validation in later implementation QA.

## Global Composition System

Approved composition model: Atlas plus instrument rail.

- Primary surface: one dominant atlas, terrain, proof path, memory strata, or instrument object.
- Secondary surface: one inspector/action rail tied to the selected object.
- Tertiary surface: compact evidence records, metrics, filters, or configuration controls.
- Background: map substrate, not decorative grid alone.
- Cards: only repeated records, control modules, or inspector items. Avoid cards as the default page-section wrapper.

Global scan order:

1. Current state or posture.
2. Main visual object.
3. Next action or selected-object inspector.
4. Evidence and supporting metrics.
5. Secondary filters, exports, and configuration.

Mobile rule:

The mobile first viewport must show one focal state plus one useful action. It must not become a compressed desktop dashboard with navigation, hero, metric cards, and secondary panels all competing above the fold.

## Mission Control

### Role

Global live atlas and next action. This is the product's first impression and should carry the most distinctive visual identity.

### First-Viewport Hierarchy

1. Global atlas object: live topology, active mission route, verification beams, memory strata, and risk overlays.
2. Active mission summary and next best action rail.
3. System posture metrics grouped by meaning: agents, tasks, risk, verification, tokens.
4. Recent trace and evidence preview.

### Focal Object

The atlas object. It replaces the current radar placeholder as the remembered object.

Required states:

- Live topology: connected agent routes and active execution path.
- Empty topology: intentional atlas waiting for signal, not a blank placeholder.
- Risk state: risk overlay visible on the atlas, not only a badge.
- Verification state: route or beam treatment for passing/failing checks.

### Scan Path

Top-left product posture -> central atlas -> right-side active mission and next action -> lower evidence/trace preview.

### Information Density

Medium-high. The atlas should dominate about half of the desktop first viewport. Metrics should be grouped and subordinate.

### Responsive Behavior

- Desktop: atlas center-left or full-width hero band with right inspector rail.
- Tablet: atlas above, mission/action rail below in two columns.
- Mobile: compact atlas strip first, next action second, metrics folded below.

### Required Visual Assets or Diagrams

- Authored SVG/canvas atlas substrate.
- Topology route layer.
- Verification route overlay.
- Memory/risk strata overlay.
- Intentional empty-state atlas.

### Current Gap

The current desktop screenshot uses a large dark radar placeholder with equal-weight surrounding cards. It is functional but not yet a signature art-directed first impression.

## Task Flow

### Role

Execution terrain. Task Flow should show where work is, what path unlocks next, and what evidence proves progress.

### First-Viewport Hierarchy

1. Current executable path and blocker state.
2. Dependency terrain as the primary visual region.
3. Selected task inspector with owner, evidence, linked files, verification command, and handoff state.
4. Timeline and filters.
5. Export controls.

### Focal Object

Dependency terrain. It should look like an execution map, not a generic React Flow canvas plus separate timeline.

### Scan Path

Current path headline -> dependency terrain -> selected task inspector -> timeline context -> filters/export.

### Information Density

High. Expert users need density here, but density should be organized as terrain plus inspector, not equal card clusters.

### Responsive Behavior

- Desktop: terrain takes the main horizontal span, inspector pinned right.
- Tablet: terrain above, inspector below, timeline collapses to a compact horizontal strip.
- Mobile: current task card first, dependency path as scrollable mini-map, inspector details in disclosure sections.

### Required Visual Assets or Diagrams

- Execution terrain visual grammar for dependency levels.
- Current-path route highlight.
- Blocker and verification markers.
- Handoff-ready marker that is visible without opening a modal.

### Current Gap

The current screenshot has useful task timeline, graph, and intelligence panel, but they read as separate widgets. The next design pass should make them one composed workspace.

## Intelligence Map

### Role

Evidence traversal. Intelligence Map should explain why a task matters and where it touches code, tests, evidence, and decisions.

### First-Viewport Hierarchy

1. Current task context and trace availability.
2. Code impact layer.
3. Linked tests and evidence refs.
4. Prior decisions and memory links.
5. Navigation to Task Flow, Topology, or Memory.

### Focal Object

Layered evidence path from task to code impact to tests to evidence to decision.

### Scan Path

Task context -> impacted symbols -> linked tests -> evidence refs -> prior decision and action links.

### Information Density

Medium. The user should be able to understand the inspection path before seeing all records.

### Responsive Behavior

- Desktop: horizontal or diagonal evidence path with detail panels below.
- Tablet: two-column evidence path with detail cards.
- Mobile: vertical stepper with sticky task context and compact evidence counts.

### Required Visual Assets or Diagrams

- Evidence path diagram.
- Code-impact layer markers.
- Test/evidence link markers.
- Decision provenance strip.

### Current Gap

The current screenshot exposes an inspection flow, but it is still four equal cards plus record panels. It needs a stronger traversal composition so the user sees a path, not a dashboard.

## Governance Cockpit

### Role

Risk gate and proof trail. Governance must make safe, blocked, and review-required states impossible to misread.

### First-Viewport Hierarchy

1. Overall posture: safe, review required, blocked.
2. Approval gate matrix.
3. Proof verification path.
4. Audit ledger timeline.
5. Findings, revoked certificates, peer trust, and billing policy.

### Focal Object

Risk gate matrix plus proof trail. The cockpit should show why the system is blocked or safe, not just that it is blocked.

### Scan Path

Posture -> gate matrix -> proof path -> findings/revocations -> operational details.

### Information Density

High. Risk surfaces need details, but posture and gating must visually dominate.

### Responsive Behavior

- Desktop: posture banner and gate matrix left, audit/proof trail right, operational details below.
- Tablet: posture banner full-width, gate matrix, then proof trail.
- Mobile: posture first, blocking reason second, primary safe action third, details collapsed.

### Required Visual Assets or Diagrams

- Proof trail visualization.
- Gate dependency map.
- Revocation marker pattern.
- Blocked/review/safe structural states beyond badge color.

### Current Gap

The current cockpit is stronger than earlier screens but still relies on card clusters and badges. It needs a proof-path object and stronger blocked-state grammar.

## Memory Manager

### Role

Memory provenance and trust. Memory Manager should show what the system remembers, why it trusts it, and what evidence supports it.

### First-Viewport Hierarchy

1. Memory strata: ephemeral, session, persistent, shared.
2. Provenance and citation health.
3. Recent memory claims and confidence.
4. Search, filters, category tree, and maintenance actions.

### Focal Object

Memory strata diagram. The user should see memory as layered provenance, not only records.

### Scan Path

Strata overview -> selected tier/category -> record list -> provenance/citations -> maintenance action.

### Information Density

Medium. Memory is trust-sensitive; clarity beats maximum rows.

### Responsive Behavior

- Desktop: strata map left/top, records center, provenance inspector right.
- Tablet: strata summary top, records and inspector below.
- Mobile: search and selected tier first, records as compact rows, provenance in disclosure.

### Required Visual Assets or Diagrams

- Memory strata diagram.
- Citation/provenance chain.
- Confidence and expiration indicators.
- Maintenance action markers for stale or unverified memory.

### Current Gap

Source shows a conventional searchable record console with categories, domains, batch actions, citations, confidence, and expiration. It needs a visual model of memory trust and provenance. A fresh screenshot must be captured after any implementation.

## Settings

### Role

Instrument tuning. Settings should make configuration reliable and calm without competing with operational surfaces.

### First-Viewport Hierarchy

1. Current configuration state.
2. Risk-bearing settings: model, API key, workspace paths.
3. General preferences: language, theme, guide.
4. Advanced or low-frequency controls.

### Focal Object

Configuration state panel. This is not a decorative screen; it should feel like tuning the instrument.

### Scan Path

Current configuration summary -> high-risk model/API/path controls -> preferences -> guide/tutorial actions.

### Information Density

Low-medium. Settings should reduce cognitive load.

### Responsive Behavior

- Desktop: configuration summary and tabbed sections with clear grouping.
- Tablet: tabs remain, groups stack.
- Mobile: high-risk settings first, lower-risk preferences collapsed.

### Required Visual Assets or Diagrams

- No large decorative asset required.
- Optional configuration health strip.
- Clear risk markers for API key, workspace path, and model config.

### Current Gap

The current screenshot is organized but generic. It should be calmer and more clearly prioritized around risk-bearing configuration.

## Admin

### Role

Operational instrument bay. Admin contains tenant billing, swarm operation, ledger validation, HITL interception, and governance surfaces.

### First-Viewport Hierarchy

1. Admin health/posture summary.
2. Swarm operation canvas or active intervention module.
3. Ledger/proof validation module.
4. Tenant billing and API-key controls.
5. Governance cockpit or link into Governance Cockpit focus mode.

### Focal Object

Operational instrument bay. The first viewport should show the current operational risk and the active control module.

### Scan Path

Admin posture -> active operation canvas -> ledger/proof status -> high-risk controls -> governance detail.

### Information Density

High, but controls and evidence must be visually separated. The current Admin screen mixes billing, swarm, ledger, and governance vertically; stronger zones are needed.

### Responsive Behavior

- Desktop: two-zone instrument bay, operation canvas and proof module side-by-side.
- Tablet: operation canvas first, proof module second, billing below.
- Mobile: posture and current intervention first, high-risk controls behind confirmations.

### Required Visual Assets or Diagrams

- Swarm operation canvas with meaningful routes.
- Ledger/proof validation visual object.
- High-risk control confirmation pattern.
- Governance cockpit deep-link or embedded focus mode.

### Current Gap

The current screenshot is functional and dense, but it stacks multiple unrelated admin modules. It needs a clearer instrument-bay hierarchy and stronger separation between controls, evidence, and governance.

## Cross-Surface Composition Rules

- Mission Control owns the strongest visual identity.
- Task Flow owns execution terrain.
- Intelligence Map owns evidence traversal.
- Governance Cockpit owns risk/proof state.
- Memory Manager owns trust/provenance.
- Settings owns instrument tuning.
- Admin owns high-risk operation modules.

No two surfaces should use the same "hero plus metric cards plus panels" layout without a distinct focal object.

## Required Follow-Up for Phase 71-05

Phase 71-05 should convert this study into:

- Viewer design primitives for atlas substrate, terrain, proof trail, memory strata, instrument rail, and evidence path.
- Responsive grid rules for desktop, tablet, and mobile.
- Token roles for atlas, code impact, memory, proof, risk, verification, and controls.
- Screenshot QA targets for each major composition.
- A rule that code-only polish cannot close design findings without visual evidence.

## Changed On Disk

- Added this screen-by-screen composition study.

## Verification Notes

- This is a design-only artifact.
- No runtime UI code changed.
- Existing screenshots were inspected where available.
- Memory Manager requires a future screenshot because the current Phase 67-07 screenshot set does not include that route.
