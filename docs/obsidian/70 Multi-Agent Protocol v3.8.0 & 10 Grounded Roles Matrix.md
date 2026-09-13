---
tags:
  - protocol/v3-8-0
  - roles/grounding
  - multi-agent/governance
type: protocol_matrix
layer: L2-Protocol-and-Contract-Gateways
sync_status: verified
---

# Multi-Agent Protocol v3.8.0 & 10 Grounded Roles Matrix (70)

> **Parent Index**: [[00 LLM-Agent-System Index]]
> **Related Architecture**: [[20 Feature DAG & Feature-Based Ownership Topology]]
> **Canonical Protocol Reference**: `Universal_Coding_Agent_Development_Protocol.md` (v3.8.0) Section 1.1

---

## 1. Universal Baseline Memory Invariant

To ensure all agents natively understand repository wiki links, knowledge DAGs, and local memory vault structures:
> **All Roles 1~10 mount `obsidian-vault` and `obsidian-research-notes` as mandatory baseline cognitive skills.**

---

## 2. The 10 Specialized Roles & Host Skill Grounding

| # | Role Name | Execution Class | Scope & Responsibilities | Host Skill Grounding | Hard Invariants & Prohibitions |
|---|---|---|---|---|---|
| **1** | `UI_UX_AGENT` | `REPOSITORY_EXECUTOR` | Frontend presentation, widget hierarchy, aesthetics | Antigravity: `frontend-design`, `aesthetic-design-system`, `theme-factory`, `canvas-design`, **`obsidian-vault`**, **`obsidian-research-notes`**<br/>Codex: `figma`, `figma-implement-design`, `figma-code-connect-components`, `frontend-skill` | Prohibited from touching SQL, migrations, backend IPC, or core runtime logic. |
| **2** | `BACKEND_INFRA_AGENT` | `REPOSITORY_EXECUTOR` | Backend services, persistence, migrations, IPC | Antigravity: `resource-lifecycle-debug`, `diagnose`, `systematic-debugging`, **`obsidian-vault`**, **`obsidian-research-notes`**<br/>Codex: `sqlite`, `codebase-design` | Prohibited from writing presentation UI or leaking raw SQL to presentation layer. |
| **3** | `DOMAIN_LOGIC_AGENT` | `REPOSITORY_EXECUTOR` | Pure business algorithms, domain entities, value objects | Antigravity: `agent-rules-books`, `brainstorming`, `tdd`, **`obsidian-vault`**, **`obsidian-research-notes`**<br/>Codex: `domain-modeling`, `codebase-design` | Framework-agnostic by definition. Zero UI, Win32, or concrete ORM dependencies allowed in domain core. |
| **4** | `APPLICATION_FLOW_AGENT` | `REPOSITORY_EXECUTOR` | Orchestration, state management, concurrency control | Antigravity: `systematic-debugging`, `dispatching-parallel-agents`, **`obsidian-vault`**, **`obsidian-research-notes`**<br/>Codex: `speech`, `transcribe`, `diagnosing-bugs` | Prohibited from direct SQL or raw native OS calls. Must enforce `latest-request-wins` race elimination. |
| **5** | `INTEGRATION_MERGE_AGENT` | `REPOSITORY_EXECUTOR` | Branch cherry-picking, integration, merge conflicts | Antigravity: `finishing-a-development-branch`, `using-git-worktrees`, `git-guardrails-claude-code`, **`obsidian-vault`**, **`obsidian-research-notes`**<br/>Codex: `resolving-merge-conflicts`, `gh-address-comments`, `gh-fix-ci` | Never perform untested fast-forward merges. Must pass full global regression gates before merge. |
| **6** | `SECURITY_AUDIT_AGENT` | `REPOSITORY_REVIEWER` | Security posture, vulnerability scanning, threat modeling | Antigravity: `security-audit`, `threat-model`, `pentest`, `incident-response`, `skillspector`, **`obsidian-vault`**, **`obsidian-research-notes`**<br/>Codex: `codex-security-scan`, `codex-security-diff-scan`, `codex-security-validate`, `codex-security-fix` | Read-only audit authority. Scans for plaintext credentials, injection flaws, and clipboard/IPC leakage. |
| **7** | `PERFORMANCE_LATENCY_AGENT` | `REPOSITORY_REVIEWER` | Latency profiling, memory/thread leaks, IPC overhead | Antigravity: `resource-lifecycle-debug`, `diagnose`, **`obsidian-vault`**, **`obsidian-research-notes`**<br/>Codex: profiling skills | Resource lifecycle governance. Investigates thread lockups, connection leaks, IPC roundtrips, and token overhead. |
| **8** | `QA_TEST_AGENT` | `REPOSITORY_REVIEWER` | Automated regression testing, test suite design, coverage | Antigravity: `test-driven-development`, `tdd`, `brooks-test`, `verification-before-completion`, **`obsidian-vault`**, **`obsidian-research-notes`**<br/>Codex: `tdd`, `karpathy-review-lite`, `playwright-interactive` | Evidence before completion invariant. Must run actual test commands and attach verified receipts. |
| **9** | `ARCHITECT_PLANNER_AGENT` | `ADVISORY_SPECIALIST` | High-level system RFCs, modular dependency graphs, plans | Antigravity: `writing-plans`, `executing-plans`, `iterative-planner`, `improve-codebase-architecture`, **`obsidian-vault`**, **`obsidian-research-notes`**<br/>Codex: `momus.toml` (Deep Plan Reviewer) | Non-coding advisory role. Formulates RFCs/Plans; validates them against Deep Plan Reviewer (`momus`) before handoff. |
| **10** | `KNOWLEDGE_TOPOLOGY_AGENT` | `OPS` / `ADVISORY` | Knowledge graph topology, Obsidian/Notion sync, anti-rot | Antigravity: **`obsidian-vault`**, **`obsidian-research-notes`**, `token-optimization`, `caveman`, `notion`<br/>Codex: `notion-knowledge-capture`, `token-efficient-handoff`, `claude-handoff` | Knowledge integrity guardian. Synchronizes documentation and local Obsidian vaults; prunes dead docs and verifies freshness. |
