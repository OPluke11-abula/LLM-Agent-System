# Knowledge Base Git Hygiene

## Purpose

Package LAS local knowledge-base changes for review without mixing them with unrelated coordination or runtime artifacts.

## Mode

This is a git `STATUS` workflow. It inspects and reports commit boundaries. It does not stage, commit, rebase, push, reset, delete, or hide files.

## Trigger

Use this workflow when `.agent/knowledge_base/` has many untracked files and an agent needs to decide what belongs in a durable commit package.

## Durable Knowledge Package

The durable package can include:

- `.agent/knowledge_base/index.md`
- `.agent/knowledge_base/log.md`
- `.agent/knowledge_base/projects/`
- `.agent/knowledge_base/workflows/`
- `.agent/knowledge_base/decisions/`
- `.agent/knowledge_base/known-issues/`
- `.agent/knowledge_base/evidence/`
- `.agent/knowledge_base/exports/`
- `.agent/knowledge_base/tools/`
- `.agent/knowledge_base/indexes/`
- `.agent/knowledge_base/handoffs/`

Current health tooling treats `indexes/knowledge-inventory-latest.json` as part of the QA surface. Do not ignore `indexes/` unless the linter contract is changed to refresh before audit.

## Exclude From This Package

- `.agent/agent_tasks.md`
- `.agent/programmer/agent_tasks.md`
- unrelated `.agent/agent.md` edits unless a separate task asks to package them
- `.agent/codebase-memory/*.sqlite*`
- local runtime caches, databases, logs, or generated binary state

## Procedure

1. Run `git status --short -- .agent .gitignore`.
2. Run `git ls-files .agent/knowledge_base .agent/agent_tasks.md .agent/programmer/agent_tasks.md .agent/agent.md .gitignore`.
3. Run `git status --ignored --short -- .agent/knowledge_base .agent/codebase-memory .gitignore`.
4. List `.agent/knowledge_base` files and classify them as durable source, generated QA surface, or excluded runtime state.
5. Run LAS knowledge-base audit and Obsidian vault audit before claiming the package is reviewable.
6. Run `git diff --check -- .agent/knowledge_base`.
7. If the user asks for a commit, use a separate commit workflow and stage only the reviewed package paths.

## Notes

- `.gitignore` does not hide already tracked files. Use `git update-index --skip-worktree` only with explicit approval for local coordination files.
- A clean knowledge-base audit is not proof that repo code/tests pass.
- This workflow is intentionally packaging-only.

## Related Notes

- [[workflows/knowledge-base-health-audit]]
- [[workflows/knowledge-index-repair]]
- [[workflows/agent-start-preflight]]
