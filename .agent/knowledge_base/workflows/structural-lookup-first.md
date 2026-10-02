# Structural Lookup First Workflow

## Purpose

Choose the smallest live lookup that can answer a code question before reading
large files or scanning the repository broadly. This is an advisory workflow:
it records the lookup path and broad-read rationale, but never blocks or mutates
the code graph.

## Lookup Order

1. Route from [[../projects/LLM-Agent-System]] or the task's known entrypoint.
2. Query the code graph for the smallest matching symbol, route, class, or
   function.
3. Trace direct callers or callees when the change crosses a boundary.
4. Read a bounded live snippet around the symbol and its immediate contract.
5. Use narrow literal search for strings, configuration, or non-code files.
6. Use a broad file read or repository scan only when the earlier steps are
   unavailable or insufficient.

## Broad-Read Justification

When step 6 is needed, record this compact note before or alongside the read:

```markdown
Broad read: <path or scope>
Reason: <graph/snippet/search result that was insufficient>
Needed to answer: <specific question>
Bound: <lines, files, or glob limit>
Follow-up: <narrow lookup or verification planned>
```

Do not use a broad read merely to rediscover project orientation already held
in the project note or code-graph pointers.

## Evidence Contract

Record only the query intent, resolved symbol or path, bounded source location,
and relevant caller/callee result in a report or handoff. Treat graph output as
orientation until the live source is checked. If the graph is stale or absent,
state that and fall back to a bounded source read or focused literal search.

## Verification

- Confirm the selected symbol or path exists in the current checkout.
- Run the smallest relevant test or syntax check after edits.
- Use [[maintenance]] for the knowledge-base health audit after workflow edits.
- Do not initialize, rebuild, or mutate a code graph without explicit approval.

## Related Notes

- [[code-graph-bridge]]
- [[query-memory]]
- [[../projects/LLM-Agent-System]]
