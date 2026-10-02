---
tags:
  - architecture/leaf
  - frontend/design_system
  - ui/primitives
  - layer/l1
type: module_leaf
layer: L1-Ingress-and-Cockpit-Surface
module: viewer.components.ui.primitives
file_path: viewer/src/components/ui/primitives.tsx
sync_status: verified
---

# Module: UIPrimitives (Design Tokens, Atoms & Micro-Interactions)

## 1. Three-Line Architectural Annotation
- **Responsibility**: Foundation UI component library providing design tokens, dark-mode surfaces, accessible primitives, and micro-interactions.
- **Invariant**: All interactive components adhere strictly to WCAG 2.1 AA accessibility standards (keyboard focusable, ARIA labelled, contrast ratio >= 4.5:1).
- **Data Flow**: Consumed across all cockpit views, binding Tailwind utility classes with Framer Motion animations.

---

## 2. Source Code & Symbol Mapping

**Source Location**: [`primitives.tsx`](file:///d:/GitHub/LLM-Agent-System/viewer/src/components/ui/primitives.tsx) (650 lines)

### Symbol Table

| Symbol | Kind | Line Range | Description |
| :--- | :--- | :--- | :--- |
| `cx` | `def` | L11-L29 | High-performance className merge utility combining conditional Tailwind classes. |
| `toneForStatus` | `def` | L31-L46 | Maps execution status strings to unified color tones (`success`, `hazard`, `warning`, `neutral`). |
| `Surface` | `component` | L48-L65 | Background panel container supporting elevation levels, borders, and backdrop blurs. |
| `Button` | `component` | L74-L102 | Accessible button supporting variants (`primary`, `secondary`, `quiet`, `hazard`). |
| `StatusBadge` | `component` | L104-L128 | Compact badge with optional animated pulse indicator for active agent states. |
| `MetricTile` | `component` | L130-L146 | KPI display card showing metric values, percentage change, and trend direction. |
| `ProgressBar` | `component` | L148-L169 | Animated progress bar with smooth CSS width transitions. |
| `Dialog` / `Modal` | `component` | L325-L375 | Radix-UI accessible modal dialog with backdrop blur and focus trap. |
| `ShimmerButton` | `component` | L466-L494 | Button component with rotating conic-gradient shimmer border animation. |
| `BentoCard` | `component` | L535-L559 | Bento-grid card container with hover highlight beam. |

---

## 3. Operational Invariants & Anti-Corruption Guardrails
1. **Zero Raw Magic Values**: Spacings, colors, and border radii strictly derive from CSS variable tokens defined in `index.css`.
2. **Animation Performance**: Transforms and opacity changes use CSS GPU acceleration (`will-change`, composited layers) to prevent frame drops.

---

## 4. Verification & Test Evidence
- **Build Receipt**: Vite build validated clean exit code 0.

---

## 5. Topological Linkage
- **Upstream Layer**: [[L1-Ingress-and-Cockpit-Surface]]
- **Used by**: All views in [[viewer-app]]
