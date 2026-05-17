# Workflows Entry Point

This file documents PAP-facing workflows for LAS.

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
- `POST /v1/chat`
- `POST /v1/stream`
- `POST /v1/task`
- `GET /v1/session/{id}`

## Topology Bridge

```powershell
python agent_workspace/topology_stream.py stream --msg "test" --session verify-p1 --dry-run
```

Topology state is emitted to `workspace/topology_state.json` unless
`AGENT_WORKSPACE_DIR` overrides the shared workspace directory.

## 中文說明

本文件記錄 LAS 的 PAP-facing workflows：CLI runtime、FastAPI adapter，以及
topology bridge。這些 workflow 都透過外部入口使用 LAS，不把產品整合邏輯寫入
核心閉環 runtime。
