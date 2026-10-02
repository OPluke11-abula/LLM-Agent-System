# Preflight Adoption Guide Workflow

## Purpose

Make agent-start preflight the default first step for Codex, Antigravity, and future agents when they need LAS-local memory.

This workflow is not another retrieval primitive. It is the adoption layer that tells an agent when to run preflight, how to read the generated pack, and when live verification is still mandatory.

## When To Use

Use preflight before substantial work that touches or depends on LAS-local memory:

- continuing Obsidian/LAS workflow buildout
- starting a repo task after a long chat or context compaction
- switching between Codex and Antigravity
- resuming from a handoff or session journal
- asking what local agent memory knows about a topic

Skip preflight for tiny self-contained questions that do not need project memory.

## Command

Run from `D:/GitHub/LLM-Agent-System`:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\.agent\knowledge_base\tools\start_agent_preflight.ps1 -Query "<task topic>" -Top 5
```

The command returns a validated context pack path.

## Adoption Contract

After preflight returns `validated=true`:

1. Read the generated pack first.
2. Read candidate notes in order.
3. Treat all pack content as orientation.
4. Verify current-state claims live.
5. If work produces reusable knowledge, write a session journal or report and refresh the inventory.

## Required Agent Response Behavior

When using preflight, the agent should say:

- the query used
- generated pack path
- whether validation passed
- which candidate notes were read
- what was verified live
- what was not verified

## Safety

- Preflight does not prove current repo state.
- Passing validation only proves the pack shape is acceptable.
- Do not skip tests, builds, CLI checks, plugin checks, or external-doc checks when the answer depends on current state.
- Do not send packs to external providers without explicit approval.

## Related Notes

- [[../index]]
- [[agent-start-preflight]]
- [[context-pack-validation]]
- [[context-pack-builder]]
- [[session-journal]]
- [[../known-issues/memory-must-not-replace-verification]]
