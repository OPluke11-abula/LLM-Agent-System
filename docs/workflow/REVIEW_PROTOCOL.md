# Review Protocol

Status: active workflow governance

This document defines LAS review behavior for code, docs, schemas, and PAP contracts.

## Review Stance

Review is validation first. The reviewer should identify bugs, regressions, missing tests, security risks, and contract drift before summarizing improvements.

Findings must include:

- severity
- file path and line or symbol when available
- observed behavior
- expected behavior
- impact
- remediation direction

## Reviewer Boundaries

- Reviewers report; they do not silently make broad fixes.
- If asked to fix review findings, keep edits scoped to validated issues.
- Do not flag designed behavior as a bug.
- Do not report hardening preferences as vulnerabilities unless there is a plausible exploit path and impact.

## Required Checks

Before saying a change is ready:

- Re-read touched files or the staged diff.
- Run focused tests for the changed behavior.
- Run schema/manifest checks when PAP contracts, tools, workflows, or `.agent` files changed.
- Run full verification when shared runtime behavior changed.
- Report commands actually run and their results.

## Security Review Trigger

Use a structured security review when a task changes:

- auth or authorization
- secrets or token handling
- database queries or migrations
- external integrations or webhooks
- file upload, parsers, command execution, sandbox, or path handling
- high-impact policy gates

Security findings require:

- entrypoint trace
- propagation trace when applicable
- sink trace
- exploit or abuse path
- impact
- validation status
