# LAS Knowledge Inventory - 2026-07-03

## Purpose

This inventory ranks LAS-local knowledge notes by title, path, note type, headings, and search cues. It is a token-saving map, not a source of proof.

## Corpus

- Root: `D:/GitHub/LLM-Agent-System/.agent/knowledge_base`
- Included: Markdown notes under `projects/`, `workflows/`, `decisions/`, `known-issues/`, `handoffs/`, `evidence/`, `exports/`, and root navigation notes.
- Excluded: non-Markdown files, databases, dependency folders, caches, runtime state, and secret-bearing paths.
- Generated: 2026-07-03

## Ranking Hints

- Prefer exact title, path, and heading matches over broad body matches.
- Treat `index.md` and `log.md` as routers, not final answers.
- Read the smallest specific note first.
- Verify current repo, config, tool, test, and build claims live.

## Inventory

### projects/LLM-Agent-System.md

- Type: project
- Title: LLM Agent System
- Headings: Summary; Snapshot From Obsidian Intake; Start Here; Architecture Pointers; High-Value Symbols; Route Pointers; Common Commands
- Links: ../index; ../known-issues/memory-must-not-replace-verification; ../workflows/project-intake
- Search cues: LAS overview, architecture, commands, routes, symbols, project intake

### workflows/query-memory.md

- Type: workflow
- Title: Query Memory Workflow
- Headings: Purpose; Procedure; Answer Contract; Memory-Derived; Verified Now; Not Verified; Next
- Links: ../known-issues/memory-must-not-replace-verification; project-intake
- Search cues: query, local memory, answer contract, verified now, not verified

### workflows/semantic-retrieval-pilot.md

- Type: workflow
- Title: Semantic Retrieval Pilot Workflow
- Headings: Purpose; Scope; Stages; Stage 0 - Markdown Baseline; Stage 1 - Local Text Inventory; Stage 2 - Embedding Pilot; Stage 3 - Obsidian Plugin Pilot
- Links: ../index; query-memory; evidence-capture; ../known-issues/memory-must-not-replace-verification; ../exports/semantic-retrieval-pilot-plan
- Search cues: semantic retrieval, local text inventory, embeddings, Smart Connections, plugin risks

### workflows/local-knowledge-inventory.md

- Type: workflow
- Title: Local Knowledge Inventory Workflow
- Headings: Purpose; Scope; Procedure; Ranking Rules; Query Output Contract; Refresh Triggers; Safety
- Links: ../index; semantic-retrieval-pilot; query-memory; ../indexes/knowledge-inventory-2026-07-03; ../known-issues/memory-must-not-replace-verification
- Search cues: inventory, ranking, title weighting, path weighting, headings, wikilinks

### workflows/evidence-capture.md

- Type: workflow
- Title: Evidence Capture Workflow
- Headings: Purpose; Core Rule; Output Shape; Command; Working Directory; Exit Code; Captured Output
- Links: ../index; query-memory; handoff; ../known-issues/memory-must-not-replace-verification
- Search cues: evidence, command output, verification, captured output, proof

### workflows/session-journal.md

- Type: workflow
- Title: Session Journal Workflow
- Headings: Purpose; Relationship To Handoffs; Output Shape; Required Sections; Procedure; Quality Bar; Related Notes
- Links: ../index; handoff; evidence-capture; semantic-retrieval-pilot; ../known-issues/memory-must-not-replace-verification
- Search cues: session journal, low-token start, next agent, changed on disk

### workflows/handoff.md

- Type: workflow
- Title: Handoff Workflow
- Headings: Purpose; Required Sections; Procedure; Quality Bar; Related Notes
- Links: query-memory; maintenance
- Search cues: handoff, resume, next agent, changed files, verified commands

### workflows/project-intake.md

- Type: workflow
- Title: Project Intake Workflow
- Headings: Purpose; Procedure; Required Fields; Related Notes
- Links: ../projects/LLM-Agent-System; query-memory; handoff
- Search cues: project intake, repository orientation, required fields

### workflows/maintenance.md

- Type: workflow
- Title: Maintenance Workflow
- Headings: Purpose; Checks; Modification Policy; Related Notes
- Links: ../index; ../known-issues/memory-must-not-replace-verification
- Search cues: maintenance, lint, health checks, modification policy

### known-issues/memory-must-not-replace-verification.md

- Type: known issue
- Title: Known Issue - Memory Must Not Replace Verification
- Headings: Symptom; Cause; Fix Or Workaround; Verification; Related Notes
- Links: ../index; ../workflows/query-memory; ../workflows/handoff
- Search cues: stale memory, live verification, proof, current state

### decisions/local-markdown-agent-os.md

