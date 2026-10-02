# Obsidian Root Scratch Triage

## Purpose

Resolve empty root-level scratch or default Obsidian notes without deleting, moving, or reclassifying user content.

## Trigger

Use this workflow when `tools/lint_obsidian_vault.ps1` reports an `empty-root-note` Info finding for a root-level scratch/default note.

## Inputs

- Obsidian vault `AGENTS.md`.
- LAS knowledge-base `index.md` and `log.md`.
- Obsidian vault `index.md` and `log.md`.
- Current vault audit JSON from `tools/lint_obsidian_vault.ps1 -Format Json`.

## Procedure

1. Read the vault operating rules before changing notes.
2. Confirm the audit finding is only `empty-root-note` and the target note is empty or whitespace-only.
3. Prefer non-destructive triage: do not delete or move the note.
4. Fill the empty scratch note with a minimal placeholder that states it is scratch, not project memory.
5. Add workflow/report links to both LAS and Obsidian indexes.
6. Append one operation log entry after verification.
7. Rerun Obsidian vault audit, LAS inventory refresh, LAS health audit, query/preflight smoke tests, Obsidian CLI search/read, credential scan, and whitespace diff check.

## Safety

- Do not rewrite non-empty root notes.
- Do not bulk move or delete scratch notes without explicit approval.
- Do not edit `.obsidian/` or install plugins.
- Treat the placeholder as a lint cleanup marker, not durable project knowledge.

## Verification Commands

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File D:\GitHub\LLM-Agent-System\.agent\knowledge_base\tools\lint_obsidian_vault.ps1 -Format Json
powershell -NoProfile -ExecutionPolicy Bypass -File D:\GitHub\LLM-Agent-System\.agent\knowledge_base\tools\refresh_knowledge_inventory.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File D:\GitHub\LLM-Agent-System\.agent\knowledge_base\tools\lint_knowledge_base.ps1 -Format Json
powershell -NoProfile -ExecutionPolicy Bypass -File D:\GitHub\LLM-Agent-System\.agent\knowledge_base\tools\query_knowledge_inventory.ps1 -Query 'obsidian root scratch triage' -Top 3 -Format Json
powershell -NoProfile -ExecutionPolicy Bypass -File D:\GitHub\LLM-Agent-System\.agent\knowledge_base\tools\start_agent_preflight.ps1 -Query 'obsidian root scratch triage' -Top 5 -NoRefresh
```

## Related Notes

- [[workflows/obsidian-vault-health-audit]]
- [[workflows/obsidian-log-link-repair]]
