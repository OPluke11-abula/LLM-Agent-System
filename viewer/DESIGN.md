# LAS Viewer Design Contract

## 1. Product Frame

LAS Viewer is an operational command instrument for agent work: tasks, topology, memory, governance, verification, code impact, and evidence. The UI must feel dense, inspectable, advanced, and trustworthy without becoming decorative or marketing-oriented.

The Phase 71 design direction is `Cognitive Operations Atlas`: LAS is a living map of agent cognition and execution. Agents, tasks, memory, governance, code impact, and evidence are layers in one navigable atlas. The user should feel they are steering a professional system, not browsing a generic dark dashboard.

## 2. Visual Direction

Approved visual personality: `Refined Technical Cartography`.

The product should feel:

- Cartographic, not spaceship.
- A precision instrument, not a neon console.
- Layered with evidence, not packed with interchangeable cards.
- Premium through hierarchy, material discipline, and authored focal objects.
- Operationally calm even when risk or failure is present.

Rejected defaults:

- Generic dark SaaS dashboard.
- Blue/purple gradient AI dashboard.
- Equal-weight metric-card grids.
- Decorative glow, bokeh, or ambient motion without state meaning.
- Cards inside cards as the default layout strategy.

## 3. Surface Roles

Each major route must own a distinct composition role.

- Mission Control: global atlas and next action.
- Task Flow: execution terrain and selected-task inspector.
- Intelligence Map: evidence traversal from task to code impact, tests, evidence, and decisions.
- Governance Cockpit: risk gate matrix and proof trail.
- Memory Manager: memory strata, trust, provenance, and citations.
- Settings: instrument tuning and risk-bearing configuration.
- Admin: high-risk operational instrument bay.

No two surfaces should use the same "hero plus metric cards plus panels" layout without a distinct focal object.

## 4. Token Roles

All raw colors still belong in `src/index.css`, but new tokens should be named by product role, not only by generic hue.

Required token roles:

- Atlas substrate: background map field and terrain layers.
- Atlas route: active route, selected path, and graph traversal.
- Code impact: structural/code graph layer.
- Memory: memory strata and prior-decision layer.
- Proof: cryptographic proof trail and audit path.
- Verification: passed checks and evidence-backed state.
- Review: uncertain, pending, cost, or approval-review state.
- Blocked: failed, revoked, unsafe, or externally blocked state.
- Instrument control: settings, admin controls, command palette, and next-action controls.
- Inspector: selected object, evidence rail, and action rail surfaces.

Current generic tokens may remain as implementation substrate:

- Backgrounds: `--bg-base`, `--bg-panel`, `--bg-card`, `--bg-elevated`, `--bg-muted`, `--bg-glass`.
- Borders and focus: `--border-c`, `--border-strong`, `--border-rim`, `--ring`.
- Text: `--t1`, `--t2`, `--t3`.
- Status and accents: `--accent`, `--accent-strong`, `--accent-bg`, `--signal-violet`, `--success`, `--success-bg`, `--warning`, `--warning-bg`, `--danger`, `--danger-bg`.
- Shape and depth: `--radius-panel`, `--radius-card`, `--shadow-soft`, `--shadow-card`.

Raw colors are allowed only inside global token definitions or legacy animation recipes. New components should use variables, `color-mix()`, and existing spacing utilities.

## 5. Typography Contract

The current system stack is acceptable as a safe baseline, but future Phase 71 implementation should improve typography hierarchy before changing font files.

Rules:

- Display text should feel authored, not default.
- Body text must remain readable in dense, multilingual operational views.
- Mono text is reserved for IDs, paths, commands, hashes, proof refs, and telemetry.
- Use fewer all-caps labels; keep them for scan sections, atlas layers, and compact state captions.
- Numeric telemetry needs consistent alignment and clear weight.
- Long paths and commands must truncate predictably and expose full content through title, tooltip, inspector, or copy action.

External or custom fonts require explicit licensing, self-hosting, performance review, and multilingual rendering checks.

## 6. Layout Grids

Use an `Atlas plus instrument rail` composition model.

Desktop:

- Primary visual object takes the dominant region.
- Inspector or next-action rail is attached to the selected object.
- Metrics are grouped by meaning, not scattered as decoration.
- Repeated records can use cards; page sections should be bands, maps, rails, or regions.

