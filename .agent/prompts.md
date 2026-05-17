# Prompts Entry Point

LAS uses `agent_workspace/agent.jinja2` as the runtime prompt template.

The template receives context from:

- `knowledge_base/` markdown documents discovered by `AgentEngine`
- runtime variables such as `current_time`, `context_status`, `user_input`, and `session_id`
- conversation memory injected by the router

## Contract

- Prompt policy changes that affect runtime behavior should be documented here.
- Detailed prompt snippets can be added under `.agent/prompts/`.
- The actual executable template remains `agent_workspace/agent.jinja2`.

## 中文說明

LAS 的執行中 prompt template 是 `agent_workspace/agent.jinja2`。PAP 的
`.agent/prompts.md` 用來記錄 prompt contract 與演進規則；不把 prompt 邏輯搬離
現有 runtime。
