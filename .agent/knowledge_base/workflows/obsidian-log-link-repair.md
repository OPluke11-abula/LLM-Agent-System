# Obsidian Log Link Repair Workflow

## Purpose

Repair unresolved Obsidian `log.md` wikilinks caused by copying LAS-style lowercase note paths into the Title Case Obsidian vault mirror.

## Trigger

Use this workflow when `tools/lint_obsidian_vault.ps1` reports `unresolved-wikilink` findings in `log.md` where the target exists in Obsidian under a Title Case filename.

## Procedure

1. Run `tools/lint_obsidian_vault.ps1 -Format Json` and capture current unresolved log links.
2. Confirm the intended Title Case target notes exist in the vault.
3. Replace only the broken `log.md` wikilinks with the canonical Obsidian note paths.
4. Preserve the operation history text; do not rewrite unrelated log entries.
5. Rerun the vault audit and confirm the log link findings are gone.
6. Record remaining non-blocking findings, if any, in the flow report.

## Acceptance Checks

- Obsidian vault audit has zero `unresolved-wikilink` findings for `log.md`.
- No Critical or High vault audit findings remain.
- LAS health audit remains at zero findings.
- Obsidian CLI can search and read the workflow and report.
- `git diff --check -- .agent/knowledge_base` exits `0`.

## Safety

This workflow repairs navigation links in `log.md` only. It must not edit `.obsidian/`, install plugins, delete notes, or rewrite raw source content.
