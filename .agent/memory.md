# Memory Entry Point

LAS currently uses local memory under `agent_workspace/memory/`.

## Working Memory

- Backend: local JSON files
- Runtime owner: `AgentRouter` / `MemoryManager`
- Path: `agent_workspace/memory/<session_id>.json`
- Scope: short-term conversation history per session

## Long-Term Memory

- Backend: pluggable via `MemoryBackend` abstract contract
- Default backend: `SQLiteBackend` (`agent_workspace/memory/long_term_memory.db`)
- Runtime owner: `LongTermMemoryStore`
- Write trigger: `AgentRouter._on_memory_limit_reached()`
- Query surfaces:
  - CLI: `python agent_workspace/long_term_memory.py query --q "<text>"`
  - API: `GET /v1/memory/query?q=<text>`

### Backend contract

Every long-term memory backend implements three methods:

```
write(session_id, key, value)   — persist a record
read(session_id, key)           — retrieve a single record
search(query, session_id, top_k) — full-text or semantic search
```

Backends are registered in `agent_workspace/memory_backends.py` and selected
via `config.yaml`:

```yaml
memory:
  long_term_enabled: true
  backend: "sqlite"        # or "qdrant", "chroma", "weaviate" (future)
```

### SQLiteBackend details

- Uses FTS5 virtual table for full-text keyword search.
- WAL journal mode for concurrent reads.
- Thread-safe via connection-per-thread pattern.
- Zero extra dependencies (Python stdlib `sqlite3`).

## Long-Term Memory Direction

Future long-term memory should remain PAP-compatible by documenting:

- memory backend
- write format
- retention policy
- user/session identity boundaries
- vector store configuration when Qdrant, Chroma, or Weaviate is introduced

When a vector backend is added, implement `MemoryBackend` and register it in
`_BACKEND_REGISTRY` inside `memory_backends.py`. No changes to
`LongTermMemoryStore`, `AgentRouter`, or `api.py` are needed.

## 中文說明

目前 LAS 使用 `agent_workspace/memory/` 中的本機檔案作為 working memory。
當 session working memory 超過保留上限時，`AgentRouter` 會透過
`LongTermMemoryStore` 寫入 long-term store。

Long-term store 已升級為可插拔的 Backend 架構：
- 預設使用 `SQLiteBackend`（`long_term_memory.db`），內建 FTS5 全文搜尋。
- 透過 `config.yaml` 的 `memory.backend` 欄位切換 backend。
- 未來改接 Qdrant、Chroma 或 Weaviate 時，只需實作 `MemoryBackend` 介面並
  註冊到 `_BACKEND_REGISTRY`，無需修改 core 或 API 層程式碼。
