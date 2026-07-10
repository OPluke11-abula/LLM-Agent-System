# LLM Agent System Viewer Design System

## 1. Atmosphere & Identity

The viewer is a premium AI Mission Control surface for operating LAS, not a generic admin dashboard. It should feel like an advanced agent operations cockpit: dark-mode native, sharply engineered, visually dimensional, and fast enough for repeated expert use. The first viewport must communicate that a live multi-agent system is running, being verified, and making decisions.

The signature is a live topology focal object surrounded by command-grade telemetry. Surfaces use machined dark glass, cold metal luminance steps, subtle rim light, and precise signal colors. Motion should make the system feel alive without becoming decorative: agent activity, verification state, risk gates, and memory evidence can pulse or transition; static metadata should stay calm.

Reference stack for Phase 67:

- Redesign lane: upgrade the existing React/Tauri viewer without replacing the stack.
- Premium surface lane: use layered, dimensional cockpit materials rather than flat dark panels.
- Linear-inspired product discipline: near-black native canvas, tight information hierarchy, subtle borders, command-palette ergonomics, and sparse accent use. Do not copy brand assets or make the app look like Linear directly.

The previous "quiet operational control plane" direction is now a baseline, not the target. Any Phase 67 UI work should raise visual impact while preserving operational clarity.

## 2. Color

### Palette

| Role | Token | Dark | Light | Usage |
|------|-------|------|-------|-------|
| Surface/base | `--bg-base` | `#05070b` | `#f6f7f9` | Native dark canvas and topology field |
| Surface/panel | `--bg-panel` | `rgba(12, 16, 24, 0.94)` | `rgba(255, 255, 255, 0.96)` | Large Mission Control panels |
| Surface/card | `--bg-card` | `rgba(18, 23, 33, 0.88)` | `rgba(250, 251, 253, 0.95)` | Cards, metric tiles, compact modules |
| Surface/elevated | `--bg-elevated` | `rgba(29, 36, 50, 0.96)` | `#ffffff` | Command palette, drawers, selected panels |
| Surface/muted | `--bg-muted` | `rgba(255, 255, 255, 0.035)` | `rgba(12, 18, 31, 0.035)` | Quiet inactive states |
| Surface/glass | `--bg-glass` | `rgba(10, 15, 24, 0.72)` | `rgba(255, 255, 255, 0.76)` | Fixed overlays, command palette shell, floating controls |
| Border/default | `--border-c` | `rgba(180, 196, 224, 0.13)` | `rgba(33, 43, 64, 0.12)` | Default panel, card, and node boundaries |
| Border/strong | `--border-strong` | `rgba(212, 226, 250, 0.28)` | `rgba(33, 43, 64, 0.2)` | Hover and selected boundaries |
| Border/rim | `--border-rim` | `rgba(255, 255, 255, 0.36)` | `rgba(33, 43, 64, 0.28)` | Premium rim light on featured surfaces |
| Text/primary | `--t1` | `#f7f9fd` | `#111827` | Main labels and values |
| Text/secondary | `--t2` | `#b8c3d4` | `#536173` | Supporting text and row values |
| Text/tertiary | `--t3` | `#78869b` | `#8a95a5` | Captions, metadata, disabled copy |
| Accent | `--accent` | `#78d8ff` | `#246dba` | Active route, selected trace, focus color |
| Accent/strong | `--accent-strong` | `#b7efff` | `#17487c` | Primary action text, selected topology edges |
| Accent/background | `--accent-bg` | `rgba(120, 216, 255, 0.12)` | `rgba(36, 109, 186, 0.1)` | Accent badges and command highlights |
| Signal/violet | `--signal-violet` | `#8f8cff` | `#5c56cc` | Conductor/model intelligence, not general decoration |
| Status/success | `--success` | `#64e1a3` | `#2e9460` | Allowed, connected, healthy, complete |
| Status/warning | `--warning` | `#f2c777` | `#a96f1f` | Review, pending, optimizing |
| Status/danger | `--danger` | `#ff8f9a` | `#bd4b4b` | Failed, blocked, tampered |
| Grid | `--grid` | `rgba(185, 210, 245, 0.065)` | `rgba(26, 36, 58, 0.045)` | Topology background grid |

### Rules

- Component code must consume CSS variables from `viewer/src/index.css`; do not add raw color values in React components.
- If a Phase 67 component needs `--bg-glass`, `--border-rim`, or `--signal-violet`, add the token to CSS before using it.
- Use accent colors as signals, not decoration. The dominant read should be graphite, cold metal, and luminous telemetry.
- Status color is semantic only. Do not use success, warning, or danger for decoration.
- Theme variants may override existing tokens, but components must consume the same token names.

## 3. Typography

### Scale

