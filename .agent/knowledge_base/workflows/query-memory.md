# Query Memory Workflow

## Purpose

Answer questions from local agent memory while clearly separating durable notes from live verification.

## Procedure

1. Read `.agent/knowledge_base/index.md`.
2. Search compiled project notes, workflows, decisions, known issues, and handoffs.
3. Read the smallest useful note set.
4. Mark each answer fact as:
   - memory-derived
   - verified live in this turn
   - not verified
5. Run live checks only when the answer depends on current state.
6. If durable output is needed, write it under `.agent/knowledge_base/exports/`.

## Answer Contract

```markdown
## Memory-Derived
## Verified Now
## Not Verified
## Next
```

## Live Verification Triggers

Always verify live before claiming:

- current git branch, HEAD, dirty status, or diff state
- current package/tool version
- current test/build/lint pass or failure
- server availability
- external docs, releases, APIs, or policies

## Related Notes

- [[../known-issues/memory-must-not-replace-verification]]
- [[project-intake]]
