---
tags:
  - architecture/leaf
  - frontend/cockpit
  - missions/realtime
  - layer/l1
type: module_leaf
layer: L1-Ingress-and-Cockpit-Surface
module: viewer.components.MissionControlView
file_path: viewer/src/components/MissionControlView.tsx
sync_status: verified
---

# Module: MissionControlView (Real-Time Operations & Prompt Tuning Cockpit)

## 1. Three-Line Architectural Annotation
- **Responsibility**: Ingress cockpit surface allowing operators to prompt the multi-agent system, view live streaming thinking tokens, review tool proposals, and inspect run stats.
- **Invariant**: Prompt submission enforces `latest-request-wins` with auto-abort of stale prior streams; operator input cannot be submitted while backend is paused.
- **Data Flow**: Dispatches prompt mutations to backend `AgentRouter` via HTTP/WebSocket, streams incremental response tokens into local state, and triggers tool approval modals.

---

## 2. Source Code & Symbol Mapping

**Source Location**: [`MissionControlView.tsx`](file:///d:/GitHub/LLM-Agent-System/viewer/src/components/MissionControlView.tsx) (480 lines)

### Symbol Table

| Symbol | Kind | Line Range | Description |
| :--- | :--- | :--- | :--- |
| `MissionControlView` | `function` | L35-L480 | Primary cockpit view component rendering active conversation history and prompt bar. |
| `StreamingTokenFeed` | `component` | L110-L160 | Virtualized list rendering live LLM reasoning tokens with syntax highlighting. |
| `ToolApprovalCard` | `component` | L180-L240 | Interactive HITL card displaying pending tool calls with Approve / Reject action buttons. |
| `AgentTurnMetrics` | `component` | L260-L310 | Displays real-time latency, token usage counter, and estimated cost per turn. |
| `handlePromptSubmit` | `def` | L330-L380 | Validates input, updates optimistic UI, and opens streaming SSE connection. |

---

## 3. Operational Invariants & Anti-Corruption Guardrails
1. **Optimistic Rendering with Rollback**: User prompt is shown immediately; network failures roll back state with clear inline error banner.
2. **Strict Sanitization**: Rendered markdown from agent responses passes through DOMPurify to eliminate script injection.

---

## 4. Verification & Test Evidence
- **Build Receipt**: Vite production bundle verified (0 errors).

---

## 5. Topological Linkage
- **Upstream Layer**: [[L1-Ingress-and-Cockpit-Surface]]
- **Parent Shell**: [[viewer-app]]
- **Collaborating Modules**:
  - [[core-router]]
  - [[viewer-primitives]]
