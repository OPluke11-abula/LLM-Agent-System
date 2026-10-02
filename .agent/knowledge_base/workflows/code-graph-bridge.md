# Code Graph Bridge Workflow

## Purpose

Use the project note as a bounded map to high-value code symbols, then refresh
structural context live before making edits. The note preserves entry points; it
does not cache graph output or prove current source state.

## Bounded Pointers

Start from [[../projects/LLM-Agent-System]] and choose the smallest applicable
symbol group:

| Change area | Start symbols |
|---|---|
| Tool execution and approvals | `AgentEngine.execute_tool`, `AgentRouter._execute_tool_with_approval` |
| Agent loop and streaming | `AgentRouter.run_agent_loop`, `AgentRouter.stream_agent_loop` |
| Viewer topology trace | `conductor_trace_payload`, `ConductorTracePanel` |
| Evidence and review contracts | `pack_evidence`, `validate_review_findings` |

## Before Editing

1. Query the available code graph with a narrow task or symbol request. Prefer
   an explore-style request for orientation, then a node/source request for the
   exact symbol.
2. Check callers or the traced path when a change crosses an execution,
   approval, persistence, or API boundary.
3. If the graph is stale, unavailable, or does not resolve the symbol, read the
   live source and use focused text search only as a fallback. Do not initialize
   or rebuild a graph without explicit approval.
4. Record only the query intent, source path, symbol, and relevant callers in a
   report or handoff. Do not paste graph dumps or use cached node/edge counts as
   current facts.

## Refresh Rule

- Every edit requires a graph refresh or direct live-source lookup in the same
  task.
- A project-note symbol is an orientation pointer, not evidence that the symbol
  still exists, has the same callers, or is safe to change.
- Re-query after a material edit when the graph service reports pending index
  updates; use the changed file as the source of truth until it is fresh.

## Related Notes

- [[../projects/LLM-Agent-System]]
- [[project-intake]]
- [[query-memory]]
- [[maintenance]]
