# LLM Agent System

## Summary

LAS is a local, contract-first AI agent runtime with a Python/FastAPI backend, PAP-compatible `.agent/` workspace contracts, and a React/Tauri visual control plane.

This page is a fast orientation note. It does not prove current repo status.

## Live Intake Snapshot

- Repo: `D:/GitHub/LLM-Agent-System`
- Branch at intake: `main`
- HEAD at intake: `2cbb467`
- Working tree at intake: `66` changed/untracked entries
- Intake date: `2026-07-09`
- Historical Codebase Memory MCP snapshot: ready with `3978` nodes and `13985`
  edges at intake. Refresh graph state before relying on it.

## Start Here

- Read `README.md` for product scope and operator commands.
- Read `.agent/README.md` for PAP contract boundaries.
- Check `git status --short` before changing anything.
- Use an available code graph before broad text search; refresh it or read live
  source before edits.
- Use `agent_workspace/tool_manifest.py validate` before broad repo verification when touching PAP/tool contracts.
- Use `scripts/verify.cmd` as the broader gate when warranted.

## Runtime Snapshot

- Python: `3.14.6` in the active shell.
- Node.js: `v24.13.1`.
- npm: `11.11.0`.
- Rust/Cargo: `cargo 1.94.1`.
- Backend tests: `pyproject.toml` points pytest at `agent_workspace/tests` with coverage over `agent_workspace`.
- Viewer package: `viewer/package.json` uses React 19, React Router 7, React Flow 11, Tauri 2, TypeScript 6, Vite 8, Tailwind 4, and Playwright.

## Main Source Areas

- `agent_workspace/core/`: runtime engine, router, policy, memory, conductor, and execution boundaries.
- `agent_workspace/routes/`: FastAPI route modules for admin, audit, billing, collaboration, swarm, memory, and related APIs.
- `agent_workspace/skills/`: PAP-declared local tool implementations and skill contracts.
- `agent_workspace/tests/`: Python regression and contract tests.
- `spec/`: JSON schemas for PAP/LAS contracts, registry, evidence memory, and review findings.
- `.agent/`: PAP workspace manifest, skills/prompts/memory/workflow docs, and local knowledge base.
- `viewer/`: React/Tauri visual control plane and verification scripts.
- `docs/`: architecture, workflow, hub, and protocol alignment documentation.

## Runtime Entrypoints

- API app: `agent_workspace.api:app`, commonly launched with `uvicorn agent_workspace.api:app --host 0.0.0.0 --port 8000`.
- CLI: `agent_workspace/cli.py`.
- Tool manifest: `agent_workspace/tool_manifest.py`.
- PAP validation: `agent_workspace/pap_validate.py`.
- Code graph tooling: `agent_workspace/codebase_index.py` and `agent_workspace/skills/tool_codebase_memory.py`.
- Viewer app: `viewer/` with Vite/Tauri scripts in `viewer/package.json`.

## Architecture Pointers

- `agent_workspace/core/engine.py`: `AgentEngine`, tool schemas, tool execution allowlist boundary.
- `agent_workspace/core/router.py`: `AgentRouter`, agent loops, approval-aware tool execution, conductor telemetry.
- `agent_workspace/routes/`: FastAPI route modules for collaboration, audit, admin, swarm, billing, and related APIs.
- `agent_workspace/topology_stream.py`: topology stream and conductor trace payloads consumed by the viewer.
- `agent_workspace/memory_pack.py`: evidence memory packing and traceable workflow memory records.
- `agent_workspace/review_findings_validate.py`: structured review/security finding validation.
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
- `agent_workspace.memory_pack.pack_evidence`
- `agent_workspace.review_findings_validate.validate_review_findings`

## Code Graph Bridge

The high-value symbols above are bounded orientation pointers, not a cached
graph snapshot. Use [[../workflows/code-graph-bridge]] to select a narrow query
for the change area, inspect the live symbol source, and trace callers when the
edit crosses execution, approval, persistence, or API boundaries.

Before every edit, refresh the graph or read the live source in the same task.
If the graph is stale or unavailable, fall back to live source and focused text
search. Do not treat stored node/edge counts, prior graph output, or this note
as proof of current callers or source behavior.

## Route Pointers

- `GET /v1/health`
- `GET /v1/metrics`
- `GET /v1/tools`
- `POST /v1/chat`
- `POST /v1/stream`
- `POST /v1/task`
- `GET /v1/session/{session_id}`
- `POST /v1/session/{session_id}/approve`
- `POST /v1/session/{session_id}/reject`
- `GET /v1/memory`
- `GET /v1/memory/query`
- `POST /v1/memory/preference`
- `POST /v1/memory/update`
- `GET /v1/crew/topology`
- `POST /v1/crew/register`
- `GET /v1/admin/tenants`
- `POST /v1/admin/tenants/rotate-key`
- `POST /v1/admin/tenants/update-subscription`
- `GET /v1/billing/saas/invoice`
- `POST /v1/billing/stripe/webhook`

## Common Commands

```powershell
python agent_workspace/tool_manifest.py validate
python agent_workspace/pap_validate.py .agent/agent.md
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
- Current-state claims must be rechecked live because the working tree was dirty at intake.
- For contract/tooling changes, run `python agent_workspace/tool_manifest.py validate`.
- For full confidence, run `scripts/verify.cmd` from repo root.
- For viewer changes, run relevant `viewer/package.json` scripts.
- Use [[../workflows/code-graph-bridge]] for structural discovery before broad
  text search when a graph is available; refresh it or read live source before
  edits.

## Historical Snapshot

- Obsidian intake date: `2026-07-02`.
- Branch at Obsidian intake: `main`.
- HEAD at Obsidian intake: `341c15c`.
- Working tree at Obsidian intake: `16` changed/untracked entries.

## Related Notes

- [[../index]]
- [[../known-issues/memory-must-not-replace-verification]]
- [[../workflows/project-intake]]
- [[../workflows/code-graph-bridge]]
