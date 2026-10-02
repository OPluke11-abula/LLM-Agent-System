# Visual Reference and Moodboard Workflow

## Purpose

Create two or three concrete visual directions before major LAS Viewer UI implementation.

This workflow prevents code-first styling by forcing a Professional Design Agent to define reference rationale, palette, typography, material/depth rules, composition grammar, source constraints, and rejection criteria before a Frontend Programmer changes JSX/CSS.

## Inputs

- Current task scope from `.agent/agent_tasks.md`.
- Current art direction packet, usually `../exports/phase-71-las-viewer-art-direction-packet-2026-07-07.md`.
- Current design critique, usually `../exports/phase-67-design-critique-flow-report-2026-07-07.md`.
- Existing screenshots under `viewer/output/`.
- Relevant implementation surfaces under `viewer/src/components/` and `viewer/src/index.css`.
- Any user-provided visual preference, example, Figma file, image, or product reference.

## Procedure

1. Confirm the target surface and phase gate.
2. Read the current art direction packet and prior critique.
3. Inspect current screenshots before making visual claims.
4. Generate or collect exactly two or three candidate directions.
5. For each direction, complete the required direction card below.
6. Reject directions that copy protected brand assets, rely on generic dark-dashboard tropes, or cannot support LAS accessibility and dense operational workflows.
7. Select one recommended direction, or state that a hybrid is required.
8. Write the moodboard packet under `.agent/knowledge_base/exports/`.
9. Link the packet from `.agent/agent_tasks.md` before implementation starts.

## Required Direction Card

Each direction must include:

- Direction name
- Product promise
- Reference rationale
- Source and license notes
- Palette
- Typography posture
- Material and depth rules
- Composition grammar
- Motion rhythm
- Required visual assets
- Accessibility constraints
- Best-fit LAS surfaces
- Rejection criteria
- Implementation risk
- Screenshot acceptance notes

## Source and License Rules

- Prefer self-authored descriptions, generated assets, screenshots from the local LAS viewer, open-license references, or user-supplied references.
- Do not copy protected product screens, logos, icons, brand systems, or distinctive trade dress.
- If an external reference is used, record the source URL or local path, what principle was extracted, and what must not be copied.
- Generated assets must be stored locally with descriptive filenames and must not include copyrighted logos or recognizable protected product UI.
- Reference images are input evidence; implementation must use extracted principles, tokens, composition rules, and motion intent.

## Candidate Directions for LAS Viewer

### Direction A: Forensic Atlas

- Product promise: LAS feels like a live investigative map where tasks, agents, code impact, tests, and evidence are layered into one navigable system.
- Reference rationale: Use cartographic grids, evidence paths, proof trails, and layered terrain to turn operational complexity into a readable map.
- Source and license notes: Prefer generated abstract cartography, local screenshots, and self-authored SVG/canvas studies. Do not copy government, intelligence, GIS, or investigative product interfaces.
- Palette: obsidian field, warm graphite panels, atlas blue routes, steel cyan code impact, amber review, red block, verification green, violet memory strata.
- Typography posture: technical display titles, restrained body text, mono for refs and evidence. Avoid default-looking title rhythm.
- Material and depth rules: map substrate first, inspector rail second, records third. Depth indicates selected layer, not decoration.
- Composition grammar: one large atlas focal object, layered routes, side inspector, evidence strips, proof paths, and non-equal panel weights.
- Motion rhythm: route tracing, selected node pulse, layer reveal, proof-path progression, reduced to static layer states when motion is disabled.
- Required visual assets: atlas substrate, topology layer, verification route lines, memory strata, risk overlays.
- Accessibility constraints: color plus labels for route states, keyboard navigation through layers, reduced-motion proof path, readable mobile labels.
- Best-fit LAS surfaces: Mission Control, Intelligence Map, Governance Cockpit, Memory Manager.
- Rejection criteria: reject if it becomes generic radar, military cosplay, a flat grid background, or unreadable decorative mapping.
- Implementation risk: custom atlas visuals may grow complex; require bounded SVG/canvas primitives and screenshot tests.
- Screenshot acceptance notes: first viewport must show the atlas focal object on desktop and a simplified atlas plus next action on mobile.

### Direction B: Instrument Panel

