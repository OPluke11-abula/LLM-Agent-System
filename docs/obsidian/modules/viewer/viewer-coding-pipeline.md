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
- **Responsibility**: Production-grade developer cockpit visualizing the 5-stage autonomous coding loop (`INTAKE` $\to$ `PRECHECK` $\to$ `PLAN_AND_GATE` $\to$ `ISOLATED_MUTATION` $\to$ `VERIFY_AND_EVIDENCE` $\to$ `DRAFT_PR_EXPORT`), Stop-and-Wait Human Approval Modal, Merkle root audit trail, and verifiable Draft PR receipts.
- **Invariant**: The UI must physically enforce the Stop-and-Wait Architecture Gate (Rule 0.2), never allowing mutation execution without an active approval token or human confirmation.
- **Data Flow**: Consumes REST endpoints (`/v1/pipeline/tasks`) and live WebSocket broadcasts (`/v1/pipeline/ws`) from `agent_workspace/routes/pipeline.py`, displaying real-time stage transitions, ladder execution logs, and Merkle root calculations.

---

## 2. Source Code & Symbol Mapping

**Source Location**: [`CodingPipelineView.tsx`](file:///d:/GitHub/LLM-Agent-System/viewer/src/components/CodingPipelineView.tsx) (480 lines)

### Symbol Table

| Symbol | Kind | Line Range | Description |
| :--- | :--- | :--- | :--- |
| `STAGE_CONFIG` | `constant` | L25-L65 | Visual metadata dictionary (names, icons, color badges) for each `PipelineStage`. |
| `CodingPipelineView` | `function` | L70-L480 | Root cockpit view orchestrating stage stepper, task intake form, approval modal, and receipt cards. |
| `StageStepper` | `component` | L120-L180 | 5-stage interactive progress bar displaying current, pending, and completed pipeline stages. |
| `ApprovalGateModal` | `component` | L200-L260 | Stop-and-Wait human confirmation dialog requiring approval token input to unlock execution. |
| `VerificationLadderTable` | `component` | L280-L340 | Tabular receipt ledger listing test commands, exit codes, durations, and output logs. |
| `AuditAndPreservationPanel` | `component` | L360-L420 | Merkle tree root hash card and host checkout preservation status indicator. |
| `DraftPRPreview` | `component` | L430-L475 | Markdown preview of the generated GitHub Draft PR, commit SHA, and offline patch bundle fallback. |

---

## 3. Operational Invariants & Anti-Corruption Guardrails
1. **Stop-and-Wait Gate UI Enforcement**: Unapproved plans present an explicit amber badge and block execution trigger buttons until approved.
2. **Fail-Fast Error Surfacing**: Test ladder failures immediately display the exact command, exit code, and root-cause diagnostic message.
3. **Canonical Host Preservation Transparency**: Displays `CanonicalPreservationReceipt` state confirming zero uncommitted host mutations.

---

## 4. Verification & Test Evidence
- **Build Receipt**: Vite production build succeeded in 668ms with 0 errors/warnings (`npm run build` in `viewer/`).
- **API Parity**: Verified with FastAPI backend router `routes/pipeline.py` and `test_pipeline_api_p3.py` (6/6 tests PASS).

---

## 5. Topological Linkage
- **Upstream Layer**: [[L1-Ingress-and-Cockpit-Surface]]
- **Backend Controller**: [[core-pipeline]]
- **Parent Shell**: [[viewer-app]]
- **Protocol Baseline**: [[70 Multi-Agent Protocol v3.8.0 & 10 Grounded Roles Matrix]]
