# Maintenance Workflow

## Purpose

Run a read-only health check so `.agent/knowledge_base/` remains useful without accumulating stale, disconnected, or unsafe notes.

## Checks

- Required root files exist: `index.md`, `log.md`.
- Required subdirectories exist: `projects/`, `workflows/`, `handoffs/`, `decisions/`, `known-issues/`, `exports/`, `raw/`, `templates/`, and `wiki/`.
- Index links resolve and task-facing notes are not orphaned from `index.md`.
- Obsidian wikilinks resolve to existing local notes.
- Markdown notes are non-empty.
- Handoffs include `Next Agent Should Read`, `Next Agent Start Here`, or a generated `Read Order`.
- Decisions include both `Decision` and `Revisit When` sections.
- Known issues include `Verification`, `Verification Guidance`, or `Next Checks`.
- Notes do not contain common credential-like patterns.

## Command

Run the shared, read-only health audit after knowledge-base changes:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\.agent\knowledge_base\tools\lint_knowledge_base.ps1 -FailOn High
```

Use `-Format Json` when a report needs machine-readable findings. Treat `High`
and `Critical` findings as blockers; record `Medium` findings before choosing a
narrow repair.

## Modification Policy

- Default mode is read-only.
- Do not delete, move, rewrite, or bulk-fix notes without explicit approval.
- Record advisory items separately from failures.

## Related Notes

- [[../index]]
- [[../known-issues/memory-must-not-replace-verification]]
