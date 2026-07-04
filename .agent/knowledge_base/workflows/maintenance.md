# Maintenance Workflow

## Purpose

Run a read-only health check so `.agent/knowledge_base/` remains useful without accumulating stale, disconnected, or unsafe notes.

## Checks

- Required root files exist: `index.md`, `log.md`.
- Important subdirectories exist: `projects/`, `workflows/`, `handoffs/`, `decisions/`, `known-issues/`, `exports/`, `raw/`, `templates/`.
- Important links resolve to existing Markdown files.
- Project notes include verification caveats.
- Handoffs include `Next Agent Should Read`.
- Decisions include revisit conditions.
- Known issues include verification guidance.
- Notes do not contain common credential patterns.

## Modification Policy

- Default mode is read-only.
- Do not delete, move, rewrite, or bulk-fix notes without explicit approval.
- Record advisory items separately from failures.

## Related Notes

- [[../index]]
- [[../known-issues/memory-must-not-replace-verification]]
