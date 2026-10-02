# Phase 71 LAS Viewer Art Direction Packet

## Purpose

This packet completes Phase 71-02. It gives LAS Viewer a reusable design brief and art direction before further major UI implementation. It responds to the Phase 67 design critique: the current viewer is coherent and functional, but still feels too code-first because its premium quality depends on dark cockpit patterns, glass cards, grids, and status badges instead of a professional visual thesis.

This packet is design-first. It is not an implementation contract and does not authorize broad JSX/CSS changes by itself. Phase 71-05 should translate the approved direction into `viewer/DESIGN.md`, tokens, primitives, and screenshot acceptance criteria.

## Audience

Primary users:

- Human operators supervising multi-agent work.
- Developers reviewing task state, evidence, code impact, and verification.
- Security or governance reviewers checking risk gates, proof paths, and blocked operations.
- Future design and frontend agents that need a shared visual target before building.

Usage posture:

- The user is not browsing a marketing product. They are steering a live operational system.
- They need fast orientation, high trust, clear next action, and visual evidence that the system is advanced without becoming noisy.
- They should feel that LAS is a professional command instrument, not a dashboard assembled from components.

## Emotional Target

The viewer should feel:

- Advanced: more like an intelligence instrument than an admin panel.
- Calm under pressure: dense but not frantic.
- Precise: every visual layer should explain system state.
- Premium: art-directed material, hierarchy, and motion, not generic decoration.
- Trustworthy: blocked, safe, risky, verified, and uncertain states are visually distinct and auditable.

The viewer should not feel:

- Like a generic dark SaaS dashboard.
- Like a sci-fi skin over ordinary cards.
- Like a pile of unrelated panels.
- Like a code demo using whatever token classes were convenient.

## Product Metaphor

Approved metaphor: Cognitive Operations Atlas.

LAS is a living map of agent cognition and execution. Agents, tasks, memory, governance, code impact, and evidence are layers in one navigable atlas. The user is not just reading metrics; they are navigating a system landscape.

Core object: the Atlas.

- Mission Control shows the global atlas.
- Task Flow shows the execution terrain.
- Intelligence Map shows evidence and code-impact layers.
- Governance Cockpit shows risk gates and proof trails.
- Memory Manager shows memory strata and provenance.
- Settings and Admin tune the instrument, not decorate the product.

Memorable moment:

The first viewport should expose a high-fidelity system map with layered signals: active mission, agent topology, verification beams, memory strata, risk overlays, and next action. Even with no live topology, the empty state should still look like an intentional atlas waiting for signal.

## Visual Personality

Direction name: Refined Technical Cartography.

Characteristics:

- Cartographic, not spaceship.
- Precision instrument, not neon arcade.
- Dense evidence layers, not decorative panels.
- Editorial hierarchy, not equal-weight cards.
- Quiet luxury through material control, not loud gradients.

Design adjectives:

- Layered
- Measured
- Tactile
- Instrumented
- Cartographic
- Forensic
- Composed

Rejected adjectives:

- Glowy
- Cyberpunk
- Gamer
- Marketing
- Widgety
- Randomly futuristic
- One-note dark blue

## Typography Posture

Current system-stack typography is operationally safe but not distinctive enough for the premium target.

Recommended posture:

- Display: a restrained technical display face or custom-feeling uppercase treatment for page titles, atlas labels, and major state captions.
- Body: highly legible UI text that can survive dense tables, paths, and multilingual copy.
- Mono: keep mono for IDs, paths, command previews, evidence refs, hashes, and status telemetry.

Implementation notes for later phases:

- Do not globally switch fonts until performance, licensing, and multilingual rendering are checked.
- If external fonts are used, they must be self-hosted or explicitly licensed.
- The first improvement can be typographic hierarchy without changing font files: tighter title rhythm, stronger scale contrast, fewer all-caps labels, and clearer number treatment.

Acceptance criteria:

