# Semantic Retrieval Pilot Workflow

## Purpose

Test semantic retrieval as a staged agent-memory workflow without installing Obsidian plugins, creating embeddings, or editing `.obsidian/`.

The goal is to reduce repeated broad context reads while preserving the core rule: retrieval suggestions orient agents, but live checks prove current facts.

## Scope

In scope:

- search over `.agent/knowledge_base/` Markdown
- staged retrieval design for LAS-local notes
- query response format with evidence and confidence
- safety rules for future embedding or plugin pilots

Out of scope for this pilot:

- plugin installation
- embedding generation
- API-key setup
- indexing secrets, databases, caches, or raw private configs
- runtime code changes outside `.agent/knowledge_base/`

## Stages

### Stage 0 - Markdown Baseline

Use the existing Markdown knowledge base:

1. Read `.agent/knowledge_base/index.md`.
2. Search file names and note bodies under `.agent/knowledge_base/`.
3. Read the smallest useful set of matching notes.
4. Return candidates with the source path and a short reason.
5. Mark all results as retrieval suggestions until verified live.

### Stage 1 - Local Text Inventory

Build a local inventory later if Stage 0 is useful:

- note path
- title
- headings
- tags or explicit wikilinks
- last modified time
- short summary
- extracted keywords

This can support SQLite FTS or a small JSON index without embeddings.

### Stage 2 - Embedding Pilot

Only after explicit approval:

1. Define the model/provider and storage location.
2. Run a sensitive-value scan before indexing.
3. Exclude secret-bearing or generated-state paths.
4. Generate embeddings for approved Markdown files only.
5. Record cache paths and rollback steps.

### Stage 3 - Obsidian Plugin Pilot

Only after explicit approval and backup:

- evaluate Smart Connections first
- preserve `.obsidian/` backup
- install one plugin only
- record plugin ID and version
- document generated files or caches
- keep Copilot and Auto Note Mover deferred unless separately approved

## Exclusions

Never index:

- `.env`, `.env.*`
- `.sqlite`, `.db`, `.wal`, `.shm`
- `.obsidian/workspace*`
- token, cookie, credential, or key files
- raw logs that may contain secrets
- dependency folders and generated build output

## Query Contract

Each retrieval result should include:

```markdown
## Query

## Candidates

- path:
  reason:
  evidence:
  confidence: low | medium | high
  verification_needed:

## Verified Now

## Not Verified
```

## Pilot Queries

Use these to test retrieval quality:

- `memory must not replace verification`
- `evidence capture workflow`
- `LAS viewer verification commands`
- `project intake workflow`
- `handoff workflow`
- `semantic retrieval plugin risks`

## Acceptance Criteria

Stage 0 is useful if:

- the top candidates point to the expected workflow, decision, evidence, or known-issue notes
- the response cites paths instead of dumping full files
- stale memory is marked as unverified
- live checks are requested for current repo, tool, test, or plugin claims
- no secrets are printed or indexed

## Failure Handling

- If retrieval returns too many hits, narrow by folder first.
- If retrieval finds conflicting notes, prefer the newest `log.md` entry and mark the conflict.
- If no note matches, say the knowledge base has no durable memory for the topic and use live discovery only as needed.
- If a future embedding/plugin pilot creates generated state, document the state and rollback path before calling it complete.

## Related Notes

- [[../index]]
- [[query-memory]]
- [[evidence-capture]]
- [[../known-issues/memory-must-not-replace-verification]]
- [[../exports/semantic-retrieval-pilot-plan]]
