# Risk Policy

Status: active workflow governance

This document defines how LAS agents classify task risk and choose the required gates.

## Risk Levels

### Low

Examples:

- documentation-only edits
- tests for existing behavior
- small UI copy or layout refinements
- read-only scans

Default gates:

- focused verification relevant to the touched files
- `git diff --check`

### Medium

Examples:

- new schemas or validators
- runtime behavior behind existing boundaries
- changes to routing metadata, telemetry, or memory records
- non-sensitive API additions

Default gates:

- focused tests
- contract or schema validation
- `git diff --check`
- full repo gate when shared behavior is touched

### High

Examples:

- authentication or authorization
- secrets, credentials, tokens, or signatures
- billing, quotas, subscriptions, or external API side effects
- database migrations
- file parsing, upload, command execution, sandbox, or path handling
- deploy, push, destructive filesystem actions, or external-state changes

Default gates:

- focused tests covering fail-closed behavior
- security review or structured findings when relevant
- `UnifiedPolicyGate` for runtime sensitive actions
- full `scripts\verify.cmd` when the repo behavior changes
- explicit user approval for pushes, deploys, destructive actions, or external side effects

## Approval Boundaries

Agents may proceed without asking for routine scoped implementation work. Ask or request approval when:

- the action mutates external state
- the action is destructive
- the task requires credentials or secrets
- the implementation choice would break compatibility
- the task would exceed the user's stated scope

## Security Rules

- Fail closed for unknown roles, scopes, tools, certificates, and policy decisions.
- Do not log secret values; log metadata keys, hashes, or refs instead.
- Do not run exploit code against third-party systems.
- Do not install hooks, daemons, runtime patches, or global configuration without explicit approval.
