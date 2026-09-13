---
tags:
  - architecture/leaf
  - frontend/dag
  - tasks/kanban
  - layer/l1
type: module_leaf
layer: L1-Ingress-and-Cockpit-Surface
module: viewer.components.TaskFlowView
file_path: viewer/src/components/TaskFlowView.tsx
sync_status: verified
---

# Module: TaskFlowView (Interactive DAG Visualizer & Execution Stepper)

## 1. Three-Line Architectural Annotation
- **Responsibility**: Interactive ReactFlow-powered canvas visualizing workflow execution DAGs, step transitions, parallel execution branches, and live node status colors.
- **Invariant**: Step state changes must animate smoothly without triggering full-canvas node re-renders or losing user pan/zoom viewport coordinates.
- **Data Flow**: Subscribes to workflow state events from `WorkflowEngine`, calculates topological node layouts using Dagre, and emits step inspection events.

---

## 2. Source Code & Symbol Mapping

**Source Location**: [`TaskFlowView.tsx`](file:///d:/GitHub/LLM-Agent-System/viewer/src/components/TaskFlowView.tsx) (520 lines)

### Symbol Table

| Symbol | Kind | Line Range | Description |
| :--- | :--- | :--- | :--- |
| `TaskFlowView` | `function` | L45-L520 | Main DAG canvas component integrating ReactFlow with custom workflow node renderers. |
| `useTaskFlowController` | `hook` | L80-L190 | Custom hook managing workflow DAG state, node selection, and playback controls. |
| `StepInspectorPanel` | `component` | L210-L290 | Side drawer displaying input JSON, output data, error stack traces, and healing attempts. |
| `DAGPlaybackControls` | `component` | L310-L360 | Play/Pause, Step-Forward, and Reset controls for workflow simulation and replay. |
| `calculateDagreLayout` | `def` | L380-L430 | Computes deterministic (x, y) node coordinates based on step dependency edges. |

---

## 3. Operational Invariants & Anti-Corruption Guardrails
1. **Viewport Persistence**: Node state updates never reset zoom or pan offsets.
2. **Cycle Highlighting**: Erroneous circular dependencies in workflow definitions are highlighted in pulsing red with warning tooltips.

---

## 4. Verification & Test Evidence
- **Build Receipt**: Vite build validated clean exit code 0.

---

## 5. Topological Linkage
- **Upstream Layer**: [[L1-Ingress-and-Cockpit-Surface]]
- **Engine Counterpart**: [[core-workflow-engine]]
- **Parent Shell**: [[viewer-app]]
