# Handoff Workflow

## Purpose

Create compact, audit-friendly handoff notes that let another agent resume without re-reading the whole conversation or rediscovering the repo.

## Required Sections

- Goal
- Current State
- Changed On Disk
- Verified
- Not Verified
- Decisions
- Next Agent Should Read

## Procedure

1. Read `.agent/knowledge_base/index.md` and recent `.agent/knowledge_base/log.md`.
2. Summarize the task goal.
3. List changed files, not just intended changes.
4. List commands actually run and their result.
5. List unverified items explicitly.
6. Write a handoff under `.agent/knowledge_base/handoffs/`.
7. Update `.agent/knowledge_base/log.md`.

## Quality Bar

- Keep it short enough to read first.
- Include exact local paths when useful.
- Do not claim tests or installs passed unless verified.
- Do not copy secrets, private credentials, cookies, tokens, or API keys.

## Related Notes

- [[query-memory]]
- [[maintenance]]
