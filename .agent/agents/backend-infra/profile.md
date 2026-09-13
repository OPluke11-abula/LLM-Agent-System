# BACKEND_INFRA_AGENT Profile

**Class**: `REPOSITORY_EXECUTOR`
**Primary Human Owner**: Ethan
**Assigned Scope**: `agent_workspace/core/`, `agent_workspace/db/`, `agent_workspace/api/`

## Mounted Skills
- **Antigravity Skills**: `resource-lifecycle-debug`, `diagnose`, `systematic-debugging`, `obsidian-vault`, `obsidian-research-notes`
- **Codex Skills**: `sqlite`, `codebase-design`, `obsidian-research-notes`

## Hard Invariants & Prohibitions
- **Prohibited**: Modifying React/Tauri frontend components, or leaking raw SQL to presentation layer.
- **Enforced**: Clean service boundaries, typed failures, SQLite FTS5 integrity, and resource lifecycle leak prevention.
