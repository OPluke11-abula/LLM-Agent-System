# Local Knowledge Inventory Workflow

## Purpose

Build a small local inventory of Markdown knowledge notes so agents can rank likely files before reading them.

This is Stage 1 after the semantic retrieval pilot. It improves over naive full-text search by indexing title, path, note type, headings, wikilinks, and search cues without storing full note bodies.

## Scope

In scope:

- `.agent/knowledge_base/**/*.md`
- title and heading extraction
- wikilink extraction
- note type classification by folder
- lightweight search cues
- a human-readable inventory under `.agent/knowledge_base/indexes/`

Out of scope:

- embeddings
- external model calls
- Obsidian plugin installation
- indexing `.env`, database, cache, workspace, dependency, or generated build files
- replacing live verification

## Procedure

1. Read `.agent/knowledge_base/index.md`.
2. Enumerate Markdown files under approved folders.
3. Exclude raw logs or sensitive paths unless explicitly approved.
4. For each note, extract:
   - relative path
   - title
   - note type
   - top headings
   - wikilinks
   - short search cues
5. Write the inventory under `.agent/knowledge_base/indexes/`.
6. Link the inventory from `.agent/knowledge_base/index.md`.
7. Append one `.agent/knowledge_base/log.md` entry.
8. Run credential-value and whitespace checks.

## Ranking Rules

Prefer candidates in this order:

1. exact title match
2. path segment match
3. heading match
4. wikilink match
5. search cue match
6. broad body search as fallback

`index.md` and `log.md` should help navigation, but they should not outrank a specific workflow, known issue, decision, project note, handoff, evidence note, or export.

## Query Output Contract

```markdown
## Query

## Ranked Candidates

- path:
  title:
  why:
  confidence:
  read_first:

## Verification Needed
```

## Refresh Triggers

Refresh the inventory when:

- new workflows, decisions, known issues, handoffs, evidence, or exports are added
- a note title or major heading changes
- retrieval repeatedly returns `index.md` or `log.md` before specific notes
- a future embedding or plugin pilot needs a clean corpus manifest

## Safety

- Retrieval is orientation, not proof.
- Do not index credential values or private runtime state.
- Do not send inventory data to external providers without explicit approval.
- Keep generated inventory compact and reviewable.

## Related Notes

- [[../index]]
- [[semantic-retrieval-pilot]]
- [[query-memory]]
- [[../indexes/knowledge-inventory-2026-07-03]]
- [[../known-issues/memory-must-not-replace-verification]]
