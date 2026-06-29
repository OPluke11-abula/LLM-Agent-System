# LAS Handoff Guide

Status: PAP entrypoint

Use this file when a task must move to another thread, agent, or repository.

## Required Context

Every LAS handoff must identify:

- current objective and current state
- repositories, branches, and changed files
- decisions already made
- exact verification commands already run
- pending steps
- risks, constraints, and unverified assumptions
- onboarding files the next agent must read

The detailed Markdown and JSON field contract lives in `docs/workflow/HANDOFF_SCHEMA.md`.

## Machine Packet Contract

`AgentEngine.export_handoff()` writes PAP-style packets under:

```text
.agent/memory/handoff/
```

New LAS packets include:

- `protocol`
- `version`
- `handoff_id`
- `created_at`
- `task_state`
- `pending_steps`
- `context_summary`
- `memory_snapshot`
- `checksum`

The checksum is calculated over the canonical payload fields `task_state`, `pending_steps`, `context_summary`, and `memory_snapshot`. The importer still accepts older LAS packets that do not have `pending_steps` when their legacy checksum is valid.

## Resume Rule

A fresh agent must read `.agent/agent.md`, `.agent/skills.md`, `.agent/agent_tasks.md`, `.agent/workflows.md`, and any active plan referenced by the handoff before changing files.