- Titles feel authored, not default.
- Dense labels remain readable at 390px mobile width.
- Numeric telemetry has consistent alignment and visual weight.
- Long paths and commands remain scannable with truncation and tooltips.

## Color Story

Current colors are too close to a generic dark cockpit. Keep dark operation mode, but shift the palette toward cartographic signal layers.

Base palette:

- Obsidian field: near-black background for long-session comfort.
- Graphite panels: dark neutral surfaces with slight warmth, avoiding flat navy.
- Frost text: high-legibility primary text, muted secondary text.

Signal palette:

- Atlas blue: active navigation, selected layer, current route.
- Verification green: passed checks, evidence-backed state.
- Amber review: uncertainty, pending approval, cost or policy review.
- Red block: blocked, revoked, failed proof, unsafe action.
- Violet memory: memory strata, prior decisions, semantic links.
- Steel cyan: code graph and structural intelligence.

Rules:

- Do not let blue/violet dominate every surface.
- Use color as layer identity and state semantics, not decoration.
- Every risky state must have text and shape semantics, not only color.
- Avoid purple-blue gradients as the main brand look.

## Material Language

The material should feel like layered technical glass over a map substrate, but the current card-heavy approach needs restraint.

Use:

- Full-width map regions for primary surfaces.
- Thin layer boundaries for evidence, topology, and proof paths.
- Inspector rails for selected objects and next actions.
- Compact chips for states, not as the primary visual language.
- Subtle depth only when it explains focus or layering.

Avoid:

- Cards inside cards.
- Every panel having the same radius, border, and shadow.
- Decorative glow without operational meaning.
- Empty dark space that is not intentionally composed.

Material hierarchy:

1. Atlas substrate: background map/grid/terrain.
2. Primary focus object: topology, task terrain, proof trail, or memory strata.
3. Inspector rail: selected item, next action, evidence.
4. Repeated records: tasks, gates, refs, findings.
5. Transient command layer: command palette and overlays.

## Density Model

LAS should stay dense because the product is operational. The issue is not density; it is undifferentiated density.

Density rules:

- One focal object above the fold.
- One primary next action visible without searching.
- Secondary metrics grouped by role, not spread evenly as decorative KPI cards.
- Evidence and refs should be compact, but not compete with the main map.
- Mobile should show one decisive action and one focal state first, then supporting metrics.

Screen density targets:

- Mission Control: medium-high density, one atlas object dominates.
- Task Flow: high density, execution terrain plus inspector.
- Intelligence Map: medium density, layered evidence path.
- Governance Cockpit: high density, but risk hierarchy must dominate.
- Memory Manager: medium density, provenance and strata over raw lists.
- Settings: low-medium density, configuration clarity over spectacle.

## Motion Rhythm

Motion should make the atlas feel alive, not flashy.

Approved motion:

- Layer reveal when entering a surface.
- Selected node focus pulse with reduced-motion fallback.
- Proof path progression for governance verification.
- Subtle route tracing between task, code impact, tests, and evidence.
- Command palette should feel instant and precise, not theatrical.

Rejected motion:

- Constant ambient glow.
- Layout-shifting animations.
- Decorative particles or generic bokeh.
- Motion that hides state changes or delays operation.

Reduced-motion rule:

- All motion must degrade to opacity, border, or static state changes.
- Verification and risk state cannot depend on animation.

## Screen Hierarchy

### Mission Control

Primary job: show the global atlas and the next best action.

Required hierarchy:

1. Atlas object: live system map or intentional empty atlas.
2. Active mission and next action.
3. Verification/risk/memory summary.
4. Recent trace and evidence.

Design note: the current first viewport gives too much equal weight to hero metrics, radar, mission card, and action rail. The atlas must become the remembered object.

### Task Flow

Primary job: turn tasks into execution terrain.

Required hierarchy:

1. Current executable path.
2. Dependency terrain.
3. Selected task inspector.
4. Timeline and filters.
5. Export and secondary actions.