- Product promise: LAS feels like premium technical hardware: precise controls, tactile state, and high-trust operational surfaces.
- Reference rationale: Use industrial instrumentation principles, high-quality controls, clear gauges, and physical hierarchy without copying any proprietary console.
- Source and license notes: Prefer self-authored hardware metaphors, generated neutral panel studies, and local screenshots. Do not copy avionics, automotive, or trading-terminal UI.
- Palette: graphite chassis, muted metal highlights, white/frost text, sparing blue active controls, green verified indicators, amber caution, red blocked, violet memory markers.
- Typography posture: compact technical labels, high-contrast numerals, restrained title type, mono for commands and proof refs.
- Material and depth rules: tactile controls, shallow inset regions, rim-lit active states, stronger separation between control zones and read-only evidence.
- Composition grammar: top instrument strip, central active module, right-side action/control rail, lower diagnostic bay.
- Motion rhythm: fast control feedback, state snaps, subtle gauge progress, no ambient animation.
- Required visual assets: control-state gauges, proof modules, verification meters, risk gate controls.
- Accessibility constraints: large touch targets for controls, visible focus, no state by color alone, high contrast for blocked and pending states.
- Best-fit LAS surfaces: Governance Cockpit, Settings, Admin, Command Palette, Next Action Rail.
- Rejection criteria: reject if it becomes skeuomorphic clutter, toy-like hardware, or too many equal gauges.
- Implementation risk: tactile UI can reduce density if overbuilt; reserve it for controls and risk gates.
- Screenshot acceptance notes: controls must look intentional and usable, not just bordered buttons.

### Direction C: Editorial Intelligence

- Product promise: LAS feels like a premium intelligence briefing where dense evidence becomes an authored narrative and scan path.
- Reference rationale: Use editorial hierarchy, strong sequencing, typographic contrast, and composed evidence blocks to make complex workflows easier to read.
- Source and license notes: Prefer self-authored layout studies and generated abstract editorial boards. Do not copy news, magazine, or analyst-report layouts directly.
- Palette: dark neutral canvas, frost text, off-white content zones, restrained accent routes, high-contrast risk callouts, muted memory violet and code cyan.
- Typography posture: stronger display hierarchy, refined section titles, careful body line length, mono evidence captions.
- Material and depth rules: fewer cards, more bands and composed text/image regions, clear primary/secondary narrative levels.
- Composition grammar: headline state, visual evidence strip, primary narrative column, side decision rail, progressive disclosure for details.
- Motion rhythm: section reveal, evidence focus, command palette precision, minimal decorative motion.
- Required visual assets: annotated screenshots, evidence strips, decision timelines, visual summaries of task-to-proof flow.
- Accessibility constraints: excellent text fit, clear reading order, mobile-first heading hierarchy, keyboard-friendly disclosure.
- Best-fit LAS surfaces: Intelligence Map, Task Flow, Memory Manager, reports, handoffs.
- Rejection criteria: reject if it becomes marketing/editorial fluff, hides controls, or weakens operational density.
- Implementation risk: too much narrative can slow expert operators; pair with command palette and inspector shortcuts.
- Screenshot acceptance notes: scan path must be obvious in the first viewport without explanatory helper text.

## Selection Rules

Choose one direction when:

- It clearly fits the target surface.
- It can support dense operational data.
- It has a feasible asset strategy.
- It lowers vibe-coded risk compared with the current dark cockpit.

Use a hybrid only when:

- The hybrid assigns specific roles to each direction.
- The implementation contract names where each direction applies.
- The hybrid does not collapse back into generic card/dashboard styling.

Recommended default:

- Use Direction A, Forensic Atlas, for the overall LAS Viewer identity.
- Use Direction B, Instrument Panel, for controls, governance, settings, and high-risk actions.
- Use Direction C, Editorial Intelligence, for evidence explanation, memory, and report-like surfaces.

## Moodboard Packet Output Contract

Write the packet under `.agent/knowledge_base/exports/` with:

- Goal and target surfaces
- Evidence reviewed
- Direction cards
- Recommendation
- Rejected options and why
- Source/license notes
- Assets to generate or collect
- Implementation handoff notes
- Screenshot acceptance checklist
- Open questions for user/design review

## Related Notes

- [[../exports/phase-67-design-critique-flow-report-2026-07-07]]
- [[../exports/phase-71-las-viewer-art-direction-packet-2026-07-07]]
- [[../../prompts/roles/professional_design_agent]]
