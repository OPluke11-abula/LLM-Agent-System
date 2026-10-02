# LAS Routing Entry Point

Status: PAP entrypoint

This file is the concise routing index for agents that have already loaded `.agent/agent.md`.

## Onboarding Order

1. Read `.agent/agent.md` for hard rules, runtime identity, tools, entrypoints, and memory tiers.
2. Read `.agent/skills.md` only for the skills relevant to the current task.
3. Read `.agent/agent_tasks.md` for the active phase and task status.
4. Read `.agent/workflows.md` for the workflow governance document that matches the current stage.
5. Read this routing file when selecting an execution path.

## Routing Rules

- Planning or architecture: use static repo evidence first, then update the relevant plan or task record.
- Code generation or bug fixing: keep changes scoped, add or update focused tests, and run the narrow gate before broader verification.
- Security work: load `docs/workflow/SECURITY_REVIEW_GATE.md`, redact secrets, and record evidence in structured findings when needed.
- Handoff work: use `.agent/handoff_guide.md` and `docs/workflow/HANDOFF_SCHEMA.md`.
- Workflow work: validate `.agent/workflows/codex-development.yaml` with `agent_workspace/workflow_lint.py`.
- Review-gate work: validate review/security finding artifacts with `agent_workspace/review_findings_validate.py`.

## Verification

Before marking a routed task complete, run the smallest relevant command and record the exact result in `.agent/agent_tasks.md`. For repository-wide completion, run `.\scripts\verify.cmd`.