- Type: decision
- Title: Decision - Local Markdown Agent OS
- Headings: Decision; Context; Reasoning; Consequences; Revisit When; Related Notes
- Links: ../index; ../workflows/query-memory; ../known-issues/memory-must-not-replace-verification
- Search cues: local Markdown, agent OS, decision, revisit criteria

### evidence/2026-07-03-git-status-knowledge-base-sync.md

- Type: evidence
- Title: Evidence - Git Status For Knowledge Base Sync - 2026-07-03
- Headings: Command; Working Directory; Exit Code; Captured Output; Interpretation; Caveats; Related Notes
- Links: ../workflows/evidence-capture; ../index; ../known-issues/memory-must-not-replace-verification
- Search cues: git status, dirty worktree, knowledge-base sync, evidence

### handoffs/session-journal-2026-07-03-obsidian-las-workflows.md

- Type: handoff
- Title: Session Journal - Obsidian LAS Workflows - 2026-07-03
- Headings: Session Goal; Changed On Disk; Evidence And Reports; Verified Now; Not Verified; Decisions; Next Agent Start Here
- Links: ../exports/session-journal-flow-report-2026-07-03
- Search cues: session journal, Obsidian LAS workflows, next agent start

### exports/obsidian-vault-os-brief-for-las.md

- Type: export
- Title: Obsidian Vault OS Brief For LAS
- Headings: Summary; Transferable Pattern; Initial LAS Sync; Next Implementation Step; Source
- Links: none
- Search cues: Obsidian Vault OS, LAS optimization, transferable pattern

### exports/semantic-retrieval-pilot-plan.md

- Type: export
- Title: Semantic Retrieval Pilot Plan - 2026-07-03
- Headings: Summary; Why This Matters; Proposed Flow; Stage Gates; Retrieval Result Contract; Pilot Queries; Guardrails
- Links: ../workflows/semantic-retrieval-pilot; ../workflows/query-memory; ../workflows/evidence-capture; ../known-issues/memory-must-not-replace-verification
- Search cues: retrieval plan, Stage 0, Stage 1, embeddings, Smart Connections

### exports/session-journal-flow-report-2026-07-03.md

- Type: export
- Title: Session Journal Flow Report - 2026-07-03
- Headings: Summary; LAS Files Created; LAS Files Updated; Obsidian Mirror; Not Changed; Verification; Related Notes
- Links: ../workflows/session-journal; ../handoffs/session-journal-2026-07-03-obsidian-las-workflows; ../workflows/handoff; ../workflows/evidence-capture
- Search cues: session journal flow, verification, Obsidian mirror

### index.md

- Type: router
- Title: LAS Agent Knowledge Index
- Headings: Purpose; Start Here; Project Intakes; Workflows; Decisions; Known Issues; Handoffs; Evidence; Exports; Verification Commands
- Links: projects/LLM-Agent-System; known-issues/memory-must-not-replace-verification; workflows/project-intake; workflows/query-memory; workflows/handoff; workflows/maintenance; workflows/semantic-retrieval-pilot; workflows/session-journal
- Search cues: start here, router, verification commands, knowledge map

### log.md

- Type: audit log
- Title: LAS Agent Knowledge Log
- Headings: 2026-07-03
- Links: workflows/evidence-capture; evidence/2026-07-03-git-status-knowledge-base-sync; workflows/semantic-retrieval-pilot; exports/semantic-retrieval-pilot-plan; workflows/session-journal; handoffs/session-journal-2026-07-03-obsidian-las-workflows
- Search cues: operation history, audit trail, latest workflow changes

### lessons_learned.md

- Type: legacy lessons
- Title: FindAi Studio LAS Self-Learning Experience & Lessons Learned Registry
- Headings: Active Resolution Directory; Lesson ID entries for task mocking, SQLite locks, React Flow resize loop, dynamic workspace paths, context bloat, concurrency balancing
- Links: none
- Search cues: lessons learned, self-learning registry, context bloat, historical issues

## Pilot Query Results

### Query: memory must not replace verification

Read first:

1. `known-issues/memory-must-not-replace-verification.md`
2. `workflows/query-memory.md`
3. `workflows/evidence-capture.md`

Why: exact title and known-issue path should outrank `index.md`.

### Query: semantic retrieval plugin risks

Read first:

1. `workflows/semantic-retrieval-pilot.md`
2. `exports/semantic-retrieval-pilot-plan.md`

Why: exact workflow and export match Stage 2 and Stage 3 risks.

### Query: next agent start

Read first:

1. `workflows/session-journal.md`
2. `handoffs/session-journal-2026-07-03-obsidian-las-workflows.md`
3. `workflows/handoff.md`

Why: session journal and handoff workflows own resume behavior.

## Caveats

- This is a hand-reviewed pilot inventory, not an automated indexer.
- It should be refreshed after new workflows or reports are added.
- It does not prove that any repo code, tests, builds, or tools currently pass.
