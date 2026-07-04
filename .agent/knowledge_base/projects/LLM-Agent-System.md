# LLM Agent System

## Summary

LAS is a local, contract-first AI agent runtime with a Python/FastAPI backend, PAP-compatible `.agent/` workspace contracts, and a React/Tauri visual control plane.

This page is a fast orientation note. It does not prove current repo status.

## Snapshot From Obsidian Intake

- Repo: `D:/GitHub/LLM-Agent-System`
- Branch at intake: `main`
- HEAD at intake: `341c15c`
- Working tree at intake: `16` changed/untracked entries
- Intake date: `2026-07-02`
- Code graph project: `D-GitHub-LLM-Agent-System`

## Start Here

- Read `README.md` for product scope and operator commands.
- Read `.agent/README.md` for PAP contract boundaries.
- Check `git status --short` before changing anything.
- Use Codebase Memory MCP project `D-GitHub-LLM-Agent-System` before grep-style code discovery.
- Use `agent_workspace/tool_manifest.py validate` before broad repo verification when touching PAP/tool contracts.
- Use `scripts/verify.cmd` as the broader gate when warranted.

## Architecture Pointers

- `agent_workspace/core/engine.py`: `AgentEngine`, tool schemas, tool execution allowlist boundary.
- `agent_workspace/core/router.py`: `AgentRouter`, agent loops, approval-aware tool execution, conductor telemetry.
- `agent_workspace/routes/`: FastAPI route modules for collaboration, audit, admin, swarm, billing, and related APIs.
- `agent_workspace/topology_stream.py`: topology stream and conductor trace payloads consumed by the viewer.
- `.agent/`: PAP-compatible workspace contracts for skills, prompts, memory, workflows, and knowledge.
- `viewer/`: React/Tauri dashboard and topology control plane.

## High-Value Symbols

- `agent_workspace.core.engine.AgentEngine.execute_tool`
- `agent_workspace.core.engine.AgentEngine.get_tool_schemas`
- `agent_workspace.core.router.AgentRouter.run_agent_loop`
- `agent_workspace.core.router.AgentRouter._run_agent_loop_internal`
- `agent_workspace.core.router.AgentRouter.stream_agent_loop`
- `agent_workspace.core.router.AgentRouter._execute_tool_with_approval`
- `agent_workspace.topology_stream.conductor_trace_payload`
- `viewer.src.components.TopologyView.ConductorTracePanel`

## Route Pointers

- `GET /v1/crew/topology`
- `GET /v1/audit/logs`
- `GET /v1/audit/verify`
- `POST /v1/billing/stripe/webhook`
- `GET /v1/swarm/billing/status`
- `POST /v1/swarm/billing/policy`

## Common Commands

```powershell
python agent_workspace/tool_manifest.py validate
.\scripts\verify.cmd -SkipViewer
.\scripts\verify.cmd
uvicorn agent_workspace.api:app --host 0.0.0.0 --port 8000
```

Viewer:

```powershell
cd viewer
npm run build
npm run verify:ui
npm run test:swarm-ui
npm run doctor
```

## Verification Policy

- This page is not proof that the repo is currently passing.
- Before claiming a fix, run the smallest relevant check and report the exact command/result.
- For contract/tooling changes, run `python agent_workspace/tool_manifest.py validate`.
- For full confidence, run `scripts/verify.cmd` from repo root.
- For viewer changes, run relevant `viewer/package.json` scripts.

## Related Notes

- [[../index]]
- [[../known-issues/memory-must-not-replace-verification]]
- [[../workflows/project-intake]]
