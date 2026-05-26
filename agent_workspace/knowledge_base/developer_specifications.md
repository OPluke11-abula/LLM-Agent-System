---
id: developer_specifications
title: "LAS Developer Specifications"
description: "Active API endpoints, CLI subcommands, memory configurations, and roadmap details for AI Agent reference."
creator: "FindAi Studio Core Team"
version: "1.0.0"
tags:
  - api
  - cli
  - configurations
  - roadmap
  - specifications
---

# LAS Developer Specifications

This document serves as the single source of truth for AI Programmer Agents to discover and manage runtime interfaces, CLI parameters, and environment settings.

---

## 1. CLI Command Reference (Unified Developer CLI)

The developer CLI toolbelt is located at `agent_workspace/cli.py`. The following subcommands and flags are fully implemented and must be used for system operations:

* **List Skills**: `python agent_workspace/cli.py --list-skills` (displays all local and global PAP tools).
* **Describe Skill**: `python agent_workspace/cli.py --describe-skill <SKILL_ID>` (prints contract schema).
* **Validate Contracts**: `python agent_workspace/cli.py --validate` (runs static schema alignment checks).
* **Memory Read**: `python agent_workspace/cli.py --session <ID> --memory-read <KEY>` (queries persistent records).
* **Memory Write**: `python agent_workspace/cli.py --session <ID> --memory-write <KEY> <VALUE>` (writes persistent records).
* **Run Workflow**: `python agent_workspace/cli.py --session <ID> --run-workflow <WORKFLOW_ID>` (executes step DAG).
* **Resume Workflow**: `python agent_workspace/cli.py --session <ID> --run-workflow <WORKFLOW_ID> --resume` (resumes from failed checkpoint).
* **Bootstrap Scaffold**: `python agent_workspace/cli.py init [path]` (creates standard skeleton).
* **Linter**: `python agent_workspace/cli.py lint [path] [--fix]` (statically checks reference integrity).
* **Debate Loop**: `python agent_workspace/cli.py run-debate --topic <TOPIC> --agents <ROLES> --rounds <N>` (moderates debates).
* **Interactive Chat**: `python agent_workspace/cli.py --chat` (runs interactive closed-loop session).
* **Single Stream**: `python agent_workspace/cli.py --stream <MESSAGE>` (streams single execution).

---

## 2. API Endpoints Map

The FastAPI service adapter runs from `agent_workspace/api.py`. It exposes the following runtime endpoints:

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/v1/health` | Service status, active provider, readiness indicators |
| `GET` | `/v1/tools` | Reflects live tool list verified against PAP schemas |
| `POST` | `/v1/chat` | Synchronous agent turn-taking request (supports custom `account_id`) |
| `POST` | `/v1/stream` | Server-Sent Events (SSE) streaming token output & HITL events |
| `WS` | `/v1/stream_ws` | Bidirectional WebSockets streaming for live dashboard telemetry |
| `WS` | `/v1/stream` | Multi-turn WebSocket chat session streaming |
| `POST` | `/v1/task` | Asynchronous task queue submission |
| `GET` | `/v1/session/{id}` | Fetches topological session state & completed task outcomes |
| `GET` | `/v1/memory` | Retrieves long-term persistent memory records |
| `GET` | `/v1/memory/query` | Semantic/keyword query searches across long-term memory |
| `GET` | `/v1/metrics` | Exposes Prometheus runtime telemetry metrics |
| `GET/PUT` | `/v1/config` | Dynamically queries/modifies active LLM provider configurations |
| `GET` | `/v1/accounts` | Lists configured provider credentials and token statistics |
| `POST` | `/v1/accounts` | Adds or updates a provider credential dynamically |
| `DELETE` | `/v1/accounts/{id}` | Removes a configured provider credential |
| `GET` | `/v1/accounts/active` | Retrieves the currently active provider credential ID |
| `POST` | `/v1/accounts/active` | Swaps the active provider account dynamically |
| `POST` | `/v1/sessions/{session_id}/approve` | Grants interactive human approval for paused HITL gates |
| `POST` | `/v1/sessions/{session_id}/reject` | Denies human approval for paused HITL gates |

---

## 3. Pluggable Memory Configuration

LAS is dual-backend compliant (SQLite by default, Redis for enterprise scalability). It resolves endpoints based on active environment variables:

* **Default (SQLite)**: Writes thread-safe records directly to SQLite DB.
* **Redis Activation**: Configure the following environment variables:
  - `MEMORY_BACKEND="redis"`
  - `REDIS_URL="redis://localhost:6379"` (or the appropriate remote connection string).

---

## 4. Product Roadmap Status

All planned core development phases are fully implemented, verified green, and committed:

* **Phase 0 & 3 (Foundation & Quality)**: Strict linter, contract schemas, path traversal prevention, & green pytest suite.
* **Phase 1 & 2 (Protocol & Tooling)**: Asynchronous workflow engine with checkpoints, handoffs, and CLI subcommands.
* **Phase 4 & 5 (UX & RAG)**: Drag-and-drop React Flow dashboard canvas, PAP workflow exports, & pure-Python semantic TF-IDF search.
* **Phase 6 & 7 (Enterprise & Multi-Agent)**: Multi-account credentials storage, real-time token tracking, and consensus debate rooms.
* **Phase 8 & 9 (Observability & Safety)**: Visual Dagre polish, dynamic HSL edges, interactive HITL gate endpoints, and dynamic RBAC.
* **Phase 11 (Swarm Company)**: Multi-dashboard views (CEO, Dev, Auditor), org charts, & concurrent WS streaming.
