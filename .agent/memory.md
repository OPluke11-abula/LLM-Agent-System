# Memory Entry Point

LAS currently uses local session memory under `agent_workspace/memory/`.

## Working Memory

- Backend: local JSON files
- Runtime owner: `AgentRouter` / `MemoryManager`
- Path: `agent_workspace/memory/<session_id>.json`
- Scope: short-term conversation history per session

## Long-Term Memory Direction

Future long-term memory should remain PAP-compatible by documenting:

- memory backend
- write format
- retention policy
- user/session identity boundaries
- vector store configuration when Qdrant, Chroma, or Weaviate is introduced

## 中文說明

目前 LAS 使用 `agent_workspace/memory/` 中的本機 JSON 檔作為 working memory。
未來加入長期語意記憶時，需在這裡記錄 backend、寫入格式、保留策略、身份邊界
與向量資料庫設定。
