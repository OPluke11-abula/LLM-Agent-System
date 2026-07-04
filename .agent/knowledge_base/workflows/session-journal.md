# Session Journal Workflow

## Purpose

Create a compact session-level record after meaningful agent work so the next agent can start from a small, current summary instead of re-reading a long chat.

Use this for recurring AI coding sessions, Obsidian vault maintenance, LAS knowledge-base changes, and multi-agent handoffs.

## Relationship To Handoffs

- A handoff tells another agent how to resume a specific task.
- A session journal records what happened in the session and links the durable artifacts, evidence, and remaining caveats.

When in doubt, write the session journal first, then write a handoff only if another agent must continue a specific unfinished task.

## Output Shape

Write session journals under `.agent/knowledge_base/handoffs/`:

```text
session-journal-YYYY-MM-DD-<topic>.md
```

## Required Sections

- Session Goal
- Changed On Disk
- Evidence And Reports
- Verified Now
- Not Verified
- Decisions
- Next Agent Start Here

## Procedure

1. Read `.agent/knowledge_base/index.md` and recent `.agent/knowledge_base/log.md`.
2. Identify the session goal and the workflow that was executed.
3. List changed files that belong to the session scope.
4. Link evidence notes, workflow reports, or Obsidian reports instead of copying long output.
5. Record exact verification commands and results.
6. Mark anything not verified.
7. Write the journal under `.agent/knowledge_base/handoffs/`.
8. Link the journal from `.agent/knowledge_base/index.md`.
9. Append one `.agent/knowledge_base/log.md` entry.
10. Run link, credential-value, and whitespace checks.

## Quality Bar

- Keep the note short enough to be the first file a future agent reads.
- Prefer paths and wikilinks over pasted logs.
- Do not claim tests, installs, builds, or plugin state passed unless verified in the session.
- Do not treat old memory as proof of current state.
- Do not copy secrets, credentials, cookies, or raw tokens.

## Related Notes

- [[../index]]
- [[handoff]]
- [[evidence-capture]]
- [[semantic-retrieval-pilot]]
- [[../known-issues/memory-must-not-replace-verification]]
