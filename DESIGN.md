# LLM Agent System Viewer Design System

## 1. Atmosphere & Identity

The viewer is a quiet operational control plane for agent runtime inspection. It should feel dense, precise, and calm: a live systems console with enough depth to show hierarchy, but no marketing decoration. The signature is muted telemetry layering: panels, metrics, badges, and graph nodes use restrained tonal shifts, thin borders, and compact monospace labels so operators can scan repeated sessions quickly.

## 2. Color

### Palette

| Role | Token | Dark | Light | Usage |
|------|-------|------|-------|-------|
| Surface/base | `--bg-base` | `#0b0d12` | `#f6f7f9` | App background and topology canvas base |
| Surface/panel | `--bg-panel` | `rgba(18, 21, 29, 0.96)` | `rgba(255, 255, 255, 0.96)` | Large operational panels and control surfaces |
| Surface/card | `--bg-card` | `rgba(25, 29, 39, 0.92)` | `rgba(250, 251, 253, 0.95)` | Cards, metric tiles, compact modules |
| Surface/elevated | `--bg-elevated` | `rgba(32, 37, 49, 0.96)` | `#ffffff` | Hovered cards, popovers, focused fields |
| Surface/muted | `--bg-muted` | `rgba(255, 255, 255, 0.035)` | `rgba(12, 18, 31, 0.035)` | Quiet inactive states |
| Border/default | `--border-c` | `rgba(151, 164, 188, 0.16)` | `rgba(33, 43, 64, 0.12)` | Default panel, card, and node boundaries |
| Border/strong | `--border-strong` | `rgba(188, 199, 217, 0.28)` | `rgba(33, 43, 64, 0.2)` | Hover and selected boundaries |
| Text/primary | `--t1` | `#f4f7fb` | `#111827` | Main labels and values |
| Text/secondary | `--t2` | `#aab4c4` | `#536173` | Supporting text and row values |
| Text/tertiary | `--t3` | `#687386` | `#8a95a5` | Captions, metadata, disabled copy |
| Accent | `--accent` | `#8fb7ff` | `#3b6fd8` | Active route, selected trace, focus color |
| Accent/strong | `--accent-strong` | `#b8ceff` | `#274da1` | Primary button and strong action text |
| Accent/background | `--accent-bg` | `rgba(143, 183, 255, 0.12)` | `rgba(59, 111, 216, 0.1)` | Accent badges and buttons |
| Status/success | `--success` | `#7ed7a6` | `#2e9460` | Allowed, connected, healthy, complete |
| Status/warning | `--warning` | `#e7bf78` | `#a96f1f` | Review, pending, optimizing |
| Status/danger | `--danger` | `#ef8e8e` | `#bd4b4b` | Failed, blocked, tampered |
| Grid | `--grid` | `rgba(180, 194, 218, 0.055)` | `rgba(26, 36, 58, 0.045)` | Topology background grid |

### Rules

- Use existing CSS variables from `viewer/src/index.css`; do not add raw color values in component code.
- Status color is semantic only. Do not use success, warning, or danger for decoration.
- Theme variants may override existing tokens, but components must consume the same token names.

## 3. Typography

### Scale

| Level | Size | Weight | Line Height | Tracking | Usage |
|-------|------|--------|-------------|----------|-------|
| Page title | 24-32px | 700 | 1.2 | 0 | View headers |
| Section title | 14-18px | 700 | 1.35 | 0 | Panel headings |
| Body | 12-14px | 400-600 | 1.45 | 0 | Operational text |
| Caption | 10-11px | 600 | 1.35 | 0.08-0.14em | Uppercase labels |
| Micro metric | 8-10px | 700 | 1.3 | 0.10-0.14em | Dense trace labels and badges |

### Font Stack

- Primary: `-apple-system`, `BlinkMacSystemFont`, `SF Pro Display`, `SF Pro Text`, `Segoe UI`, `sans-serif`
- Mono: browser monospace via Tailwind `font-mono`

### Rules

- Keep operational panels compact; micro labels are acceptable only inside dense telemetry surfaces.
- Avoid new font families unless the whole viewer typography system is intentionally revised.

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

### Rules

- Do not put cards inside cards unless the child is a repeated metric tile.
- Use bounded scroll areas for variable-length refs and traces.

## 5. Components

### Surface
- **Structure**: shared `Surface` primitive wrapping a `div`, `section`, or `aside`.
- **Variants**: `card-bg` default and `control-surface` elevated.
- **Spacing**: caller applies `p-3` or `p-4` based on density.
- **States**: hover border strengthening is built into `card-bg`.
- **Accessibility**: content order must remain logical; use semantic `section` when the surface is a standalone region.
- **Motion**: transform and shadow transition at 180ms.

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
| Micro | 160-180ms | ease | Button, card, node hover |
| Standard | 250-320ms | ease | Progress and route transitions |
| Ambient | 1.4-2.2s | cubic-bezier(0.4, 0, 0.2, 1) | Active status pulse only |

Rules:

- Animate only `transform`, `opacity`, `box-shadow`, color, or progress width.
- Respect `prefers-reduced-motion` through the global reduced-motion rule in `viewer/src/index.css`.
- Do not add attention pulses for informational-only metadata.

## 7. Depth & Surface

### Strategy

Mixed tonal-shift plus restrained shadows.

| Level | Token | Usage |
|-------|-------|-------|
| Soft | `--shadow-soft` | Large panels and control surfaces |
| Card | `--shadow-card` | Cards, nodes, metric tiles |
| Focus | `--ring` | Keyboard focus and selected nodes |

Rules:

- Preserve 8px card radius and 14px panel radius from `--radius-card` and `--radius-panel`.
- Use borders plus tonal shifts before introducing new shadows.
- New telemetry surfaces should use existing primitives and token names.
