# Explicit KB Commit Package Dry Run

## Purpose

Prepare the exact `.agent/knowledge_base/` package that could be staged in a later explicit commit workflow, without staging or committing it now.

## Mode

This is a git `STATUS` workflow. It only inspects the working tree and writes a manifest/report. It does not stage, commit, rebase, push, reset, delete, or hide files.

## Package Command

```bash
git add --dry-run .agent/knowledge_base
```

The real staging command is intentionally not run in this workflow. If the user explicitly asks for the commit, use a separate commit workflow and then run:

```bash
git add .agent/knowledge_base
git diff --cached --name-only
git diff --cached --stat
```

## Exclusions

The dry-run package must not include:

- `.agent/agent_tasks.md`
- `.agent/programmer/agent_tasks.md`
- unrelated `.agent/agent.md` edits
- `.agent/codebase-memory/*.sqlite*`
- `.gitignore`, unless a later task explicitly changes ignore policy

## Verification

1. Confirm current branch.
2. Confirm no staged changes before dry-run.
3. Confirm `git add --dry-run .agent/knowledge_base` includes only package paths.
4. Run LAS knowledge-base audit and Obsidian vault audit.
5. Run `git diff --check -- .agent/knowledge_base`.
6. Record that no staging/commit occurred.

## Related Notes

- [[workflows/knowledge-base-git-hygiene]]
- [[workflows/agent-start-preflight]]
