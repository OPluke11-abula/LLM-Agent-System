# Semantic Retrieval Pilot Plan - 2026-07-03

## Summary

This plan defines a staged retrieval pilot for LAS-local agent memory. It keeps the first implementation Markdown-only and read-only, then leaves clear gates for a later local index, embeddings, or Obsidian plugin pilot.

No plugin was installed, no embeddings were generated, and `.obsidian/` was not edited.

## Why This Matters

LAS now has a local `.agent/knowledge_base/` surface. Agents can use it as a durable orientation layer, but broad manual reading still costs time and context. Retrieval should make the first-read set smaller while preserving live verification for current state.

## Proposed Flow

1. Start with `.agent/knowledge_base/index.md`.
2. Search Markdown titles, headings, and body text.
3. Return candidate notes with reasons and confidence.
4. Read only the best candidates.
5. Verify current claims live before reporting success.
6. Capture proof under `.agent/knowledge_base/evidence/` when needed.

## Stage Gates

Stage 0:

- Use direct Markdown search.
- No generated index.
- No embeddings.
- No external provider.

Stage 1:

- Add a local text inventory or SQLite FTS only after Stage 0 proves useful.
- Keep the inventory inside `.agent/knowledge_base/` or another documented local cache.

Stage 2:

- Add embeddings only after explicit approval.
- Exclude sensitive paths.
- Record model, provider, storage path, and rollback instructions.

Stage 3:

- Pilot Obsidian Smart Connections only after explicit approval and `.obsidian/` backup.
- Keep Copilot and Auto Note Mover deferred unless separately approved.

## Retrieval Result Contract

Every retrieval answer should distinguish:

- retrieval candidates
- evidence from durable notes
- current live verification
- facts not verified in the current turn

## Pilot Queries

- `memory must not replace verification`
- `evidence capture workflow`
- `LAS viewer verification commands`
- `project intake workflow`
- `handoff workflow`
- `semantic retrieval plugin risks`

## Guardrails

- Retrieval is not proof.
- Do not index secrets or private runtime state.
- Do not send vault or repo memory to an external provider without approval.
- Do not install plugins during this pilot.
- Do not edit existing dirty LAS files outside `.agent/knowledge_base/`.

## Related Notes

- [[../workflows/semantic-retrieval-pilot]]
- [[../workflows/query-memory]]
- [[../workflows/evidence-capture]]
- [[../known-issues/memory-must-not-replace-verification]]
