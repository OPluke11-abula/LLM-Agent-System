# Memory Entry Point

LAS currently uses local memory under `agent_workspace/memory/`.

## Working Memory

- Backend: local JSON files
- Runtime owner: `AgentRouter` / `MemoryManager`
- Path: `agent_workspace/memory/<session_id>.json`
- Scope: short-term conversation history per session

## Long-Term Memory

- Backend: pluggable via the `MemoryBackend` abstract contract
- Default backend: `SQLiteBackend` (`agent_workspace/memory/long_term_memory.db`)
- Runtime owner: `LongTermMemoryStore`
- Write trigger: `AgentRouter._on_memory_limit_reached()`
- Query surfaces:
  - CLI: `python agent_workspace/long_term_memory.py query --q "<text>"`
  - API: `GET /v1/memory/query?q=<text>`

### Backend Contract

Every long-term memory backend implements these methods:

```text
write(session_id, key, value)     # persist a record
read(session_id, key)             # retrieve a single record
search(query, session_id, top_k)  # full-text or semantic search
all_records()                     # list stored records
```

Backends are registered in `agent_workspace/memory_backends.py` and selected
via `config.yaml`:

```yaml
memory:
  long_term_enabled: true
  backend: "sqlite"
```

## Governance Direction

Future memory work should make the store governable, not just searchable:

- memory type: episodic, semantic, user preference, or project memory
- retention and deletion policy
- source citation and source hash
- confidence score
- privacy boundary by user, session, project, and deployment
- backend configuration for future vector stores

## 中文說明

LAS 目前已有 working memory 與 long-term memory 的基礎。下一階段重點不是只做
keyword store，而是把 memory 做成可治理的產品能力：可刪除、可引用來源、可標示
信心分數，並能清楚區分使用者、專案與部署邊界。
