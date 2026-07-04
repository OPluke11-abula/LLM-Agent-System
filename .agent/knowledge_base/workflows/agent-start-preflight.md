# Agent Start Preflight Workflow

## Purpose

Prepare a validated low-token starting point before an agent begins work.

This workflow chains the local memory steps into one entry point:

1. refresh inventory
2. build context pack
3. validate context pack
4. read pack first
5. verify current-state claims live

## Script

Run from `D:/GitHub/LLM-Agent-System`:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\.agent\knowledge_base\tools\start_agent_preflight.ps1 -Query "context pack validation" -Top 5
```

Default output:

```text
.agent/knowledge_base/handoffs/agent-start-preflight-latest-<query-slug>.md
```

## Procedure

1. Run the preflight script with the task query.
2. Confirm the script returns `validated=true`.
3. Read the generated pack first.
4. Read candidate notes in order.
5. Use current tools to verify repo state, code, config, tests, builds, plugin state, and external docs before making current-state claims.
6. If the task produces reusable knowledge, update the relevant workflow/report/session journal.

## Output Contract

The script returns:

- query
- generated pack path
- candidate count
- validation status
- validation line count
- `contains_full_text=false`
- next action

## Safety

- Preflight output is orientation, not proof.
- Passing validation only means the pack is a reasonable start artifact.
- Do not skip live verification.
- Do not send packs to external providers without explicit approval.

## Related Notes

- [[../index]]
- [[context-pack-builder]]
- [[context-pack-validation]]
- [[inventory-backed-query]]
- [[../known-issues/memory-must-not-replace-verification]]
