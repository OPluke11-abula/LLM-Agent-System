---
protocol_version: "1.0.0"
min_runtime_version: "0.1.0"
name: programmer-agent
version: "0.7.0"
purpose: >
  PAP-compatible LAS developer agent for scoped planning, implementation,
  verification, and handoff work.
description: >
  Maintains and extends the LLM Agent System with contract-first runtime,
  workflow, memory, security, and viewer changes while keeping context bounded.
language: en
authorization_level: interactive-approval
use_case_tags:
  - programmer-agent
  - pap-compatible
  - python
  - fastapi
  - react
  - tauri
  - codebase-memory
  - token-efficient
tools:
  - delegate_task
  - calculate
  - run_tests
  - verify_workspace
  - code_detect_change_impact
  - code_get_architecture
  - code_get_snippet
  - code_index_repo
  - code_search_symbol
  - code_trace_call_path
  - log_append
  - log_archive_month
  - log_compress_done
  - memory_query
  - memory_store_knowledge
  - memory_store_preference
  - workspace_add_task
  - workspace_cancel_task
  - workspace_link_tasks
  - workspace_render_topology
  - workspace_update_status
  - transfer_agent
  - governed_memory
  - structured_log
  - topological_workspace
schema_evolution:
  allow_self_evolution: false
  strict_forward_compatibility: true
protocol:
  root: .agent/
  manifest: .agent/agent.md
  entrypoints:
    overview: .agent/README.md
    skills: .agent/skills.md
    prompts: .agent/prompts.md
    memory: .agent/memory.md
    workflows: .agent/workflows.md
    tasks: .agent/agent_tasks.md
    routing: .agent/routing.md
    handoff: .agent/handoff_guide.md
  directories:
    core: .agent/core/
    skills: .agent/skills/
    prompts: .agent/prompts/
    memory: .agent/memory/
    workflows: .agent/workflows/
    knowledge_base: .agent/knowledge_base/
memory:
  backend: local
  tiers:
    ephemeral: in_memory
    session: in_memory
    persistent: sqlite
    shared: sqlite
  path: agent_workspace/memory/
prompts:
  path: .agent/prompts.md
workflows:
  path: .agent/workflows.md
---

# LAS PAP Agent Manifest

Read this file as the compact operating contract. For task details, use
`.agent/agent_tasks.md`; for design rules, use `viewer/DESIGN.md`; for workflow
details, use `.agent/workflows.md`.

## Operating Rules

1. Keep core runtime behavior in `agent_workspace/core/`; put API, CLI,
   serialization, UI, and bridge behavior in adapters or dedicated modules.
2. Keep Python skills and `.agent/skills/*.md` PAP contracts in parity. Validate
   tool manifests when skill contracts or runtime registration changes.
3. Prefer structural lookup first: code graph tools and bounded snippets before
   broad reads. Use broad scans only for non-code files, literals, configs, or
   stale/missing indexes.
4. Keep context compact. Summarize completed work, keep pending queues expanded,
   and create a handoff before long histories become the working memory.
5. Verify before claiming success. Report the exact checks run; never treat an
   unrun test, build, scan, or gate as passing.

## Current Queue Discipline

- Start from `.agent/agent_tasks.md` `Current Queue State`.
- Preserve queue order unless the user explicitly reprioritizes.
- As of the compacted task queue, return to Phase `68-02` before continuing
  Phase 71 implementation work.

## External-State Guardrails

- Do not stage, commit, push, deploy, install hooks, or enable CI/blocking
  external actions without explicit user approval.
- Keep security and registry/hub actions report-only unless a task explicitly
  asks for mutation and verification.
- Redact secrets and avoid printing raw credentials from configs, registries,
  reports, or generated artifacts.

## Verification Ladder

- Documentation or queue-only change: `git diff --check` plus PAP manifest
  validation when `.agent/agent.md` changes.
- Backend/runtime change: focused pytest first; expand to tool manifest and full
  repo verification at milestone boundaries.
- Viewer/UI change: focused build or marker check first; screenshot/mobile/full
  gates only when layout, interaction, or release confidence requires it.
