# Evidence Capture Workflow

## Purpose

Capture raw command, test, and tool output as durable evidence references while keeping agent summaries compact.

Use this workflow when a task needs proof of current state, such as git status, validation output, tests, build logs, CLI version checks, or security scans.

## Core Rule

Evidence is not the same as interpretation.

- Store raw or lightly bounded output under `.agent/knowledge_base/evidence/`.
- Store the summary in handoffs, reports, or project notes.
- Cite the evidence path from the summary.
- Re-run live checks before claiming current success.

## Output Shape

Evidence note:

```markdown
# Evidence - <Topic> - YYYY-MM-DD

## Command
## Working Directory
## Exit Code
## Captured Output
## Interpretation
## Caveats
## Related Notes
```

## Procedure

1. Run the smallest command that proves the claim.
2. Capture command, cwd, date, exit code, and bounded output.
3. Redact secrets before writing an evidence note.
4. Write the evidence note under `.agent/knowledge_base/evidence/`.
5. Reference the evidence note from reports or handoffs.
6. Update `.agent/knowledge_base/log.md`.
7. Run a sensitive-value scan over the new evidence note.

## Evidence IDs

Use stable, readable filenames:

```text
YYYY-MM-DD-<topic>.md
```

Examples:

- `2026-07-03-git-status-knowledge-base-sync.md`
- `2026-07-03-tool-manifest-validate.md`
- `2026-07-03-viewer-build.md`

## What To Capture

- command and arguments
- working directory
- exit code
- relevant stdout/stderr
- truncation note, if output was bounded
- interpretation
- caveats

## What Not To Capture

- API keys, tokens, cookies, credentials, private payment details
- huge logs without bounds
- full proprietary source dumps when a file path and line reference is enough
- unredacted environment dumps

## Related Notes

- [[../index]]
- [[query-memory]]
- [[handoff]]
- [[../known-issues/memory-must-not-replace-verification]]
