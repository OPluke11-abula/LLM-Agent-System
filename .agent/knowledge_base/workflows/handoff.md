# Handoff Workflow

## Purpose

Create compact, audit-friendly handoff notes that let another agent resume without re-reading the whole conversation or rediscovering the repo.

## Required Sections

- Goal and Scope
- Current State
- Changed On Disk
- Verified
- Not Verified
- Memory Notes
- Decisions
- Unresolved Risks
- Next Agent Should Read
- Next Action
- Suggested Skills

## Procedure

1. Read `.agent/knowledge_base/index.md` and recent `.agent/knowledge_base/log.md`.
2. If the handoff depends on memory, use [[query-memory]] and separate memory-derived facts from live-verified facts.
3. Summarize the task goal and scope boundaries.
4. Record current state, including branch/HEAD/dirty state when relevant.
5. List changed files, not just intended changes.
6. List commands actually run and their observed result.
7. List unverified items explicitly with the smallest next check.
8. Record decisions and constraints that affect future work.
9. List exact files or notes the next agent should read first.
10. Suggest matching skills only when they materially help the next agent.
11. Write durable project handoffs under `.agent/knowledge_base/handoffs/`.
12. Update `.agent/knowledge_base/log.md`.

When the user explicitly asks for a one-off cross-session handoff outside the repo, write that document to the OS temp directory instead of the workspace. Keep repo-local handoffs for durable LAS knowledge-base records.

## Report Template

- [[../templates/handoff-report]]

## Section Rules

- `Goal and Scope`: state the user-visible objective and what is deliberately out of scope.
- `Current State`: describe the latest known task status and cite whether it was verified live.
- `Changed On Disk`: list exact paths and what changed; separate reviewed-only files.
- `Verified`: include exact command/source and observed result.
- `Not Verified`: include anything plausible but unchecked, plus why it was not checked.
- `Memory Notes`: cite relevant memory or KB notes and label staleness risk.
- `Decisions`: capture choices that constrain the next agent.
- `Unresolved Risks`: include failures, dirty-worktree caveats, missing approvals, and external-state limits.
- `Next Agent Should Read`: provide the shortest ordered list of paths/notes/symbols.
- `Next Action`: one concrete next step, not a broad plan.
- `Suggested Skills`: list only skills that should be invoked for the next step.

## Quality Bar

- Keep it short enough to read first.
- Include exact local paths when useful.
- Do not claim tests or installs passed unless verified.
- Do not copy secrets, private credentials, cookies, tokens, or API keys.
- Do not duplicate PRDs, plans, ADRs, issues, commits, or diffs; link to them by path instead.
- Preserve exact commands, exit status, important error text, hashes, paths, and decisions.

## Related Notes

- [[query-memory]]
- [[maintenance]]
- [[../templates/handoff-report]]
