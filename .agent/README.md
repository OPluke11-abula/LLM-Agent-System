# LAS PAP Workspace

This `.agent/` directory makes LAS explicitly PAP-compatible at the workspace
contract level. It documents how portable agents should discover tools,
prompts, memory, workflows, and project knowledge in this repository.

## Three Layers

### Layer 1: Manifest

`.agent/agent.md` is the protocol source of truth. It declares the PAP version,
workspace identity, enabled tools, and declared protocol paths.

### Layer 2: Runtime Entry Documents

- `.agent/skills.md`: maps LAS runtime tools to PAP skill contracts.
- `.agent/prompts.md`: explains how `agent_workspace/agent.jinja2` is used.
- `.agent/memory.md`: documents working memory and long-term memory direction.
- `.agent/workflows.md`: documents CLI, API, validation, and topology workflows.

### Layer 3: Detail Directories

- `.agent/skills/`: per-tool contracts for existing LAS tools.
- `.agent/core/`: runtime boundary notes.
- `.agent/prompts/`, `.agent/memory/`, `.agent/workflows/`, `.agent/knowledge_base/`: reserved for deeper PAP-aligned guidance.

## Runtime Boundary

The PAP workspace is documentation and contract surface. It does not replace
the LAS engine. Engine behavior remains in `agent_workspace/core/`, and runtime
integrations stay in external adapters such as `agent_workspace/api.py` and
`agent_workspace/topology_stream.py`.

## 中文說明

`.agent/` 是 LAS 的 protocol contract surface，讓人和 AI 都能用一致方式理解
這個 repo 的工具、prompt、memory、workflow 與 runtime 邊界。它不是第二套
runtime，也不應繞過 `agent_workspace/core/` 的授權、工具反射或狀態機行為。