Design note: the task timeline, graph, and inspector should feel like one designed workspace, not separate panels.

### Intelligence Map

Primary job: reveal why a task matters and what it touches.

Required hierarchy:

1. Current task context.
2. Code impact layer.
3. Linked tests and evidence.
4. Prior decisions and memory links.

Design note: make the inspection flow feel like traversing layers of evidence.

### Governance Cockpit

Primary job: make risk and permission state impossible to misread.

Required hierarchy:

1. Overall posture: safe, review required, blocked.
2. Approval gate matrix.
3. Proof path and audit trail.
4. Findings and revoked certificates.
5. Peer and billing details.

Design note: blocked state needs stronger visual grammar than red badges. Use structure, grouping, and proof-path emphasis.

### Memory Manager

Primary job: show memory provenance and trust.

Required hierarchy:

1. Memory strata: ephemeral, session, persistent, shared.
2. Evidence provenance.
3. Recent claims and verification status.
4. Query and maintenance actions.

Design note: memory should look like layered strata, not a generic list.

### Settings and Admin

Primary job: tune the instrument.

Required hierarchy:

1. Current configuration state.
2. Risk-bearing controls.
3. Environment and integration status.
4. Advanced settings.

Design note: avoid making settings look as visually important as Mission Control.

## Visual Asset Strategy

Required focal assets:

- Atlas substrate: generated or authored background map language for Mission Control.
- Topology layer: SVG/canvas or React-rendered map object for agents, routes, and statuses.
- Execution terrain: task dependency path with terrain-like composition.
- Proof trail: governance path visualization for audit and proof checks.
- Memory strata: layered visual metaphor for memory tier and provenance.

Asset rules:

- Prefer generated bitmap or authored SVG/canvas only when it communicates product state.
- Store local assets with explicit names and alt/aria descriptions.
- Do not use protected brand imagery or copied UI compositions.
- Every visual asset must have a reduced/empty/loading state.
- Screenshot QA must capture at least one desktop and one mobile view for each major focal asset.

## UX Convenience Principles

The premium UX goal is not only beauty. It should feel unusually convenient.

Required UX behaviors:

- One command palette path to every primary workflow.
- One next-action rail that explains expected result and failure follow-up.
- One-click movement from task to affected code, tests, evidence, and prior decision.
- Risk state visible before any external-state action.
- Handoff and verification commands visible where the user needs them.
- Empty states that offer the next useful action, not only explanation.

## Acceptance Criteria for Future Implementation

Before Phase 67 can close cleanly, the implemented viewer should satisfy:

- The first viewport has one memorable atlas focal object.
- The major surfaces no longer feel like interchangeable dark card clusters.
- Each surface has a distinct role in the Cognitive Operations Atlas.
- Visual assets or authored diagrams exist for the primary focal objects.
- Mobile first impression is command-first and not a cramped desktop copy.
- Status semantics are accessible through text, shape, grouping, and color.
- Screenshot QA captures prove desktop and mobile composition.
- Design review scores "vibe-coded risk" as low or documents remaining tasks.

## Open Questions for Phase 71-03

Phase 71-03 should explore two or three concrete visual reference directions. Suggested candidates:

- Direction A: Forensic Atlas, restrained cartography and proof trails.
- Direction B: Instrument Panel, luxury technical hardware and tactile controls.
- Direction C: Editorial Intelligence, magazine-like hierarchy over dense evidence.

Phase 71-03 should choose, combine, or reject these with visual references and rejection criteria.

## Changed On Disk

- Added this art direction packet.

## Verification Notes

- This packet was based on `.agent/knowledge_base/exports/phase-67-design-critique-flow-report-2026-07-07.md`, `viewer/DESIGN.md`, Phase 71 task scope, and existing Phase 67 screenshot evidence.
- No runtime UI code changed.
- Full viewer build and screenshot regeneration are not required for this design-only packet.
