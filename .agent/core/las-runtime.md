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

LAS 透過 `.agent/` workspace contract 對齊 PAP，但引擎仍位於
`agent_workspace/core/`。PAP 文件描述可攜式契約，不應成為繞過 LAS 授權、工具
反射或閉環狀態機的第二套 runtime。