Tablet:

- Primary object moves above or remains first in reading order.
- Inspector rail becomes a second row or collapsible panel.
- Timeline/filter controls condense before evidence rows.

Mobile:

- First viewport must show one focal state and one useful action.
- Avoid compressing desktop navigation, hero, metrics, and panels into the same mobile fold.
- Secondary metrics, evidence, and settings must collapse behind clear disclosure or follow the focal state.

## 7. Material And Elevation Recipes

Use material depth to explain layering and focus.

Approved material roles:

- Atlas substrate: map/grid/terrain field. It can be SVG, canvas, CSS, or generated bitmap when it communicates state.
- Primary focus object: topology, execution terrain, proof trail, memory strata, or operation canvas.
- Inspector rail: selected object, next action, evidence, and commands.
- Repeated record: task, finding, proof ref, code ref, memory record, or tenant row.
- Instrument control: command palette, settings controls, admin high-risk controls.

Rules:

- Do not put UI cards inside larger decorative cards.
- Avoid identical radius, border, and shadow on every surface.
- Depth should indicate selection, modality, proof state, or layer order.
- Empty states must be designed objects, not blank dark rectangles.
- Decorative glow is allowed only when it maps to live, selected, blocked, or verification state.

## 8. Core Primitives

Existing primitives remain valid:

- `Surface`: generic shell for bounded regions.
- `MetricTile`: compact metric tile.
- `StatusBadge`: compact state marker.
- `primary-button` and `quiet-button`: command links and low-friction navigation.

Phase 71 implementation should add or derive these design primitives:

- `AtlasSubstrate`: base map field for Mission Control and atlas surfaces.
- `ExecutionTerrain`: task dependency map with current path, blockers, and verification markers.
- `EvidencePath`: task-to-code-to-test-to-evidence-to-decision traversal.
- `ProofTrail`: governance proof path and audit verification route.
- `MemoryStrata`: memory tiers, provenance, confidence, and citation layers.
- `InstrumentRail`: selected-object inspector, next action, or high-risk control rail.
- `RiskGateMatrix`: safe/review/blocked gate structure with non-color semantics.

These names describe design roles; implementation can use React components, CSS classes, or existing primitives where appropriate.

## 9. Iconography And Controls

Controls should use familiar interaction models:

- Icons for tools and compact commands.
- Segmented controls for modes.
- Toggles or checkboxes for binary settings.
- Inputs, sliders, or steppers for numeric values.
- Menus for option sets.
- Tabs for alternate views.
- Text buttons only for clear commands.

Avoid emoji as operational iconography. If lucide or another icon set is already available in the route, use it consistently. Unfamiliar icons need accessible names and hover/focus descriptions.

## 10. State Variants

Every major primitive must define these states:

- Loading
- Empty
- Live
- Selected
- Hover
- Focus
- Disabled
- Safe
- Review required
- Blocked
- Error
- Offline
- Reduced motion

Risk states must be communicated through text, shape, grouping, and color. Color alone is not sufficient.

## 11. Motion Contract

Motion should make the atlas feel alive and legible.

Approved motion:

- Layer reveal when entering a surface.
- Selected node focus pulse with reduced-motion fallback.
- Proof path progression for governance verification.
- Route tracing between task, code impact, tests, evidence, and decisions.
- Fast command palette and control feedback.

Rejected motion:

- Constant ambient animation.
- Decorative particles, bokeh, or background movement.
- Layout-shifting animation.
- Motion that hides or delays state updates.

Reduced-motion behavior must preserve state comprehension through static opacity, border, text, and grouping changes.

## 12. Route Composition Contracts

### Mission Control

Focal object: global atlas.

Hierarchy:

1. Atlas object with topology, active mission route, verification beams, memory strata, and risk overlays.
2. Active mission and next best action.
3. Grouped posture metrics.
4. Trace and evidence preview.

Desktop: atlas dominates first viewport with inspector/action rail attached.

Mobile: compact atlas strip first, next action second, metrics below.

### Task Flow

Focal object: execution terrain.

Hierarchy:

1. Current executable path and blocker state.
2. Dependency terrain.
3. Selected task inspector.
4. Timeline and filters.
5. Export and secondary actions.

Mobile: current task first, dependency mini-map second, inspector sections behind disclosure.

### Intelligence Map

Focal object: evidence path.

