# Knowledge Inventory Refresh Workflow

## Purpose

Refresh the LAS local knowledge inventory from Markdown metadata with a repeatable script.

This turns the hand-reviewed Stage 1 inventory into a reusable local workflow while keeping the inventory compact, inspectable, and free of full note bodies.

## Script

Run from `D:/GitHub/LLM-Agent-System`:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\.agent\knowledge_base\tools\refresh_knowledge_inventory.ps1
```

Outputs:

- `.agent/knowledge_base/indexes/knowledge-inventory-latest.md`
- `.agent/knowledge_base/indexes/knowledge-inventory-latest.json`

## Procedure

1. Read `.agent/knowledge_base/index.md`.
2. Run the refresh script.
3. Confirm the generated JSON parses.
4. Confirm `contains_full_text=false`.
5. Run a ranking smoke test for a known query.
6. Run a credential-value scan over changed/generated files.
7. Run `git diff --check -- .agent/knowledge_base`.
8. Update `.agent/knowledge_base/log.md` and any Obsidian report.

## Refresh Rules

Refresh after adding or renaming:

- workflows
- decisions
- known issues
- handoffs
- evidence notes
- exports
- project notes

## Safety

- The script excludes `indexes/` and `tools/` from the corpus to avoid self-indexing generated files.
- The script extracts metadata only: path, type, title, headings, wikilinks, and search cues.
- The generated inventory is orientation, not proof.
- Current repo, tool, test, build, and plugin claims still require live verification.

## Related Notes

- [[../index]]
- [[local-knowledge-inventory]]
- [[semantic-retrieval-pilot]]
- [[../indexes/knowledge-inventory-latest]]
- [[../known-issues/memory-must-not-replace-verification]]
