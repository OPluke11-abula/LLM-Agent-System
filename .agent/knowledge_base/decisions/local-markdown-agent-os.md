# Decision - Local Markdown Agent OS

## Decision

Use `.agent/knowledge_base/` as a local Markdown operating layer for LAS agents.

## Context

Obsidian Vault OS showed that agent memory becomes more useful when source capture, compiled project knowledge, handoffs, decisions, known issues, exports, and maintenance are explicit local files.

## Reasoning

- Markdown is portable, inspectable, and agent-friendly.
- LAS already has `.agent/` as a PAP-compatible contract surface.
- A local `index.md` can reduce repeated project discovery.
- A local `log.md` can keep agent operations auditable.
- Plain files are safer to pilot before adding embeddings or plugin automation.

## Consequences

- Agents should read `.agent/knowledge_base/index.md` before broad repo exploration.
- Durable project knowledge belongs under `.agent/knowledge_base/projects/`.
- Recurring failure patterns belong under `.agent/knowledge_base/known-issues/`.
- Every meaningful knowledge-base update should append to `.agent/knowledge_base/log.md`.

## Revisit When

- LAS adds a runtime CLI for knowledge-base queries.
- LAS adopts semantic retrieval or embedding search.
- The knowledge base grows beyond simple Markdown navigation.
- PAP workflow manifests are generated from these Markdown workflows.

## Related Notes

- [[../index]]
- [[../workflows/query-memory]]
- [[../known-issues/memory-must-not-replace-verification]]
