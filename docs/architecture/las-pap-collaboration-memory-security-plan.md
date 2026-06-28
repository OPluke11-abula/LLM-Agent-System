# LAS/PAP Collaboration Memory and Security Workflow Adoption Plan

Date: 2026-06-28
Status: proposed plan
Source reviewed: `C:\Users\luke2\Documents\Codex\2026-06-18\codex-skills-md-antigravity\outputs\codex-ai-collaboration-memory-montage-security-research-plan-2026-06-28.md`

## Goal

Adopt the parts of the Codex collaboration, layered memory, pipeline orchestration, and security audit research that fit LAS and PAP without adding runtime hooks, daemons, remote services, or license-risky code.

The plan should extend what LAS already has:

- PAP contract-first `.agent/` workspace metadata.
- `ConductorPlan` execution telemetry.
- `routing_outcome` records in `LongTermMemoryStore`.
- `UnifiedPolicyGate` for high-impact actions.
- `AuditLedger` for tamper-evident decisions.
- `tool_manifest.py` and `pap_validate.py` for PAP parity checks.
- `scripts\verify.cmd` as the authoritative repository gate.

## Applicability Matrix

| Research idea | Apply to LAS | Apply to PAP | Decision |
|---|---:|---:|---|
| Source-of-truth order and PRD/SDD/Spec/Task/Review/Handoff gates | Yes | Yes | Adopt as lightweight workflow policy and validation targets. |
| YAML pipeline manifest with stage directors and canonical artifacts | Yes | Yes | Adapt into PAP workflow manifests under `.agent/workflows/`, not a new external pipeline engine. |
| Checkpoint JSON and resumable stages | Yes | Yes | Adopt as file-based checkpoints first, then optionally connect to `ConductorPlan`. |
| L0/L1/L2/L3 layered memory | Yes | Yes | Adapt onto existing `.agent/memory/` and `LongTermMemoryStore` record types. |
| Mermaid symbolic canvas for compressed state | Yes | Yes | Adopt as an audit view and topology bridge artifact, not as a replacement for raw evidence. |
| `node_id` / `result_ref` evidence traceability | Yes | Yes | Adopt as required fields for generated workflow and memory records. |
| Security audit Recon -> Hunt -> Validate -> Report flow | Yes | Partial | Adopt for high-risk LAS changes and PAP contract/security review gates. |
| Structured findings JSON and schema validator | Yes | Yes | Adopt with local schema and validator. |
| Parallel audit agents | Conditional | No protocol requirement | Do not enable by default; require explicit user request. |
| TencentDB OpenClaw hooks, Hermes gateway, Docker gateway | No | No | Do not adopt in LAS/PAP MVP. |
| OpenMontage code or stage text | No | No | Do not copy due AGPLv3; only reuse high-level architectural pattern. |

## Target Architecture

```text
.agent/
  agent.md
  workflows.md
  workflows/
    codex-development.yaml
  memory/
    refs/
    canvases/
    l1-atoms.jsonl
    l2-scenarios/
    l3-persona.md

docs/
  workflow/
    SOURCE_OF_TRUTH.md
    RISK_POLICY.md
    REVIEW_PROTOCOL.md
    HANDOFF_SCHEMA.md
  specs/
  tasks/
  reviews/

spec/
  workflow-stage.schema.json
  checkpoint.schema.json
  review-findings.schema.json

agent_workspace/
  workflow_lint.py
  review_findings_validate.py
```

Design constraints:

- `.agent/` remains the PAP-facing source of machine-readable workspace state.
- `docs/` holds human-readable workflow and project artifacts.
- `spec/` holds schema contracts used by validation commands.
- `agent_workspace/core/` remains for core runtime only; workflow linting and document validation stay in adapter/CLI modules.
- No hook, daemon, or automatic conversation capture is introduced in the first implementation.

## Phase 64-01: PAP Workflow Governance Scaffold

Purpose: turn the research plan into small, loadable PAP workflow rules instead of a large prompt.

Deliverables:

- `docs/workflow/SOURCE_OF_TRUTH.md`
- `docs/workflow/RISK_POLICY.md`
- `docs/workflow/REVIEW_PROTOCOL.md`
- `docs/workflow/HANDOFF_SCHEMA.md`
- `.agent/workflows.md` update that points to these files.
- README section summarizing workflow governance in English and Traditional Chinese.

Policy:

- Source of truth order starts with latest user instruction, then `.agent/agent.md`, then task spec, then docs, then code/tests.
- High-risk operations are dependency changes, migrations, auth, billing, external API side effects, secrets, pushes, deploys, and destructive filesystem actions.
- Reviewer mode validates and reports; it does not silently fix.

Acceptance criteria:

- `pap_validate.py` still accepts `.agent/agent.md`.
- `tool_manifest.py validate` still passes.
- Workflow docs are short enough to load individually by task type.
- No runtime behavior changes.

Verification:

```powershell
python agent_workspace/pap_validate.py
python agent_workspace/tool_manifest.py validate
git diff --check
```

## Phase 64-02: PAP Workflow Manifest and Checkpoint Schema

Purpose: adapt the OpenMontage-style pipeline manifest into PAP-compatible workflow definitions.

Deliverables:

- `.agent/workflows/codex-development.yaml`
- `spec/workflow-stage.schema.json`
- `spec/checkpoint.schema.json`
- `agent_workspace/workflow_lint.py`
- tests under `agent_workspace/tests/test_workflow_lint.py`

Manifest stages:

1. `repo_audit`
2. `prd`
3. `sdd`
4. `spec`
5. `task_inventory`
6. `atomic_task`
7. `review`
8. `security_gate`
9. `handoff`

Required stage fields:

- `id`
- `requires`
- `produces`
- `director_doc`
- `human_approval_required`
- `allowed_actions`
- `checkpoint_policy`
- `risk_level`

Checkpoint fields:

- `workflow_id`
- `stage_id`
- `status`
- `artifact_path`
- `artifact_hash`
- `evidence_refs`
- `started_at`
- `completed_at`
- `verifier`
- `unresolved_risks`

Acceptance criteria:

- Linter fails closed on missing required stage fields.
- Linter rejects a checkpoint whose artifact path escapes the workspace.
- Linter accepts a minimal valid workflow manifest.
- Linter does not execute stage actions.

Verification:

```powershell
.\.venv\Scripts\python.exe -m pytest --no-cov -q agent_workspace\tests\test_workflow_lint.py
python agent_workspace/workflow_lint.py --root . --workflow .agent/workflows/codex-development.yaml
```

## Phase 64-03: Evidence-Preserving Memory MVP

Purpose: map TencentDB's L0/L1/L2/L3 memory structure onto LAS without installing OpenClaw, hooks, or a daemon.

Deliverables:

- `.agent/memory/refs/` for raw evidence snippets and long command outputs.
- `.agent/memory/canvases/` for Mermaid state canvases.
- `.agent/memory/l1-atoms.jsonl`
- `.agent/memory/l2-scenarios/`
- `.agent/memory/l3-persona.md`
- Optional `agent_workspace/memory_pack.py` CLI.
- New `record_type` values in `LongTermMemoryStore` payloads:
  - `evidence_ref`
  - `workflow_atom`
  - `workflow_scenario`
  - `workflow_persona`

Rules:

- Raw evidence is never replaced by summaries.
- Every L1 atom must include `result_ref` or `source_path`.
- Every scenario must cite the atoms or refs that support it.
- L3 persona stores stable preferences only, not transient task conclusions.
- Memory packing is explicit command-driven, never automatic background capture.

Acceptance criteria:

- A long test output can be offloaded to `.agent/memory/refs/<task>.md`.
- The generated L1 atom points back to that ref.
- A generated Mermaid canvas includes node ids and ref ids.
- Existing `routing_outcome` behavior remains compatible.

Verification:

```powershell
.\.venv\Scripts\python.exe -m pytest --no-cov -q agent_workspace\tests\test_long_term_memory.py
python agent_workspace/memory_pack.py --help
git diff --check
```

## Phase 64-04: Conductor and Workflow Bridge