| Level | Size | Weight | Line Height | Tracking | Usage |
|-------|------|--------|-------------|----------|-------|
| Display cockpit | 36-56px | 620-720 | 1.0-1.08 | 0 | Mission Control first viewport only |
| Page title | 24-34px | 620-700 | 1.15 | 0 | View headers |
| Section title | 14-18px | 650-720 | 1.35 | 0 | Panel headings |
| Body | 12-14px | 400-600 | 1.45 | 0 | Operational text |
| Caption | 10-11px | 600 | 1.35 | 0.08-0.14em | Uppercase labels |
| Micro metric | 8-10px | 700 | 1.3 | 0.10-0.14em | Dense trace labels and badges |

### Font Stack

- Primary: `Geist`, `Aptos`, `SF Pro Display`, `SF Pro Text`, `Segoe UI Variable`, `Segoe UI`, `sans-serif`
- Mono: `Berkeley Mono`, `JetBrains Mono`, `SF Mono`, `ui-monospace`, `monospace`

### Rules

- Phase 67 may revise the viewer typography system, but font changes must be declared here before CSS changes.
- Display-scale text is reserved for Mission Control and major empty states. Dense panels keep compact operational type.
- Use tabular numbers for metrics, timers, costs, token counts, confidence values, and topology counters.
- Avoid default browser-looking typography. The interface should feel engineered, not generic.

## 4. Spacing & Layout

### Base Unit

All spacing maps to a 4px base through Tailwind utility steps.

| Token | Value | Usage |
|-------|-------|-------|
| `space-1` | 4px | Compact row gaps and icon gaps |
| `space-1.5` | 6px | Dense telemetry grid gaps |
| `space-2` | 8px | Panel internal grouping |
| `space-3` | 12px | Compact surface padding |
| `space-4` | 16px | Standard panel padding |
| `space-6` | 24px | Major column and card gaps |

### Grid

- Operational metric groups use 3 or 4 equal columns when values are short.
- Long refs and paths must be truncatable with a `title` attribute.
- Panel sections separate with `border-t` using `--border-c`.
- Mission Control uses an asymmetric cockpit grid: focal topology center, mission/action rail, conductor/risk inspector, and compact telemetry bands.
- Mobile and tablet layouts collapse to task-first vertical sections. The focal topology must stay readable and must not force horizontal scrolling.

### Rules

- Do not put cards inside cards unless the child is a repeated metric tile.
- Use bounded scroll areas for variable-length refs and traces.
- First viewport must show what is active, what is risky, what is verified, and what to do next.
- Repeated high-frequency commands should be reachable through the command palette, not buried in separate panels.

## 5. Components

### MissionControlShell
- **Structure**: top-level route composition with a live topology focal area, mission strip, next-action rail, and inspector region.
- **Variants**: default operations, degraded/offline, high-risk review.
- **Spacing**: asymmetric grid with stable min/max regions; no layout jump when telemetry updates.
- **States**: loading, empty workspace, disconnected stream, review required, verified.
- **Accessibility**: logical landmark order; keyboard can reach command palette, topology nodes, inspector, and action rail.
- **Motion**: route entry and topology emphasis use transform/opacity only.

### CommandPalette
- **Structure**: fixed glass shell with search input, grouped commands, recent actions, and command preview.
- **Variants**: global, scoped-to-task, scoped-to-agent, scoped-to-file.
- **Spacing**: dense but not cramped; command rows must have stable height.
- **States**: empty search, loading commands, disabled command, execution success, execution failure.
- **Accessibility**: open with keyboard, close with Escape, roving active option, visible focus, screen-reader command names.
- **Motion**: 220-320ms overlay fade and slight scale using cockpit easing.

### TaskFlowWorkspace
- **Structure**: task cockpit with a compact timeline rail, dependency graph canvas, and task intelligence inspector.
- **Variants**: default, filtered/search results, empty workspace, selected task, blocked task, ready-for-handoff task.
- **Spacing**: timeline stays compact above the graph; inspector is a bounded side panel on desktop and stacks below the graph on mobile.
- **States**: no tasks, no matches, pending, running, completed, blocked by dependency, evidence available, handoff ready.
- **Accessibility**: timeline items are buttons with explicit task names; inspector fields use text labels and do not rely on color alone.
- **Motion**: graph and timeline selection can use border/rim transitions only; no decorative looping motion.

### NextActionRail
- **Structure**: persistent contextual rail listing the highest-value next actions with expected result and command preview.
- **Variants**: verify, repair, inspect, handoff, approve, sync.
- **Spacing**: compact enough for desktop side rail; stacks below the topology on mobile.
- **States**: unavailable, ready, running, failed, completed.
- **Accessibility**: action text must explain outcome without relying on color.
- **Motion**: running actions can use restrained signal pulse; completed actions settle without repeated animation.

### IntelligenceMap
- **Structure**: linked view for structural memory, code graph impact, workflow evidence, tests, and review findings.
- **Variants**: task impact, symbol impact, security review, workflow memory.
- **Spacing**: graph area plus inspector drawer; raw evidence remains opt-in.
- **States**: no graph indexed, stale graph, impacted symbols found, tests linked, security-relevant path.
- **Accessibility**: graph nodes must have textual summaries in the inspector.
- **Motion**: edge highlight and inspector transition only; no constant decorative motion.

