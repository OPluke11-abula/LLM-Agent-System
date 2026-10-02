# Query Memory Workflow

## Purpose

Answer questions from local agent memory while clearly separating durable notes from live verification.

## Procedure

1. Read `.agent/knowledge_base/index.md`.
2. Search compact indexes first when available, then project notes, workflows, decisions, known issues, handoffs, and exports.
3. Read the smallest useful note set.
4. Label every material answer fact as one of:
   - memory-derived
   - verified live in this turn
   - not verified
5. Run live checks before making any current-state claim.
6. If live checks are unsafe, slow, or out of scope, keep the claim under `Not Verified` and list the exact check under `Next Checks`.
7. If durable output is needed, write it under `.agent/knowledge_base/exports/`.

## Answer Contract

```markdown
## Memory-Derived
## Verified Now
## Not Verified
## Next Checks
```

Use this contract for direct answers and durable reports. Do not merge memory-derived facts into verified findings unless the live command or source was checked in the current turn.

## Report Template

- [[../templates/query-memory-report]]

## Live Verification Triggers

Always verify live before claiming:

- current git branch, HEAD, dirty status, or diff state
- current package/tool version
- current test/build/lint pass or failure
- server availability
- external docs, releases, APIs, or policies
- whether a queued task is still pending, in progress, blocked, or complete

## Section Rules

- `Memory-Derived`: cite the note, handoff, index entry, rollout summary, or project page used. State whether it may be stale.
- `Verified Now`: include the exact live command/source and the result.
- `Not Verified`: include memory-derived or inferred claims that were not checked live.
- `Next Checks`: list the smallest concrete commands or reads that would verify each unverified claim.

## Related Notes

- [[../known-issues/memory-must-not-replace-verification]]
- [[project-intake]]
- [[../templates/query-memory-report]]
