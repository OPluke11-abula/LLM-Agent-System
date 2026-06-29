# Workflows Entry Point

This file documents PAP-facing workflows for LAS.

## Workflow Governance

LAS uses small, stage-specific governance documents instead of a single large workflow prompt:

- `docs/workflow/SOURCE_OF_TRUTH.md`: conflict resolution, evidence requirements, and scope rules.
- `docs/workflow/RISK_POLICY.md`: low/medium/high risk classification, approval boundaries, and security defaults.
- `docs/workflow/REVIEW_PROTOCOL.md`: review stance, finding requirements, and security review triggers.
- `docs/workflow/SECURITY_REVIEW_GATE.md`: structured security findings, high-risk triggers, and validator usage.
- `docs/workflow/HANDOFF_SCHEMA.md`: Markdown and JSON handoff fields plus onboarding order.

Load only the document needed for the current stage. These files are workflow policy; they do not change runtime behavior by themselves.

## PAP Runtime and Security Contracts

LAS carries PAP-aligned runtime and security contracts under `spec/`:

- `spec/runtime-interface.md`: stable runtime methods, LAS mappings, and standard error codes.
- `spec/security.md`: prompt, skill, memory, permission, and handoff-integrity security layers.
- `spec/memory.schema.json`: memory and handoff packet schema, including LAS-compatible `task_state` snapshots and checksum metadata.

Treat these documents as interoperability contracts. They guide adapters, validators, and future workflow execution without changing provider selection or task routing by themselves.

## Codex Development Workflow Manifest

The opt-in stage manifest lives at:

```text
.agent/workflows/codex-development.yaml
```

Validate it without executing any stage actions:

```powershell
.\.venv\Scripts\python.exe agent_workspace\workflow_lint.py --root . --workflow .agent\workflows\codex-development.yaml
```

The linter validates `spec/workflow-stage.schema.json` and optional checkpoint records against `spec/checkpoint.schema.json`, checks dependencies, and rejects workspace path escapes.

## Conductor Workflow Bridge

`ConductorPlan` accepts optional workflow metadata for audit and topology correlation:

- `workflow_stage_id`: stage id from `.agent/workflows/codex-development.yaml`.
- `workflow_checkpoint_ref`: checkpoint record path or stable reference.
- `evidence_refs`: raw evidence refs under `.agent/memory/refs/` or other validated workflow artifacts.

Router telemetry and streamed topology payloads include these values when present. Missing workflow metadata is valid and keeps ordinary router runs unchanged. These fields do not alter model/provider selection, tool allowlists, or policy scoring.

## Review and Security Findings

Structured review and security findings are validated by:

```powershell
.\.venv\Scripts\python.exe agent_workspace\review_findings_validate.py --root . --input docs\reviews\sample-security-findings.json
```

The validator checks `spec/review-findings.schema.json`, requires traceable entrypoint/sink/evidence paths, rejects workspace escapes, and enforces declared security triggers for high-risk paths.

## Evidence Memory Packing

Long command output and review evidence can be explicitly packed into `.agent/memory/` without hooks or background capture:

```powershell
.\.venv\Scripts\python.exe agent_workspace\memory_pack.py --root . --task TASK-0001 --input outputs\raw-test-output.txt --summary "Focused verification passed."
```

The packer writes:

- `.agent/memory/refs/<task>.md` for raw evidence.
- `.agent/memory/l1-atoms.jsonl` for traceable atom facts.
- `.agent/memory/l2-scenarios/<task>.md` for scenario summaries.
- `.agent/memory/l3-persona.md` only when a stable persona/preference is explicitly supplied.
- `.agent/memory/canvases/<task>.mmd` for Mermaid node/ref navigation.

Every generated atom includes a `result_ref` and `source_hash`; summaries are pointers to evidence, not replacements for evidence.

## Bootstrap and Verify

```powershell
.\scripts\bootstrap_verify.cmd
```

Fast local verification without installing dependencies:

```powershell
.\scripts\verify.cmd -SkipViewer
```

## CLI Runtime

```powershell
python agent_workspace/run.py summary
python agent_workspace/run.py stream --msg "Hello" --session demo
```

## FastAPI Adapter

```powershell
uvicorn agent_workspace.api:app --host 0.0.0.0 --port 8000
```

Runtime-facing endpoints:

- `GET /v1/health`
- `GET /v1/tools`
- `POST /v1/chat`
- `POST /v1/stream`
- `POST /v1/task`
- `GET /v1/session/{id}`
- `GET /v1/memory`
- `GET /v1/memory/query`
- `GET /v1/metrics`

## Contract Pipeline

```powershell
python agent_workspace/tool_manifest.py sync
python agent_workspace/tool_manifest.py validate
python agent_workspace/pap_validate.py
```

## Topology Bridge

```powershell
python agent_workspace/topology_stream.py stream --msg "test" --session verify-p1 --dry-run
```

Topology state is emitted to `workspace/topology_state.json` unless
`AGENT_WORKSPACE_DIR` overrides the shared workspace directory.

## 中文說明

LAS 的標準工作流是先驗證 contract，再跑 runtime，最後用 topology bridge 或
viewer 觀測 session 狀態。PAP 文件描述的是可攜式協作合約；真正的執行仍由
`agent_workspace/core/`、FastAPI adapter 與 topology bridge 承擔。
