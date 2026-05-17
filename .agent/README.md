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
- `.agent/memory.md`: documents session memory and future long-term memory alignment.
- `.agent/workflows.md`: documents CLI, API, and topology workflows.

### Layer 3: Detail Directories

- `.agent/skills/`: per-tool contracts for existing LAS tools.
- `.agent/core/`: runtime boundary notes.
- `.agent/prompts/`, `.agent/memory/`, `.agent/workflows/`, `.agent/knowledge_base/`: reserved for deeper PAP-aligned guidance.

## Runtime Boundary

The PAP workspace is documentation and contract surface. It does not replace
the LAS engine. Engine behavior remains in `agent_workspace/core/`, and
runtime integrations stay in external adapters such as `agent_workspace/api.py`
and `agent_workspace/topology_stream.py`.

## 中文說明

這個 `.agent/` 目錄讓 LAS 在 workspace contract 層級正式 PAP-compatible。
它說明可攜式 Agent 如何在本 repo 中找到工具、提示詞、記憶、工作流程與長期
專案知識。

PAP workspace 是協定面與文件面，不取代引擎。LAS 核心仍位於
`agent_workspace/core/`；API 與 topology 這類整合能力維持在外部 adapter。
