# Known Issue - Memory Must Not Replace Verification

## Symptom

An agent reads an old note and repeats it as if it proves the current state.

## Cause

Local memory is durable but can become stale. It records prior decisions, summaries, and known patterns, not current runtime truth.

## Fix Or Workaround

- Use knowledge-base notes for orientation.
- Verify current repo, config, CLI, dependency, and test state live before claiming success.
- In handoffs and reports, separate `Verified` from `Not Verified`.
- Prefer exact commands and outputs over vague claims.

## Verification

A good task report should name:

- what was read from local memory
- what was checked live
- what changed on disk
- what remains unverified

## Related Notes

- [[../index]]
- [[../workflows/query-memory]]
- [[../workflows/handoff]]
