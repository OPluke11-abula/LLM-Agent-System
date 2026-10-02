# Token-Efficient Mode Advisory Rollout

## Purpose

Roll out Phase 70 as advisory-only telemetry and workflow guidance. The mode
reports context cost, lookup choices, verification level, and handoff pressure;
it does not archive, delete, compact, trim, or mutate session state.

## Governance Matrix

| Contract | Evidence |
|---|---|
| Report-only preflight | `ContextBudgetReport` keeps `report_only=true` and `trimming_applied=false` |
| Profile selection | `TokenEfficientProfile.verification_profile` accepts only focused, surface, full, or release |
| Structural lookup first | [[structural-lookup-first]] requires bounded broad-read justification |
| Verification mapping | [[verification-profiles]] maps every profile to live commands |
| Handoff thresholds | [[handoff-first-long-session]] reports each threshold reason without writing a handoff automatically |
| Viewer visibility | Mission Control displays the advisory token-mode rail without changing runtime behavior |

## Rollout Controls

1. Keep the profile optional so existing conductor plans serialize and route as
   before when no profile is supplied.
2. Keep recommendations informational. Do not automatically trim tool payloads,
   compact history, create handoffs, change verification profiles, or rebuild a
   code graph.
3. Require live verification before reporting a profile or rollout as passing.
4. Record failures as evidence and leave the mode non-blocking until a future
   phase explicitly authorizes enforcement.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest --no-cov -q agent_workspace/tests/test_token_efficient_governance.py agent_workspace/tests/test_context_budget_preflight.py agent_workspace/tests/test_conductor_plan.py
npm.cmd --prefix viewer run build
npm.cmd --prefix viewer run verify:ui
.\scripts\verify.cmd
git diff --check
```

## Related Notes

- [[token-efficient-work-mode]]
- [[context-budget-preflight]]
- [[structural-lookup-first]]
- [[verification-profiles]]
- [[handoff-first-long-session]]
