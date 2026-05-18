# Prompts Entry Point

LAS uses `agent_workspace/agent.jinja2` as the runtime prompt template.

The template receives context from:

- `knowledge_base/` Markdown documents discovered by `AgentEngine`
- runtime variables such as `current_time`, `context_status`, `user_input`, and `session_id`
- conversation memory injected by the router

## Contract

- Prompt policy changes that affect runtime behavior should be documented here.
- Detailed prompt snippets can be added under `.agent/prompts/`.
- The executable template remains `agent_workspace/agent.jinja2`.

## 中文說明

`.agent/prompts.md` 是 prompt contract，不是實際執行模板。真正被 runtime 使用的
模板仍是 `agent_workspace/agent.jinja2`。任何會改變 agent 行為的 prompt policy
都應在這裡留下可審計說明。
