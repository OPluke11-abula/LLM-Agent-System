# Memory Entry Point

LAS currently uses local memory under `agent_workspace/memory/`.

## Working Memory

- Backend: local JSON files
- Runtime owner: `AgentRouter` / `MemoryManager`
- Path: `agent_workspace/memory/<session_id>.json`
- Scope: short-term conversation history per session

## Long-Term Memory

- Backend: local JSON file
- Runtime owner: `LongTermMemoryStore`
- Path: `agent_workspace/memory/long_term_memory.json`
- Write trigger: `AgentRouter._on_memory_limit_reached()`
- Query surfaces:
  - CLI: `python agent_workspace/long_term_memory.py query --q "<text>"`
  - API: `GET /v1/memory/query?q=<text>`

The local store uses deterministic summaries and keyword retrieval. It is the
development adapter that keeps the contract stable before a vector database is
introduced.

## Long-Term Memory Direction

Future long-term memory should remain PAP-compatible by documenting:

- memory backend
- write format
- retention policy
- user/session identity boundaries
- vector store configuration when Qdrant, Chroma, or Weaviate is introduced

## 中文說明

目前 LAS 使用 `agent_workspace/memory/` 中的本機 JSON 檔作為 working memory。
當 session working memory 超過保留上限時，`AgentRouter` 會透過
`LongTermMemoryStore` 寫入 `agent_workspace/memory/long_term_memory.json`。

目前 long-term store 使用 deterministic summary 與 keyword retrieval。未來改接
Qdrant、Chroma 或 Weaviate 時，需在這裡記錄 backend、寫入格式、保留策略、身份
邊界與向量資料庫設定。
