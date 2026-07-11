# Handoff-First Long Session Gate

## Purpose

Recommend a compact handoff before a long agent session becomes expensive or
hard to resume. The gate is advisory and report-only: it never truncates
history, deletes memory, compacts state, or writes a handoff automatically.

## Signals

Compare the current report against `HandoffThresholds`:

- `history_message_count`: conversation or task-history messages retained.
- `changed_file_count`: files changed in the current work increment.
- `evidence_ref_count`: evidence, artifact, or citation references carried.
- `context_token_count`: estimated total context tokens from the preflight.

`build_context_budget_preflight` returns the observed counts, a boolean
`handoff_recommended`, and ordered `handoff_reasons` for every threshold met.

## Procedure

1. Run the report-only context budget preflight with the active profile.
2. Treat any threshold reason as a recommendation to write or refresh a
   compact handoff before broad discovery or another large work increment.
3. Read the smallest next-note set from [[handoff]] and
   [[../templates/handoff-report]].
4. Record the recommendation, threshold values, observed counts, and next
   action in the task report or handoff.
5. Continue only when the next increment is still bounded and the evidence is
   sufficient; otherwise hand off and stop the increment cleanly.

## Evidence Contract

Keep `report_only=true` and `trimming_applied=false` visible in the preflight
report. A recommendation is not proof that a handoff was written. Record the
exact report inputs and the resulting reasons, without copying secrets or large
conversation bodies.

## Related Notes

- [[context-budget-preflight]]
- [[token-efficient-work-mode]]
- [[verification-profiles]]
- [[handoff]]
