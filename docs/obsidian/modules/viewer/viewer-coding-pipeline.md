---
tags:
  - architecture/leaf
  - frontend/pipeline
  - autonomous-coding/cockpit
  - layer/l1
  - protocol/v3-8-0
type: module_leaf
layer: L1-Ingress-and-Cockpit-Surface
module: viewer.components.CodingPipelineView
file_path: viewer/src/components/CodingPipelineView.tsx
sync_status: verified
---

# Module: CodingPipelineView (Autonomous Developer Agent Cockpit)

## 1. Three-Line Architectural Annotation
- **Responsibility**: Production-grade developer cockpit orchestrating the 5-stage autonomous coding loop (`INTAKE` $\to$ `PRECHECK` $\to$ `PLAN_AND_GATE` $\to$ `ISOLATED_MUTATION` $\to$ `VERIFY_AND_EVIDENCE` $\to$ `DRAFT_PR_EXPORT` plus `SELF_HEALING`), Stop-and-Wait Human Approval Gate, Committee Consensus Debates, and verifiable Draft PR receipts.
- **Invariant**: The UI strictly enforces the Stop-and-Wait Architecture Gate (Rule 0.2), never permitting mutations without an active human approval token, and prevents async mutation races via synchronous `useRef` locks.
- **Data Flow**: Consumes REST endpoints (`/v1/pipeline/tasks`) and live WebSocket broadcasts (`/v1/pipeline/ws`) from `agent_workspace/routes/pipeline.py`, coordinating modular subcomponents in `viewer/src/components/pipeline/`.

---

## 2. Source Code & Modular Decomposition

**Source Location**: [`CodingPipelineView.tsx`](file:///d:/GitHub/LLM-Agent-System/viewer/src/components/CodingPipelineView.tsx) (386 lines)
**Modular Package**: `viewer/src/components/pipeline/` (Phase 97 extraction)

### Subcomponent & Symbol Mapping

| Symbol / Component | File Location | Line Count | Description |
| :--- | :--- | :--- | :--- |
| `CodingPipelineView` | [`CodingPipelineView.tsx`](file:///d:/GitHub/LLM-Agent-System/viewer/src/components/CodingPipelineView.tsx) | 386 lines | Root cockpit view coordinating state, WebSocket streams, task selection, and modal dialogs. |
| `PipelineHeaderBanner` | [`pipeline/PipelineHeaderBanner.tsx`](file:///d:/GitHub/LLM-Agent-System/viewer/src/components/pipeline/PipelineHeaderBanner.tsx) | 78 lines | Header banner with connection status, action buttons, benchmark trigger, and new task dispatch. |
| `PipelineStageStepper` | [`pipeline/PipelineStageStepper.tsx`](file:///d:/GitHub/LLM-Agent-System/viewer/src/components/pipeline/PipelineStageStepper.tsx) | 108 lines | Stage progress bar displaying sequential stage transitions and self-healing badges. |
| `CommitteeDebateCard` | [`pipeline/CommitteeDebateCard.tsx`](file:///d:/GitHub/LLM-Agent-System/viewer/src/components/pipeline/CommitteeDebateCard.tsx) | 165 lines | Multi-agent committee debate cards, persona critique streams, scorecards, and consensus verdicts. |
| `ApprovalGateCard` | [`pipeline/ApprovalGateCard.tsx`](file:///d:/GitHub/LLM-Agent-System/viewer/src/components/pipeline/ApprovalGateCard.tsx) | 124 lines | Stop-and-Wait human confirmation dialog requiring token validation (`PO_LUKE_TOKEN`). |
| `VerificationLadderCard` | [`pipeline/VerificationLadderCard.tsx`](file:///d:/GitHub/LLM-Agent-System/viewer/src/components/pipeline/VerificationLadderCard.tsx) | 182 lines | Tabular verification ladder displaying test commands, exit codes, output logs, and self-healing diagnostics. |
| `TasksRail` | [`pipeline/TasksRail.tsx`](file:///d:/GitHub/LLM-Agent-System/viewer/src/components/pipeline/TasksRail.tsx) | 95 lines | Lateral task selector rail with search filter, status badges, and active selection. |
| `TaskCreationModal` | [`pipeline/TaskCreationModal.tsx`](file:///d:/GitHub/LLM-Agent-System/viewer/src/components/pipeline/TaskCreationModal.tsx) | 210 lines | Dialog modal configuring requirement prompt, target repository, branch, and role parameters. |
| `BenchmarkModal` | [`pipeline/BenchmarkModal.tsx`](file:///d:/GitHub/LLM-Agent-System/viewer/src/components/pipeline/BenchmarkModal.tsx) | 145 lines | Golden benchmark execution runner, displaying KPI scorecards across the 3 canonical benchmark scenarios. |
| `types.ts` | [`pipeline/types.ts`](file:///d:/GitHub/LLM-Agent-System/viewer/src/components/pipeline/types.ts) | 65 lines | Decoupled TypeScript interfaces for pipeline stages, tasks, receipts, and committee deliberation. |

---

## 3. Operational Invariants & Anti-Corruption Guardrails
1. **Stop-and-Wait Gate UI Enforcement**: Unapproved plans present an amber badge and disable execution trigger buttons until human validation is confirmed.
2. **Synchronous Re-entry Protection**: Mutating actions use synchronous React `useRef` locks to eliminate multi-click race conditions.
3. **Lifecycle Unmount Guarding**: Uses `AbortController` and `isSubscribed` flag to cleanly terminate in-flight HTTP requests and avoid unmounted state updates.
4. **HMR Fast Refresh Compliance**: Shared utility functions (`Tone`, `cx`, `toneForStatus`) are isolated in `viewer/src/components/ui/utils.ts`, ensuring components export only React entities.

---

## 4. Verification & Test Evidence
- **Build Receipt**: Rolldown/Vite production build succeeded in 785ms with 0 errors (`npm run build` in `viewer/`).
- **React Doctor Scorecard**: 0 Bugs, 0 Performance regressions, 0 Accessibility violations.
- **UI Smoke & Swarm Verification**: `npm run verify:ui` and `npm run test:swarm-ui` PASS.
- **API Parity**: Verified with FastAPI backend router `routes/pipeline.py` and `test_pipeline_api_p3.py` (6/6 tests PASS).

---

## 5. Topological Linkage
- **Upstream Layer**: [[L1-Ingress-and-Cockpit-Surface]]
- **Backend Controller**: [[core-pipeline]]
- **Parent Shell**: [[viewer-app]]
- **Protocol Baseline**: [[70 Multi-Agent Protocol v3.8.0 & 10 Grounded Roles Matrix]]