Purpose: connect workflow stages to `ConductorPlan` without changing provider selection or execution behavior.

Deliverables:

- `ConductorPlan.workflow_stage_id`
- `ConductorPlan.workflow_checkpoint_ref`
- `ConductorPlan.evidence_refs`
- Router telemetry update to include workflow fields when present.
- Topology bridge support for workflow-stage nodes.

Rules:

- Missing workflow metadata must not break ordinary router runs.
- Workflow metadata remains audit-only until scoring policy is explicitly added.
- Tool access continues to be the intersection of PAP-declared tools and caller allowlist.
- Ultra mode continues to require ProofOfConsensus approval through `UnifiedPolicyGate`.

Acceptance criteria:

- Existing conductor tests still pass.
- A plan can serialize workflow fields to stable JSON.
- Streamed conductor trace can include workflow refs without UI breakage.
- No provider selection changes.

Verification:

```powershell
.\.venv\Scripts\python.exe -m pytest --no-cov -q agent_workspace\tests\test_conductor_plan.py agent_workspace\tests\test_router_conductor.py
npm.cmd run build --prefix viewer
```

## Phase 64-05: Review and Security Gate Schema

Purpose: adapt the Cloudflare security-audit flow into a LAS/PAP review gate.

Deliverables:

- `spec/review-findings.schema.json`
- `agent_workspace/review_findings_validate.py`
- `docs/workflow/SECURITY_REVIEW_GATE.md`
- tests under `agent_workspace/tests/test_review_findings_validate.py`
- Optional `security_gate` workflow stage in `.agent/workflows/codex-development.yaml`

Security gate triggers:

- Auth or authorization changes.
- Secret handling changes.
- Database query or migration changes.
- External API or webhook changes.
- File parsing, upload, command execution, sandbox, or path handling changes.
- User explicitly asks for security audit.

Finding fields:

- `verdict`
- `severity`
- `category`
- `title`
- `entrypoint_trace`
- `propagation_trace`
- `sink_trace`
- `impact`
- `evidence`
- `remediation`
- `validation_status`

Rules:

- Findings require source trace and impact.
- Defense-in-depth notes are not vulnerabilities unless they have a plausible exploit path.
- No third-party exploit execution.
- No secrets in reports.
- Parallel agents are not used unless the user explicitly asks for them.

Acceptance criteria:

- Validator rejects findings with no evidence trace.
- Validator rejects `critical` or `high` findings with no impact.
- Security gate can be run as report-only.
- `UnifiedPolicyGate` can audit a `safety_scan` action as `policy_gate_decision`.

Verification:

```powershell
.\.venv\Scripts\python.exe -m pytest --no-cov -q agent_workspace\tests\test_review_findings_validate.py agent_workspace\tests\test_policy_gate.py
python agent_workspace/review_findings_validate.py --input docs/reviews/sample-security-findings.json
```

## Phase 64-06: PAP Contract Extensions

Purpose: make the workflow and memory model portable across PAP-compatible agents.

Deliverables:

- PAP schema extension proposal for:
  - workflow manifests
  - checkpoint records
  - evidence refs
  - review findings
  - memory atoms
- `.agent/skills.md` guidance for workflow-aware tools.
- `tool_manifest.py validate` extension to check workflow-sensitive tool metadata.

Candidate PAP fields:

- `workflow_id`
- `stage_id`
- `checkpoint_ref`
- `evidence_refs`
- `risk_level`
- `approval_required`
- `review_gate`
- `memory_layer`

Acceptance criteria:

- Existing PAP workspaces remain valid.
- New fields are optional unless a workflow manifest opts in.
- Runtime tools without workflow metadata still validate.
- Sensitive tools can declare review/security gate expectations.

Verification:

```powershell
python agent_workspace/tool_manifest.py validate
python agent_workspace/pap_validate.py
.\scripts\verify.cmd -SkipViewer
```

## Phase 64-07: Viewer and Operator Surface

Purpose: expose workflow state and evidence refs without turning the UI into a document reader.

Deliverables:

- Topology view workflow-stage node type.
- Conductor Trace additions for:
  - workflow stage
  - checkpoint status
  - evidence refs count
  - review/security gate status
