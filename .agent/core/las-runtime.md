# LAS Runtime Boundary

LAS is PAP-compatible through the `.agent/` workspace contract while keeping
the engine implementation in `agent_workspace/core/`.

## Core Runtime Responsibilities

- `AgentEngine`: discovers knowledge and Pydantic tools.
- `AgentRouter`: owns intent routing, session memory, provider calls, and the closed loop.
- `providers.py`: normalizes LLM provider calls.

## Adapter Responsibilities

- `api.py`: REST and SSE service layer.
- `topology_bridge.py`: topology state serialization.
- `topology_stream.py`: non-invasive stream wrapper for topology events.

## Rule

PAP documents describe portable contracts. They must not become a hidden second
runtime that bypasses LAS authorization, tool reflection, or state-machine
behavior.

## 中文說明

LAS 的核心 runtime 留在 `agent_workspace/core/`。`.agent/` 只定義可攜式合約，
方便人和 AI 安全接手 repo；它不能繞過 LAS 的授權、工具反射或 closed-loop 行為。
