# Workflows Entry Point

This file documents PAP-facing workflows for LAS.

## Workflow Governance

LAS uses small, stage-specific governance documents instead of a single large workflow prompt:

- `docs/workflow/SOURCE_OF_TRUTH.md`: conflict resolution, evidence requirements, and scope rules.
- `docs/workflow/RISK_POLICY.md`: low/medium/high risk classification, approval boundaries, and security defaults.
- `docs/workflow/REVIEW_PROTOCOL.md`: review stance, finding requirements, and security review triggers.
- `docs/workflow/HANDOFF_SCHEMA.md`: Markdown and JSON handoff fields plus onboarding order.

Load only the document needed for the current stage. These files are workflow policy; they do not change runtime behavior by themselves.

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
