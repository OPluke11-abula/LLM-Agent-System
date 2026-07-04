# Inventory-Backed Query Workflow

## Purpose

Use the generated LAS knowledge inventory to rank candidate notes before reading files.

This workflow reduces broad context reads by querying compact metadata first: title, path, note type, headings, wikilinks, and search cues.

## Script

Run from `D:/GitHub/LLM-Agent-System`:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\.agent\knowledge_base\tools\query_knowledge_inventory.ps1 -Query "memory must not replace verification"
```

Optional JSON output:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\.agent\knowledge_base\tools\query_knowledge_inventory.ps1 -Query "inventory refresh" -Format Json
```

## Procedure

1. Refresh the inventory when notes changed:
   `powershell -NoProfile -ExecutionPolicy Bypass -File .\.agent\knowledge_base\tools\refresh_knowledge_inventory.ps1`
2. Query the inventory with the user topic.
3. Read only the top specific candidate notes.
4. Prefer non-router results over `index.md` and `log.md`.
5. Separate inventory-derived candidates from live verification.
6. Verify current repo, tool, test, build, and plugin claims live before reporting them.

## Ranking Model

The script weights matches in this order:

- exact title
- exact path
- title terms
- path terms
- heading terms
- search cues
- wikilinks

Navigation notes such as `index.md` and `log.md` receive a penalty so they do not outrank specific workflows, known issues, decisions, handoffs, evidence notes, or exports.

## Output Contract

Each result includes:

- path
- title
- type
- score
- matched fields
- `read_first`

## Safety

- The query script reads compact inventory metadata only.
- Query results are orientation, not proof.
- Do not send inventory data to external providers without explicit approval.
- Do not report current state claims without live verification.

## Related Notes

- [[../index]]
- [[knowledge-inventory-refresh]]
- [[local-knowledge-inventory]]
- [[query-memory]]
- [[../indexes/knowledge-inventory-latest]]
- [[../known-issues/memory-must-not-replace-verification]]
