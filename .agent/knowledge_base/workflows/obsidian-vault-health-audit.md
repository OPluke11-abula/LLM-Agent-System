# Obsidian Vault Health Audit Workflow

## Purpose

Run a read-only health audit over the Obsidian vault mirror itself, complementing the LAS-local health audit.

## Trigger

Use this workflow when:

- LAS workflow/report notes are mirrored into Obsidian
- Obsidian index links have been reorganized
- an agent will rely on Obsidian as a local AI operating layer
- the user asks whether the vault is healthy after automation

## Tool

Use from the LAS repo:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\.agent\knowledge_base\tools\lint_obsidian_vault.ps1
```

For machine-readable output:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\.agent\knowledge_base\tools\lint_obsidian_vault.ps1 -Format Json
```

For gate-style use:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\.agent\knowledge_base\tools\lint_obsidian_vault.ps1 -FailOn High
```

## Checks

The audit checks:

- required vault directories exist
- `index.md` and `log.md` exist
- contract-directory notes are linked from `index.md`
- Obsidian wikilinks resolve, including same-folder, relative, and unique filename-stem links
- Markdown files are non-empty
- potential credential-like key/value strings are absent

## Scope

The audit is read-only. Root-level scratch/default notes are not treated as index blockers. The audit ignores `.obsidian/` settings and does not install plugins.

## Acceptance Checks

- The audit runs in Markdown and JSON modes.
- Critical and High findings are zero before relying on the vault for agent startup.
- Obsidian CLI can read the workflow and report notes.
- LAS health audit remains clean after adding this workflow.

## Safety

This workflow finds issues; it does not auto-fix them. Do not bulk rewrite, move, delete, or plugin-edit the vault without explicit approval.
