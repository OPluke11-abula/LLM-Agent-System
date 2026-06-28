# Security Review Gate

Status: active workflow governance

This document defines the report-only security gate used by LAS workflow stages.

## Trigger Conditions

Run the structured security review gate when a task changes:

- auth or authorization behavior
- secrets, tokens, credentials, or key material
- database queries, migrations, persistence, or tenant filtering
- external APIs, webhooks, callbacks, or billing integrations
- file upload, file parsing, command execution, sandbox, or path handling
- `UnifiedPolicyGate`, ProofOfConsensus, high-impact routing, or policy decisions

## Required Artifact

Security review output must be JSON validated by:

```powershell
.\.venv\Scripts\python.exe agent_workspace\review_findings_validate.py --root . --input docs\reviews\sample-security-findings.json
```

The artifact must follow `spec/review-findings.schema.json` and include traceable findings:

- `entrypoint_trace`
- `propagation_trace` when applicable
- `sink_trace`
- `evidence`
- `impact`
- `remediation`
- `validation_status`

## Review Rules

- The gate is report-only unless a caller explicitly asks to fix findings.
- High or critical findings require concrete impact and declared security triggers.
- Evidence paths must stay inside the workspace.
- Defense-in-depth notes are not vulnerabilities unless they include a plausible abuse path and impact.
- Do not include secrets or credential values in findings. Cite file paths, symbols, keys, or metadata names instead.
- Do not execute third-party exploits or scan external systems.
