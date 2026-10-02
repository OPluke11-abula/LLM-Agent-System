---
tags:
  - memory/crdt
  - persistence/sqlite
  - fts5/search
type: memory_os
layer: L4-Cognitive-and-Memory-OS
sync_status: verified
---

# 4-Tier Memory OS & SQLite FTS5 Persistence Topology (40)

> **Parent Index**: [[00 LLM-Agent-System Index]]
> **Related Architecture**: [[10 7-Layer System Architecture & Control Plane Topology]]
> **Primary Source Files**: `agent_workspace/core/memory.py`, `.agent/memory/`

---

## 1. 4-Tier Memory Hierarchy

LAS implements an enterprise-grade, bounded-context Memory OS to eliminate memory leaks and context explosion:

```mermaid
graph TD
    classDef t1 fill:#1e293b,stroke:#f43f5e,stroke-width:2px,color:#f8fafc;
    classDef t2 fill:#1e293b,stroke:#f59e0b,stroke-width:2px,color:#f8fafc;
    classDef t3 fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#f8fafc;
    classDef t4 fill:#1e293b,stroke:#34d399,stroke-width:2px,color:#f8fafc;

    M1["Tier 1: Ephemeral Memory<br/>- In-memory execution scratchpad<br/>- Task-scoped context, discarded on completion"]:::t1
    M2["Tier 2: Session Memory<br/>- SQLite message history & turn state<br/>- Session lifetime, bounded rolling window"]:::t2
    M3["Tier 3: Persistent Memory<br/>- SQLite FTS5 Full-Text Index & BM25<br/>- Long-term verified facts, cross-session search"]:::t3
    M4["Tier 4: Shared Knowledge OS<br/>- Obsidian Vault & .agent/knowledge_base/<br/>- Architecture topology notes & ADR graph"]:::t4

    M1 -->|Session Checkpoint| M2
    M2 -->|Fact Extraction & Compaction| M3
    M3 -->|Durable Knowledge Synthesis| M4
```

---

## 2. Tier Details & Storage Backends

| Tier | Name | Backend | Retention Policy | Primary Source |
|---|---|---|---|---|
| **1** | Ephemeral | In-Memory (`dict` / `list`) | Discarded on turn end | `agent_workspace/core/engine.py` |
| **2** | Session | SQLite (`sessions.db`) | Retained per session | `agent_workspace/core/memory.py` |
| **3** | Persistent | SQLite FTS5 (`fts5_memory.db`) | Durable, indexed with BM25 | `agent_workspace/core/memory.py` |
| **4** | Shared | Markdown Files + Obsidian Vault | Durable Git & Local Vault | `.agent/knowledge_base/`, `docs/obsidian/` |

---

## 3. Context Budget Preflight & Compaction

- **Token Budgeting**: Prompts check available token budget before LLM dispatch (`context_budget_preflight.py`).
- **Bounded Compaction**: Long conversation histories are automatically compacted into structured episodic summaries (`log_compactor.py`), preventing context overflow while preserving essential facts.

---

## 4. Persistence Engine & SQLite Concurrency Hardening (Phase 97)

All SQLite persistence engines backing Tier 2 and Tier 3 (`memory.py`, `audit_ledger.py`, `runtime_events.py`, `mission_store.py`, `ledger.py`, `replay_logger.py`) operate under the unified Phase 97 concurrency profile:
- **Journal Mode**: `PRAGMA journal_mode = WAL` (Write-Ahead Logging) allowing non-blocking concurrent reads during writes.
- **Synchronization**: `PRAGMA synchronous = NORMAL` providing crash durability with minimized filesystem sync latency.
- **Busy Timeout**: `PRAGMA busy_timeout = 5000` (5,000ms spin-wait) eliminating Windows file locking deadlocks.
- **Re-entrant Lock**: Protected by `threading.RLock()` ensuring thread-safe cross-turn execution in multi-agent environments.
