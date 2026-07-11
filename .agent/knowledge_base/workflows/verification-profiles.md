# Layered Verification Profiles

## Purpose

Select the smallest verification profile that proves the changed behavior, then
escalate when the change crosses a larger surface or release boundary. Profiles
are advisory and report-only; they do not skip required checks or mutate state.

## Profiles

| Profile | Use when | Required checks |
|---|---|---|
| `focused` | One symbol, helper, schema, or workflow changed | Targeted pytest or script parse; targeted `git diff --check -- <paths>` |
| `surface` | Viewer component, route, or interaction changed | `npm.cmd --prefix viewer run build`; `npm.cmd --prefix viewer run verify:ui`; add `npm.cmd --prefix viewer run verify:ui:screenshots` when visual evidence is required; targeted diff check |
| `full` | Cross-module behavior or shared contracts changed | `./scripts/verify.cmd`; full `pytest --no-cov`; viewer build and smoke checks; repository-wide `git diff --check` |
| `release` | Release, deployment, security-sensitive, or explicitly final gate | `full` profile plus screenshot QA for affected surfaces, explicit branch/status check, and any release-specific security or deployment gate |

## Selection Rules

1. Start at `focused` when the changed surface is narrow and isolated.
2. Escalate to `surface` for user-visible viewer behavior or interaction state.
3. Escalate to `full` for shared runtime contracts, persistence, APIs, or
   changes spanning backend and viewer.
4. Use `release` only for an explicit final gate, release/deploy action, or
   security-sensitive change.
5. If a lower profile fails, preserve the failure evidence and rerun the next
   profile after the cause is addressed.

## Evidence Contract

Record the selected profile, exact commands, exit results, and escalation reason
in [[agent-report-contract]] or a handoff. A profile label is not a pass claim:
the commands must run in the current checkout. Keep screenshot evidence to the
minimum desktop/mobile/interaction set required by the visual change.

## Related Notes

- [[token-efficient-work-mode]]
- [[agent-report-contract]]
- [[maintenance]]
