# Agent Report Contract

## Purpose

Keep durable LAS reports concise, auditable, and useful to the next agent
without copying raw evidence or blurring memory with live verification.

## PAP Workflow Manifest

The report-only manifest is `.agent/workflows/knowledge-base-report.yaml`. It
models three reusable stages:

1. `orient`: retrieve the smallest useful local context.
2. `verify`: optionally capture current evidence when a claim needs live proof.
3. `report`: write the durable compact result.

The manifest does not execute stages, capture data, or require a checkpoint by
itself. Use the workflow guidance and the smallest relevant checks.

## Required Sections

Every general-purpose report must include these sections in this order:

1. `Changed On Disk`
2. `Verified`
3. `Not Verified`
4. `Memory Used`
5. `Decisions`
6. `Next`

Use [[../templates/agent-report]] as the base. Specialized templates may add
task-specific sections, but they must preserve or clearly map these six fields.

## Section Rules

- `Changed On Disk`: exact paths and whether each was changed or reviewed only.
- `Verified`: exact commands or sources and observed results.
- `Not Verified`: unrun or out-of-scope checks, with the smallest next check.
- `Memory Used`: note or handoff sources plus staleness risk; never present
  memory-derived facts as current proof.
- `Decisions`: scope, compatibility, safety, and implementation choices that
  constrain follow-up work.
- `Next`: one concrete action, or explicitly state that no follow-up is needed.

## Related Notes

- [[query-memory]]
- [[evidence-capture]]
- [[handoff]]
- [[../templates/agent-report]]
