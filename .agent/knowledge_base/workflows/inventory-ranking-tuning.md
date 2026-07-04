# Inventory Ranking Tuning Workflow

## Purpose

Tune LAS knowledge inventory query ranking when the right note is present but lower-value notes, especially generated reports, outrank the canonical workflow or known issue.

## Trigger

Use this workflow when a query smoke test shows one of these symptoms:

- a generated `exports/` report outranks the canonical `workflows/` note for the same topic
- `index.md` or `log.md` appears above task-facing notes
- a known issue is found but not promoted above related reports
- agent-start preflight builds a context pack with the right topic but weak first-read ordering

## Current Ranking Rules

`tools/query_knowledge_inventory.ps1` scores matches from title, path, headings, cues, and links, then applies a type weight:

- `workflow`: `+18`
- `known_issue`: `+16`
- `project`: `+12`
- `decision`: `+10`
- `handoff`: `+8`
- `evidence`: `+6`
- `template`: `+2`
- `export`: `-10`
- `router`: `-18`
- `audit_log`: `-18`

The goal is not to hide reports. Reports remain retrievable, but canonical operating notes should be read first when match quality is similar.

## Procedure

1. Refresh inventory with `tools/refresh_knowledge_inventory.ps1`.
2. Run the query that produced weak ordering with `tools/query_knowledge_inventory.ps1 -Format Json`.
3. Confirm canonical notes rank above generated reports when their lexical match quality is similar.
4. Run a known-issue query to ensure the weight does not bury risk notes.
5. Run `tools/start_agent_preflight.ps1 -NoRefresh` for a representative task.
6. Record the before/after ranking and commands in `exports/`.

## Acceptance Checks

- `context pack validation` returns `workflows/context-pack-validation.md` before `exports/context-pack-validation-flow-report-2026-07-03.md`.
- `memory must not replace verification` returns `known-issues/memory-must-not-replace-verification.md` as the first result.
- Agent-start preflight for `context pack validation` produces a validated context pack with the workflow before the report.
- No full text is embedded in `knowledge-inventory-latest.json`.

## Safety

- Keep ranking changes additive and transparent through `matched` reasons.
- Do not use inventory ranking as proof that a repo, tool, or test result is current.
- Verify scripts, commands, and external state live before reporting them as facts.
