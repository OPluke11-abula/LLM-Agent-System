# Knowledge Base Health Audit Workflow

## Purpose

Run a read-only health audit over the LAS local Markdown knowledge base before relying on it for agent startup, context packs, or handoffs.

## Trigger

Use this workflow when:

- adding a new workflow, handoff, report, evidence note, decision, or known issue
- preparing to hand work to another agent
- investigating missing or stale Obsidian/LAS memory
- checking whether generated inventory and links are still healthy

## Tool

Use:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\.agent\knowledge_base\tools\lint_knowledge_base.ps1
```

For machine-readable output:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\.agent\knowledge_base\tools\lint_knowledge_base.ps1 -Format Json
```

To make the command fail on serious findings:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\.agent\knowledge_base\tools\lint_knowledge_base.ps1 -FailOn High
```

## Checks

The audit checks:

- missing `index.md`
- empty Markdown notes
- task-facing notes not linked from `index.md`
- unresolved Obsidian wikilinks
- missing required knowledge-base directories
- handoffs without a next-read section
- decisions without a revisit condition
- known issues without verification guidance
- potential credential-like strings
- missing or invalid `indexes/knowledge-inventory-latest.json`
- `contains_full_text` accidentally changing away from `false`

## Expected Use

1. Run the lint tool after knowledge-base edits.
2. Treat `Critical` and `High` findings as blockers before sharing or using generated packs.
3. Treat `Medium` findings as cleanup candidates unless they affect the current task.
4. Record findings in the flow report or handoff.
5. Do not auto-fix findings unless the user explicitly asks for cleanup.

## Safety

This workflow is intentionally read-only. It helps agents reduce repeated discovery, but it does not prove current code, dependency, test, build, or external-tool state.
