# Handoff Schema

Status: active workflow governance

This document defines the minimum LAS handoff content for thread transitions, cross-agent work, and cross-repo coordination.

## Handoff Fields

Use these sections for Markdown handoffs:

```markdown
# Handoff

## Objective

## Current State

## Repos And Branches

## Files Changed

## Decisions Made

## Verification Run

## Pending Steps

## Risks And Constraints

## Required Onboarding

## Suggested Skills
```

For machine-readable handoffs, use these fields:

```json
{
  "task_state": "",
  "pending_steps": [],
  "context_summary": "",
  "memory_snapshot": {},
  "checksum": ""
}
```

LAS may store `task_state` as a structured object for backward-compatible snapshots of `.agent/agent_tasks.md`. New `AgentEngine.export_handoff()` packets include `pending_steps` and calculate `checksum` over `task_state`, `pending_steps`, `context_summary`, and `memory_snapshot`.

## Evidence Rules

- Link to existing plans, specs, commits, and diffs instead of duplicating them.
- Include exact commands and results for verification already run.
- Include unresolved blockers and what would unblock them.
- Redact secrets, credentials, personal contact details, and tokens.

## Required Onboarding

For LAS work, the next agent must read:

1. `.agent/agent.md`
2. `.agent/skills.md`
3. `.agent/agent_tasks.md`
4. `.agent/workflows.md`
5. the active plan or task document

For PAP project work, the next agent must follow PAP's own `.agent/agent.md` order:

1. `.agent/agent.md`
2. `.agent/skills.md`
3. `agent_tasks.md`
4. `.agent/handoff_guide.md`
5. `.agent/routing.md`

## Completion Rule

A handoff is complete only when a fresh agent can identify:

- what to do next
- what not to change
- what has already been verified
- what remains unverified
- where the evidence lives