- Admin or Activity Log panel filter for `policy_gate_decision`, workflow checkpoints, and review findings.

Rules:

- UI displays status, hashes, refs, and summaries.
- Full raw evidence remains in files and can be opened by path.
- No new decorative dashboard sections; keep control-plane layout dense and operational.

Acceptance criteria:

- Viewer build passes.
- Existing topology and conductor trace panels remain intact.
- Mock service covers workflow-stage and review-gate examples.

Verification:

```powershell
npm.cmd run build --prefix viewer
npm.cmd run verify:ui --prefix viewer
npm.cmd run test:swarm-ui --prefix viewer
```

## Non-Goals

- Do not install TencentDB/OpenClaw plugins.
- Do not patch Codex or Antigravity runtimes.
- Do not start a memory daemon.
- Do not copy OpenMontage AGPLv3 code, YAML, or skill text.
- Do not make parallel security agents the default.
- Do not make every small task go through PRD/SDD/spec gates.
- Do not replace `.agent/agent_tasks.md` with a new task tracker.

## Risk Register

| Risk | Impact | Mitigation |
|---|---|---|
| Workflow overhead slows small fixes | Agents spend more time on ceremony than code | Gate full workflow to multi-step, high-risk, or user-requested planning work. |
| Memory summaries hide real evidence | Audit conclusions become untraceable | Require `result_ref` for atoms and keep L0 evidence files. |
| PAP schema drift | Existing workspaces fail validation | Make new workflow fields opt-in and backward compatible. |
| Security findings become noisy | False positives waste engineering time | Require source trace, exploit path, impact, and validation status. |
| License contamination from OpenMontage | Legal risk | Reuse only architectural ideas; do not copy code or prose. |
| Runtime hooks alter Codex behavior | Debugging and trust problems | Keep Phase 64 file-based and command-driven. |
| UI exposes sensitive data | Secrets leak through dashboards | Show metadata keys, hashes, counts, and refs; not raw secret-bearing values. |

## Recommended Execution Order

1. Implement Phase 64-01 and 64-02 together as a document/schema/linter slice.
2. Run `scripts\verify.cmd -SkipViewer`.
3. Add Phase 64-03 memory packing only after linter behavior is stable.
4. Bridge workflow metadata into `ConductorPlan` in Phase 64-04.
5. Add review/security schema validation in Phase 64-05.
6. Propose PAP extensions in Phase 64-06 after local LAS behavior is proven.
7. Add viewer support last, after the file and schema contracts stop changing.

## Phase 64 Candidate Task Queue

```markdown
## PHASE 64 - PAP Workflow, Evidence Memory, and Review Gates

### 64-01 Workflow Governance Scaffold
- [ ] Add lightweight workflow governance docs for source-of-truth, risk policy, review protocol, and handoff schema.

### 64-02 Workflow Manifest and Linter
- [ ] Add PAP-compatible workflow manifest schema, checkpoint schema, and read-only workflow linter.

### 64-03 Evidence Memory MVP
- [ ] Add explicit memory ref packing, L1 atoms, L2 scenarios, L3 persona, and Mermaid canvas generation.

### 64-04 Conductor Workflow Bridge
- [ ] Add optional workflow stage and evidence refs to ConductorPlan telemetry without changing routing behavior.

### 64-05 Review and Security Gate Schema
- [ ] Add structured review/security findings schema and validator with high-risk trigger rules.

### 64-06 PAP Contract Extensions
- [ ] Propose backward-compatible PAP fields for workflows, checkpoints, evidence refs, review gates, and memory layers.

### 64-07 Viewer Workflow Surface
- [ ] Surface workflow stage, checkpoint, evidence-ref, and review-gate state in the topology/conductor UI.
```

## Completion Gate

Phase 64 is complete only when:

- Workflow and checkpoint schemas validate.
- Memory atoms preserve refs to raw evidence.
- Security findings require trace and impact.
- PAP validation remains backward-compatible.
- `scripts\verify.cmd` passes.
- README and `.agent/agent_tasks.md` accurately reflect adopted capabilities.
