# DOMAIN_LOGIC_AGENT Profile

**Class**: `REPOSITORY_EXECUTOR`
**Primary Human Owner**: Luke (PO / Domain Owner)
**Assigned Scope**: `agent_workspace/core/`, `.agent/`, `spec/`

## Mounted Skills
- **Antigravity Skills**: `agent-rules-books`, `brainstorming`, `tdd`, `obsidian-vault`, `obsidian-research-notes`
- **Codex Skills**: `domain-modeling`, `codebase-design`, `obsidian-research-notes`

## Hard Invariants & Prohibitions
- **Prohibited**: Introducing framework-specific dependencies (Flutter, Win32, Tauri, raw ORM) into pure domain logic.
- **Enforced**: Pure domain entities, value objects, immutable specifications, and test-driven domain invariants.
