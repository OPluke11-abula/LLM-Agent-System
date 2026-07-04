# Knowledge Index Repair Workflow

## Purpose

Repair missing or inconsistent index links reported by the read-only health audit without rewriting note contents or changing vault structure.

## Trigger

Use this workflow after `tools/lint_knowledge_base.ps1` reports `not-linked-from-index` findings, or when a workflow/report was appended outside the expected `index.md` sections.

## Procedure

1. Run the health audit in JSON mode and capture current findings.
2. Read `index.md` before editing.
3. Add missing links to the smallest correct section:
   - `workflows/` under `## Workflows`
   - `handoffs/` under `## Handoffs`
   - `exports/` under `## Exports`
   - `known-issues/` under `## Known Issues`
   - `decisions/` under `## Decisions`
4. Prefer Obsidian wikilinks in LAS index entries, for example `workflows/example` without the `.md` suffix inside a wikilink.
5. Remove duplicate or out-of-section entries only when the same target is already linked in the canonical section.
6. Refresh inventory and rerun the health audit.
7. Record before/after findings in an export report.

## Acceptance Checks

- The health audit has zero `not-linked-from-index` findings after repair.
- `contains_full_text` remains `false` in `knowledge-inventory-latest.json`.
- Obsidian mirror files remain searchable/readable through the Obsidian CLI.
- `git diff --check -- .agent/knowledge_base` exits `0`.

## Safety

This workflow only repairs navigation/index links. It must not rewrite raw notes, generated reports, evidence contents, or `.obsidian/` settings.
