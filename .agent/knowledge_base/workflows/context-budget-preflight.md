# Context Budget Preflight Workflow

## Purpose

Produce a typed, report-only estimate of context cost and advisory reduction
potential before a token-sensitive task. The preflight never trims, compacts,
archives, deletes, or mutates the supplied context.

## API

Use `agent_workspace.core.context_budget_preflight.build_context_budget_preflight`
with:

- system prompt, messages, memory context, and tool schemas for the base token
  estimate
- task context text
- memory reference paths or IDs
- bounded code-graph reference paths or symbols
- an optional `TokenEfficientProfile`

The returned `ContextBudgetReport` contains component totals, an estimated total,
advisory reduction tokens and ratio, reference counts, a handoff recommendation,
and explicit `report_only=true` / `trimming_applied=false` markers.

## Interpretation

- Treat all counts as estimates unless the underlying counter reports otherwise.
- Reduction values are potential savings implied by the supplied profile limits;
  they do not authorize trimming.
- A handoff recommendation is a signal for the report contract, not an automatic
  handoff or session mutation.
- Cite the preflight report and its source refs using [[../templates/agent-report]].

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest --no-cov -q agent_workspace/tests/test_context_budget_preflight.py agent_workspace/tests/test_token_counter.py
```

## Related Notes

- [[token-efficient-work-mode]]
- [[evidence-memory-bridge]]
- [[code-graph-bridge]]
- [[agent-report-contract]]
