# Project Intake Workflow

## Purpose

Create a compact project memory page that helps agents orient quickly without repeatedly scanning the same repository surface.

## Procedure

1. Confirm the path is a git repository.
2. Read repo instructions first: `AGENTS.md`, `.agent/README.md`, README, or equivalent.
3. Record branch, HEAD, and dirty working tree count.
4. Prefer code graph tooling when an index exists.
5. Read the smallest useful metadata set: README, package manifests, pyproject, requirements, scripts, and app entrypoints.
6. Write or update a project page under `.agent/knowledge_base/projects/`.
7. Update `.agent/knowledge_base/index.md`.
8. Append to `.agent/knowledge_base/log.md`.
9. Run a sensitive-value scan over new notes.

## Required Fields

- Repo path
- Branch and HEAD
- Dirty working tree status
- Primary language/runtime
- Main source areas
- Test/build commands
- Runtime entrypoints
- Architecture pointers
- What to read first next time
- Live verification caveat

## Related Notes

- [[../projects/LLM-Agent-System]]
- [[query-memory]]
- [[handoff]]
