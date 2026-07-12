# LAS Agent Knowledge Index

## Purpose

This index is the first-read map for LAS-local agent knowledge. It mirrors the Obsidian Vault OS pattern in a repo-local `.agent/knowledge_base/` surface so agents can orient quickly without re-reading broad project context.

This memory is orientation, not proof. Always verify current repo, code graph, config, dependency, test, and build state live before claiming success.

## Start Here

- [[projects/LLM-Agent-System]]
- [[known-issues/memory-must-not-replace-verification]]
- [[workflows/project-intake]]
- [[workflows/query-memory]]
- [[workflows/handoff]]
- [[workflows/maintenance]]
- [[workflows/semantic-retrieval-pilot]]
- [[workflows/session-journal]]
- [[workflows/local-knowledge-inventory]]
- [[workflows/knowledge-inventory-refresh]]
- [[workflows/inventory-backed-query]]
- [[workflows/context-pack-builder]]
- [[workflows/context-pack-validation]]
- [[workflows/visual-reference-moodboard]]
- [[workflows/visual-asset-illustration-pipeline]]
- [[workflows/independent-design-review-gate]]
- [[workflows/agent-start-preflight]]
- [[workflows/preflight-adoption-guide]]
- [[workflows/knowledge-base-health-audit]]
- [[workflows/knowledge-index-repair]]
- [[workflows/obsidian-mirror-index-repair]]
- [[workflows/obsidian-vault-health-audit]]
- [[workflows/obsidian-log-link-repair]]
- [[workflows/inventory-ranking-tuning]]

- [[workflows/obsidian-root-scratch-triage]]
- [[workflows/knowledge-base-git-hygiene]]
- [[workflows/explicit-kb-commit-package-dry-run]]
## Project Intakes

- [[projects/LLM-Agent-System]]

## Workflows

- [[workflows/project-intake]]
- [[workflows/query-memory]]
- [[workflows/handoff]]
- [[workflows/maintenance]]
- [[workflows/evidence-capture]]
- [[workflows/evidence-memory-bridge]]
- [[workflows/code-graph-bridge]]
- [[workflows/structural-lookup-first]]
- [[workflows/agent-report-contract]]
- [[workflows/token-efficient-work-mode]]
- [[workflows/token-efficient-rollout]]
- [[workflows/verification-profiles]]
- [[workflows/independent-design-review-gate]]
- [[workflows/handoff-first-long-session]]
- [[workflows/context-budget-preflight]]
- [[workflows/semantic-retrieval-pilot]]
- [[workflows/session-journal]]
- [[workflows/local-knowledge-inventory]]
- [[workflows/knowledge-inventory-refresh]]
- [[workflows/inventory-backed-query]]
- [[workflows/context-pack-builder]]
- [[workflows/context-pack-validation]]
- [[workflows/visual-reference-moodboard]]
- [[workflows/agent-start-preflight]]
- [[workflows/preflight-adoption-guide]]
- [[workflows/knowledge-base-health-audit]]
- [[workflows/knowledge-index-repair]]
- [[workflows/obsidian-mirror-index-repair]]
- [[workflows/obsidian-vault-health-audit]]
- [[workflows/obsidian-log-link-repair]]
- [[workflows/inventory-ranking-tuning]]

## Wiki

- Future durable concept notes should be written under `wiki/`.

## Templates

- [[templates/handoff-report]]
- [[templates/evidence-memory-summary]]
- [[templates/agent-report]]
- [[templates/query-memory-report]]
- [[templates/design-review-report]]

## Decisions

- [[decisions/local-markdown-agent-os]]

## Known Issues

- [[known-issues/memory-must-not-replace-verification]]

## Handoffs

- Future handoffs should be written under `handoffs/`.
- [[handoffs/session-journal-2026-07-03-obsidian-las-workflows]]
- Future context packs should be written under `handoffs/` with `context-pack-` filenames.
- [[handoffs/context-pack-latest-inventory-refresh]]
- [[handoffs/agent-start-preflight-latest-context-pack-validation]]
- [[handoffs/agent-start-preflight-latest-preflight-adoption-guide]]
- [[handoffs/agent-start-preflight-latest-index-repair]]
- [[handoffs/agent-start-preflight-latest-obsidian-mirror-index-repair]]
- [[handoffs/agent-start-preflight-latest-obsidian-vault-health-audit]]
- [[handoffs/agent-start-preflight-latest-obsidian-log-link-repair]]

- [[handoffs/agent-start-preflight-latest-obsidian-root-scratch-triage]]
- [[handoffs/agent-start-preflight-latest-knowledge-base-git-hygiene]]
- [[handoffs/agent-start-preflight-latest-explicit-kb-commit-package-dry-run]]
## Evidence

- [[evidence/2026-07-03-git-status-knowledge-base-sync]]

## Indexes

- [[indexes/knowledge-inventory-2026-07-03]]
- [[indexes/knowledge-inventory-latest]]

## Exports

- [[exports/obsidian-vault-os-brief-for-las]]
- [[exports/semantic-retrieval-pilot-plan]]
- [[exports/session-journal-flow-report-2026-07-03]]
- [[exports/inventory-backed-query-flow-report-2026-07-03]]
- [[exports/context-pack-builder-flow-report-2026-07-03]]
- [[exports/context-pack-validation-flow-report-2026-07-03]]
- [[exports/agent-start-preflight-flow-report-2026-07-03]]
- [[exports/preflight-adoption-guide-flow-report-2026-07-03]]
- [[exports/knowledge-base-health-audit-flow-report-2026-07-03]]
- [[exports/knowledge-index-repair-flow-report-2026-07-03]]
- [[exports/obsidian-mirror-index-repair-flow-report-2026-07-03]]
- [[exports/obsidian-vault-health-audit-flow-report-2026-07-03]]
- [[exports/obsidian-log-link-repair-flow-report-2026-07-03]]
- [[exports/inventory-ranking-tuning-flow-report-2026-07-03]]

- [[exports/obsidian-root-scratch-triage-flow-report-2026-07-04]]
- [[exports/knowledge-base-git-hygiene-flow-report-2026-07-04]]
- [[exports/explicit-kb-commit-package-dry-run-report-2026-07-04]]
- [[exports/phase-67-design-critique-flow-report-2026-07-07]]
- [[exports/phase-71-las-viewer-art-direction-packet-2026-07-07]]
- [[exports/phase-71-screen-composition-studies-2026-07-07]]
- [[exports/release-0.1.1-five-core-rules-review-2026-07-12]]
## Verification Commands

Use the smallest relevant check first:

```powershell
python agent_workspace/tool_manifest.py validate
.\scripts\verify.cmd -SkipViewer
.\scripts\verify.cmd
```

For viewer work:

```powershell
cd viewer
npm run build
npm run verify:ui
npm run test:swarm-ui
npm run doctor
```

## Current Caveats

- This knowledge base was synced from Obsidian on 2026-07-03.
- LAS worktree was dirty at sync time; run `git status --short` before edits.
- The existing `.agent/knowledge_base/index.json` was not changed by this sync.
- Raw command evidence should be stored under `evidence/` and cited from summaries.

## Source

- Obsidian export: `C:/Users/luke2/OneDrive/??刻麾/Obsidian Vault/exports/AI Agent Development Knowledge for LAS - 2026-07-02.md`
