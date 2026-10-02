---
protocol_version: "3.8.0"
min_runtime_version: "0.1.0"
name: las-developer-agent
version: "0.8.0"
purpose: >
  Universal Protocol v3.8.0 compatible LAS developer and multi-agent coordination contract
  for scoped planning, implementation, verification, and three-tier handoff work.
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
  - three-tier-relay
  - grounded-roles
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
  - generative_spec_generator
schema_evolution:
  allow_self_evolution: false
  strict_forward_compatibility: true
protocol:
  root: .agent/
  manifest: .agent/agent.md
  entrypoints:
    overview: .agent/README.md
    state: .agent/state.md
    ownership: .agent/ownership.md
    decisions: .agent/decisions.md
    versions: .agent/versions.md
    test_policy: .agent/test_policy.md
    skills: .agent/skills.md
    prompts: .agent/prompts.md
    memory: .agent/memory.md
    workflows: .agent/workflows.md
    tasks: .agent/agent_tasks.md
    routing: .agent/routing.md
    handoff: handoff.md
  directories:
    core: .agent/core/
    skills: .agent/skills/
    prompts: .agent/prompts/
    memory: .agent/memory/
    workflows: .agent/workflows/
    knowledge_base: .agent/knowledge_base/
    agents: .agent/agents/
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

# LAS Multi-Agent Operating Contract

Read this file as the durable project-wide operating contract (Protocol v3.8.0).
For task details, use `.agent/agent_tasks.md`; for design rules, use `viewer/DESIGN.md`; for workflow details, use `docs/DEVELOPMENT_WORKFLOW_GUIDE.md`.

## 1. Operating Invariants

1. **Protocol Identity & Coordination Mode**:
   - Strictly verify `.agent/state.md` Protocol Baseline matches `3.8.0`.
   - Operate under `STATIC_DOMAIN_OWNERSHIP` unless explicitly transferred by PO Luke.
2. **Boundary & Responsibility Discipline**:
   - Keep core runtime behavior in `agent_workspace/core/`; put API, CLI, serialization, UI, and bridge behavior in adapters or dedicated modules.
   - Respect `.agent/ownership.md`. Modifying files outside your assigned domain is strictly prohibited.
3. **Anti-Summary Invariant (調研先行)**:
   - Must directly inspect primary source files (code, schemas) before formulating technical proposals or plans. Cite exact files and line ranges.
4. **Stop-and-Wait Architecture Gate**:
   - Submit a structured diff plan and edge-case analysis. STOP and obtain explicit Human approval before touching code.
5. **Seven Anti-Corruption Invariants**:
   - Zero Dead Code; Single Responsibility; Concurrency & Race Elimination (`latest-request-wins`); Typed Failures Only; Spec-First; Idempotency; Configuration over Hardcoding.
6. **Three-Tier Cognitive Relay**:
   - Tier 1: `stage.md` (local scratchpad, strictly gitignored).
   - Tier 2: `handoff.md` + Git (team cognitive relay, 3-line summary, test green prerequisite).
   - Tier 3: `docs/obsidian/` + Vault (knowledge topology, 3-line concise code annotations on leaf notes).
7. **Verification Ladder**:
   - Evidence before completion. Report exact checks run with five objective status labels: `PASS`, `FAIL`, `BLOCKED`, `NOT_RUN`, `UNVERIFIED`.

## 2. External-State Guardrails

- Do not stage, commit, push, deploy, install hooks, or enable CI/blocking external actions without explicit user approval.
- Keep security and registry/hub actions report-only unless a task explicitly asks for mutation and verification.
- Redact secrets and avoid printing raw credentials from configs, registries, reports, or generated artifacts.
