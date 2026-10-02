# Obsidian Mirror Index Repair Workflow

## Purpose

Keep the Obsidian vault index mirror consistent with LAS knowledge-base workflow/report additions so future agents can find mirrored LAS notes through the canonical `## Workflows` and `## Exports` sections.

## Trigger

Use this workflow when a LAS knowledge workflow/report has been mirrored to Obsidian but appears as an appended loose line outside the expected sections, or when Obsidian CLI search can find a note but `index.md` does not route to it cleanly.

## Procedure

1. Read `AGENTS.md` and `index.md` from the vault.
2. Confirm target workflow/report files exist before adding index links.
3. Move workflow links into `## Workflows` and report links into `## Exports`.
4. Remove duplicate loose appended links only after the canonical section entry exists.
5. Add a `log.md` entry naming the changed index targets and verification.
6. Verify with Obsidian CLI `search` and `read`.
7. Keep `.obsidian/` settings and plugin state unchanged.

## Acceptance Checks

- Newly mirrored workflow links appear under `## Workflows`.
- Newly mirrored report links appear under `## Exports`.
- No duplicate loose appended lines remain for the same targets.
- Obsidian CLI can search and read the workflow and report.
- LAS health audit remains at zero findings after the mirror-only change.

## Safety

This workflow only edits Markdown navigation and reports. It must not rewrite raw notes, plugin settings, or generated LAS evidence.
