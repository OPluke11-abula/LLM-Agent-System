# Source Of Truth Policy

Status: active workflow governance

This document defines how LAS agents resolve conflicting instructions and project facts during implementation, review, and handoff work.

## Priority Order

Use this order when sources disagree:

1. Latest explicit user instruction in the current thread.
2. System, developer, and active AGENTS instructions.
3. Repo-local `.agent/agent.md` and PAP entry documents.
4. The active task spec or `.agent/agent_tasks.md` item.
5. Architecture and workflow docs under `docs/`.
6. Existing code, tests, schemas, and manifests.
7. README, comments, and historical notes.
8. Memory-derived context, only after live verification when facts may have drifted.

## Operating Rules

- Re-open files from disk when the user asks for current state, review, or continuation.
- Treat generated summaries as pointers, not proof.
- Prefer exact local paths, commands, hashes, test output, and diff evidence.
- If a memory or handoff note conflicts with the repository, verify the repository first.
- Do not present unrun checks as passing.

## Evidence Requirements

Claims about implementation status must cite at least one live source:

- file path and relevant symbol or line
- command and result
- schema validation result
- test output
- git diff or commit hash

## Scope Rules

- Keep changes inside the active task scope.
- Do not rewrite unrelated docs, manifests, generated files, or user changes.
- For cross-repo work, explicitly state which repo is being changed and which repo is only being referenced.
- PAP protocol changes should be backward compatible unless a breaking-change task explicitly authorizes otherwise.
