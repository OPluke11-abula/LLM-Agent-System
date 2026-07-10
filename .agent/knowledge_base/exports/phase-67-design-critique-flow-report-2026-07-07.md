# Phase 67 Design Critique

## Scope

This report closes the professional design-agent critique portion of Phase 67-08. It reviews the current LAS Viewer Phase 67 surfaces as design evidence, not only as code output.

Reviewed evidence:

- `viewer/DESIGN.md`
- `viewer/src/components/MissionControlView.tsx`
- `viewer/src/components/TaskFlowView.tsx`
- `viewer/src/components/IntelligenceMapView.tsx`
- `viewer/src/components/SwarmGovernanceConsole.tsx`
- `viewer/src/index.css`
- `viewer/scripts/verify-ui.mjs`
- `viewer/output/ui-regression-67-07/dashboard-desktop.png`
- `viewer/output/ui-regression-67-07/dashboard-mobile.png`
- `viewer/output/ui-regression-67-07/task-flow-desktop.png`
- `viewer/output/ui-regression-67-07/governance-cockpit-desktop.png`

## Art Direction

Current direction: dark mission-control console with glass panels, fine grid texture, muted blue accent light, compact metrics, and operational status badges.

What works:

- The interface is more coherent than the earlier generic control plane.
- Mission Control, Task Flow, Intelligence Map, and Governance Cockpit now share a recognizable dark operator surface.
- The UI is dense and scannable enough for engineering operations.
- The first viewport exposes task, risk, verification, topology, and next-action signals.

What is missing:

- There is no strong visual thesis beyond "advanced dark cockpit".
- The design lacks a signature focal artifact that makes LAS memorable.
- The palette, typography, spacing, and material language feel engineered from tokens rather than art-directed from a concept.
- The current contract names a style but does not provide moodboards, reference rationale, visual composition rules, or asset direction.

Recommended art direction target: "Cognitive Operations Atlas". LAS should feel like an operator is navigating a living system map: agent topology, task flow, governance risk, memory, and verification evidence are layers of one navigable intelligence atlas. The memorable object should be a high-fidelity system map, not a set of dashboard cards.

## What Feels Vibe-Coded

1. The premium feel depends too much on generic dark UI ingredients: glass cards, grids, blue/violet accents, small uppercase labels, and glow-like borders.
2. The Mission Control hero says "Mission Control", but the central radar has no live visual richness when topology data is empty. The largest area of the first viewport becomes a quiet placeholder instead of a designed product moment.
3. Task Flow 2.0 has useful data, but the timeline, graph, and intelligence panel feel like separate widgets assembled in code. The screen does not yet have a designed composition hierarchy.
4. Governance Cockpit is operationally useful, but it visually reads as another dark card cluster. The blocked/security posture needs a stronger visual grammar than badges and bordered rows.
5. Typography is competent but generic. The system stack is reliable, but it does not create a premium identity.
6. The UI does not use meaningful visual assets, diagrams, generated imagery, or bespoke canvas/SVG language except for simple radar rings and graph lines.
7. Mobile layout is functional but cramped. The nav and hero stack preserve content, but the first impression becomes a list of controls rather than a designed mobile command surface.

## Composition Fixes

Priority fixes before further code polish:

- Replace the generic radar placeholder with a designed atlas object: layered topology rings, agent lanes, verification beams, memory strata, and risk overlays. Empty state should still look intentional.
- Give each major surface a distinct compositional role:
  - Mission Control: global live atlas and next action.
  - Task Flow: execution timeline plus dependency terrain.
  - Intelligence Map: evidence and code-impact layers.
  - Governance Cockpit: risk gate matrix and proof trail.
- Define a stronger first-viewport hierarchy. The current Mission Control screen splits attention among hero metrics, radar, active mission, and next-action rail without one unforgettable focal object.
- Use fewer repeated card containers. Let sections be full-width bands or compositional regions; reserve cards for repeated items.
- Introduce deliberate contrast between operational density and visual breathing room. Current dense panels are orderly but visually flat.
- Improve mobile choreography: collapse navigation into a command-first shell, keep one focal object above the fold, and push secondary metrics below.

## Design Packet Needed

Do not continue large UI polishing only through JSX/CSS iteration. A professional design-agent packet is required before marking Phase 67 complete.

Required packet:

- One-page product metaphor and emotional target.
- Two or three moodboard directions with rejection criteria.
- Palette and typography rationale, including why the default system stack is acceptable or what replaces it.
- Surface grammar: panels, full-width bands, map regions, inspector rails, badges, proof paths, and empty states.
- Screen-by-screen composition sketches for Mission Control, Task Flow, Intelligence Map, Governance Cockpit, Memory Manager, Settings, and Admin.
- Visual asset plan: generated bitmap, SVG/canvas, diagram, or Figma-authored mockup for each major focal object.
- Motion rhythm: page entry, atlas focus, selected node, risk escalation, command palette, reduced-motion equivalent.
- Accessibility guardrails: contrast, keyboard focus, non-color state semantics, reduced motion, text fit.

## Implementation Risks

- Risk 1: Engineering continues adding panels and badges, which increases apparent complexity but not perceived product quality.
- Risk 2: The dark cockpit style becomes a one-note palette and fails to feel modern or distinctive.
- Risk 3: Functional QA passes while aesthetic quality remains subjective and untracked.
- Risk 4: Without design artifacts, each new surface invents its own layout and the product drifts into dashboard collage.
- Risk 5: Generated or reference imagery could introduce licensing or brand-copying risk unless the packet records source constraints and extracts only principles.

## Next Design-First Tasks

1. Execute Phase 71-01 to define the `Professional Design Agent` role contract.
2. Execute Phase 71-02 to produce the LAS Viewer art direction packet.
3. Execute Phase 71-03 to create moodboard/reference directions.
4. Re-run Phase 67-08 visual QA only after the design packet exists or the user explicitly accepts the current code-first cockpit as an interim design.
5. Keep Phase 67-08 open until the design critique has either been resolved or converted into tracked Phase 71 implementation tasks.

## Changed On Disk

- Added this critique report.

## Verification Notes

- This critique used existing Phase 67-07 screenshot artifacts and source inspection.
- Full production build and screenshot regeneration were not run for this critique because no viewer runtime code changed.
- `git diff --check -- .agent/agent_tasks.md .agent/knowledge_base/exports/phase-67-design-critique-flow-report-2026-07-07.md` was run after updating the Phase 67 task note and reported no whitespace errors.