### Surface
- **Structure**: shared `Surface` primitive wrapping a `div`, `section`, or `aside`.
- **Variants**: `card-bg` default, `control-surface` elevated, and Phase 67 cockpit shells.
- **Spacing**: caller applies `p-3` or `p-4` based on density.
- **States**: hover border strengthening is built into `card-bg`; cockpit variants add subtle rim light on selected/active surfaces.
- **Accessibility**: content order must remain logical; use semantic `section` when the surface is a standalone region.
- **Motion**: transform, opacity, rim light, and shadow transition at 180-260ms.

### MetricTile
- **Structure**: value over uppercase label.
- **Variants**: neutral, accent, success, warning, danger tones.
- **Spacing**: `p-1` for dense trace panels, `p-2` for dashboard cards.
- **States**: static display only; no hover required.
- **Accessibility**: labels must be short and values must fit without layout shift.
- **Motion**: none.

### StatusBadge
- **Structure**: bordered inline badge with a semantic dot.
- **Variants**: neutral, accent, success, warning, danger.
- **Spacing**: internal `px-2 py-0.5`.
- **States**: static display; tone changes with status.
- **Accessibility**: visible text must not rely on color alone.
- **Motion**: none.

### ProgressBar
- **Structure**: tokenized track and fill.
- **Variants**: semantic tone via fill color.
- **Spacing**: 6px height.
- **States**: bounded 0-100%.
- **Accessibility**: pair with text when used for meaningful progress.
- **Motion**: width transition at 320ms.

## 6. Motion & Interaction

| Type | Duration | Easing | Usage |
|------|----------|--------|-------|
| Micro | 160-220ms | cubic-bezier(0.2, 0.8, 0.2, 1) | Button, card, node hover |
| Standard | 260-420ms | cubic-bezier(0.32, 0.72, 0, 1) | Command palette, drawer, route transitions |
| System signal | 900ms-1.8s | cubic-bezier(0.4, 0, 0.2, 1) | Agent activity, verification, risk transitions |
| Ambient | 1.8-3.2s | cubic-bezier(0.4, 0, 0.2, 1) | Active status pulse only |

Rules:

- Animate only `transform`, `opacity`, `box-shadow`, color, or progress width.
- Respect `prefers-reduced-motion` through the global reduced-motion rule in `viewer/src/index.css`.
- Do not add attention pulses for informational-only metadata.
- Every major interactive element needs hover, active/pressed, focus-visible, disabled, loading, and error behavior.
- Motion must explain system state. Decorative loops are design debt unless tied to live activity.

## 7. Depth & Surface

### Strategy

Machined cockpit depth: luminance stepping, translucent glass shells, thin rim borders, inset highlights, tinted shadows, and sparse glow only where a signal is active. The topology focal object and command overlays should read as dimensional materials, not flat boxes.

| Level | Token | Usage |
|-------|-------|-------|
| Soft | `--shadow-soft` | Large panels and control surfaces |
| Card | `--shadow-card` | Cards, nodes, metric tiles |
| Focus | `--ring` | Keyboard focus and selected nodes |
| Rim | `--border-rim` | Selected cockpit shells and active topology regions |

Rules:

- Preserve compact radii for dense repeated items, but allow larger cockpit shells where they frame the main experience.
- Use layered borders plus tonal shifts before introducing large shadows.
- Do not rely on a single blur to imply glass. Glass-like surfaces need tint, rim, inner highlight, and backdrop treatment.
- New telemetry surfaces should use existing primitives and token names.

## 8. Phase 67 UX Contract

### Navigation Model

- Primary mental model: Mission Control, Task Flow, Intelligence Map, Governance, Settings.
- The command palette is the fastest path for expert users and must expose the same important actions as visible navigation.
- Context inspector drawers are preferred over page jumps for task, agent, file, evidence, and risk details.

### Convenience Standard

- A user should understand the next operational step within 5 seconds of opening the app.
- High-frequency actions must be reachable in 1-2 interactions: verify, inspect failure, view impacted symbols, create handoff, sync PAP, open governance gate.
- Raw JSON, long paths, and evidence blobs stay collapsed until requested, but their summaries and counts must be visible.
- Any failed action must show the failing command or endpoint, the observed result, and the next repair action.

### Verification Standard

- Before marking Phase 67 UI work complete, run production build and browser-based visual QA.
- Required breakpoints: 375px, 768px, 1280px.
- Required states: hover, focus-visible, active/pressed, disabled, loading, empty, disconnected, error, high-risk review, verified.
- Required checks: `npm.cmd --prefix viewer run build`, `npm.cmd --prefix viewer run verify:ui:screenshots`, `git diff --check`, and `scripts\verify.cmd`.