Hierarchy:

1. Task context.
2. Code impact layer.
3. Linked tests and evidence refs.
4. React Health layer with React Doctor category counts, top affected files,
   current errors, changed-file regressions, and next fix queue from LAS parser
   output.
5. Prior decisions and memory links.

The screen should feel like traversing evidence layers, not reading equal cards.

### Governance Cockpit

Focal object: risk gate matrix plus proof trail.

Hierarchy:

1. Overall posture.
2. Approval gate matrix.
3. Proof verification path.
4. Audit ledger and findings.
5. Peer, billing, and revoked certificate details.

Blocked state must be structurally obvious before reading badges.

### Memory Manager

Focal object: memory strata.

Hierarchy:

1. Ephemeral, session, persistent, and shared memory strata.
2. Provenance and citation health.
3. Memory claims and confidence.
4. Search, filters, category tree, and maintenance actions.

Memory Manager needs fresh desktop and mobile screenshots after implementation because the Phase 67-07 screenshot set did not include it.

### Settings

Focal object: configuration state.

Hierarchy:

1. Current configuration health.
2. Risk-bearing settings: model, API key, workspace paths.
3. General preferences.
4. Advanced and low-frequency controls.

Settings should feel calmer than Mission Control and should not compete for visual identity.

### Admin

Focal object: operational instrument bay.

Hierarchy:

1. Admin posture.
2. Swarm operation canvas or active intervention module.
3. Ledger/proof validation module.
4. Tenant billing and API-key controls.
5. Governance detail or deep-link.

Controls, evidence, and high-risk actions need stronger visual separation than simple vertical stacking.

## 13. Visual Asset Contract

Use generated bitmap, authored SVG/canvas, diagrams, or Figma/mockup artifacts only when they communicate product state.

Required future assets:

- Atlas substrate and empty-state atlas.
- Topology route layer.
- Execution terrain route grammar.
- Evidence path diagram.
- Proof trail visualization.
- Memory strata diagram.
- Configuration health strip for Settings.
- Ledger/proof visual object for Admin.

Every visual asset must have:

- Local storage path or generation source.
- Accessible label or text equivalent.
- Desktop and mobile framing rules.
- Loading and empty state.
- Reduced-motion equivalent if animated.

Choose the least complex medium that preserves meaning: DOM/CSS before SVG,
SVG before canvas, and canvas before generated bitmap. Diagrams explain
relationships; screenshots prove current behavior; Figma mockups review
composition before implementation and are never runtime dependencies. Canvas
must have a synchronized semantic DOM equivalent, and raster crops must preserve
the focal object and safety-relevant state on desktop and mobile.

Production assets must be local, provenance-recorded, deterministically named,
optimized for their rendered size, and verified against a fresh build. The full
decision matrix, storage rules, accessibility contract, responsive crop gate,
optimization gate, and screenshot acceptance procedure are defined in
`.agent/knowledge_base/workflows/visual-asset-illustration-pipeline.md`.

Do not copy protected brand assets, logos, proprietary UI compositions, or distinctive trade dress.

## 14. Verification And Design QA

Before closing a major UI phase, run the relevant build/screenshot checks and perform design review.

Required evidence for implementation phases:

- `npm.cmd --prefix viewer run build`
- `npm.cmd --prefix viewer run verify:ui:screenshots`
- `git diff --check`
- route screenshots for desktop and mobile
- Memory Manager screenshot if that route changes or enters Phase 71 scope

Design review must assess:

- focal object presence
- first-viewport hierarchy
- scan path
- density control
- visual asset quality
- accessibility states
- reduced-motion behavior
- vibe-coded risk

A passing build or screenshot script is not proof of visual quality. Code-only polish cannot close a design finding when the design packet requires visual assets, composition studies, or a design review.

## 15. Source Design Artifacts

This contract is derived from:

- `.agent/knowledge_base/exports/phase-67-design-critique-flow-report-2026-07-07.md`
- `.agent/knowledge_base/exports/phase-71-las-viewer-art-direction-packet-2026-07-07.md`
- `.agent/knowledge_base/workflows/visual-reference-moodboard.md`
- `.agent/knowledge_base/workflows/visual-asset-illustration-pipeline.md`
- `.agent/knowledge_base/exports/phase-71-screen-composition-studies-2026-07-07.md`
