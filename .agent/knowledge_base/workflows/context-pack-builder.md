# Context Pack Builder Workflow

## Purpose

Build a compact task-specific context pack from the inventory-backed query results.

This gives future agents a low-token start point: query, read order, candidate paths, why each candidate matched, and what must still be verified live.

## Script

Run from `D:/GitHub/LLM-Agent-System`:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\.agent\knowledge_base\tools\build_context_pack.ps1 -Query "inventory refresh" -Top 4 -Refresh
```

Default output:

```text
.agent/knowledge_base/handoffs/context-pack-latest-<query-slug>.md
```

## Procedure

1. Refresh the inventory when notes changed.
2. Build a context pack for the task query.
3. Read only the context pack first.
4. Read candidate notes in the listed order.
5. Run live verification before claiming current repo, tool, test, build, plugin, or external-doc state.
6. If the context pack becomes reusable, link it from `.agent/knowledge_base/index.md` or a session journal.

## Output Contract

The pack includes:

- query
- inventory source
- read order
- candidate details
- matched fields and scores
- verification needed
- explicit note that full note bodies are not copied

## Safety

- Context packs are orientation, not proof.
- The builder reads compact inventory metadata and query output.
- Full note bodies are not copied into the generated pack.
- Do not send packs to external providers without explicit approval.

## Related Notes

- [[../index]]
- [[inventory-backed-query]]
- [[knowledge-inventory-refresh]]
- [[session-journal]]
- [[../known-issues/memory-must-not-replace-verification]]
