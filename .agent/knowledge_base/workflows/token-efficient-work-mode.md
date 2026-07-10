# Token-Efficient Work Mode Policy

## Purpose

Choose a transparent, advisory work mode before substantial work so agents can
reduce repeated context retrieval without weakening safety, correctness, or
verification. This policy does not compact, archive, delete, or mutate session
state automatically.

## Mode Selection

| Mode | Use when | Read budget per task increment | Tool-output budget |
|---|---|---:|---:|
| `standard` | Default implementation, review, or diagnosis | 12 targeted retrievals | 12k tokens per result; 48k total |
| `token_efficient` | Scope is known and durable notes/graph context exist | 6 targeted retrievals | 4k tokens per result; 20k total |
| `deep_research` | Architecture, security, unfamiliar systems, or explicit exhaustive research | 24 retrievals per research tranche | 16k tokens per result; 96k per tranche |

Budgets are soft ceilings, not correctness limits. Start a new increment or
escalate the mode with a one-line reason when the remaining evidence cannot
support a safe decision.

## Retrieval Rules

1. Start with the local knowledge index, project note, handoff, or compact
   inventory query when they cover the task.
2. Prefer code graph or symbol lookup, then the smallest live source snippet.
3. Use broad search only when narrow retrieval missed a required fact, caller,
   path, owner, or compatibility constraint.
4. In `token_efficient`, allow at most one broad scan per increment and record
   why it was needed. In `deep_research`, bound every scan by a declared source
   set and question.
5. Do not use memory or budget pressure to avoid a required live check.

## Verification Ladder

Select the smallest ladder rung that proves the requested behavior, then
escalate when risk or impact requires it. Exact command mappings remain owned by
the Phase 70 verification-profile task.

| Profile | Intended use |
|---|---|
| `focused` | Changed symbol, targeted test, script parse, or schema check |
| `surface` | User-facing component or route behavior, including relevant interaction checks |
| `full` | Cross-module behavior or broad contract confidence |
| `release` | Release, deploy, security-sensitive, or explicitly requested final gate |

## Screenshot Policy

- `standard`: inspect one key desktop view after visual changes; add mobile only
  when responsive layout can change.
- `token_efficient`: skip screenshots for non-visual changes; otherwise inspect
  one key view and capture more only for a visual defect or interaction.
- `deep_research`: capture the smallest desktop/mobile/interaction evidence set
  needed to answer the research question; do not generate visual evidence by
  default.

## Escalation Rules

Escalate to `standard` or `deep_research` when a task crosses trust boundaries,
security or privacy concerns, unfamiliar architecture, multiple owners, or a
failed focused check. Escalate verification to `full` or `release` when a
change affects public APIs, persistence, billing, authentication, deployment,
or user-visible release behavior.

Record mode, any broad-read justification, selected verification profile, and
escalation reason in [[agent-report-contract]] when a durable report is needed.

## Related Notes

- [[query-memory]]
- [[code-graph-bridge]]
- [[agent-report-contract]]
- [[../known-issues/memory-must-not-replace-verification]]
