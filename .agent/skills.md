# Skills Entry Point

This file is the PAP-facing skill registry for LAS.

LAS discovers executable tools from `agent_workspace/skills/*.py` through
Pydantic model reflection. This document maps those runtime tools to portable
skill contracts.

## Runtime Skill Modules

| Skill | Runtime module | Function | Contract |
| --- | --- | --- | --- |
| `calculate` | `agent_workspace/skills/example_skill_template.py` | `calculate` | `.agent/skills/calculate.md` |
| `transfer_agent` | `agent_workspace/skills/transfer_agent.py` | `transfer_agent` | `.agent/skills/transfer_agent.md` |

## Adding New Skills

1. Add or update a Python module under `agent_workspace/skills/`.
2. Expose a function whose first argument is a Pydantic `BaseModel`.
3. Let `AgentEngine` reflect the tool schema.
4. Add the skill name to `tools:` in `.agent/agent.md`.
5. Add a matching `.agent/skills/<skill_name>.md` contract.

## 中文說明

LAS 的可執行工具仍由 `agent_workspace/skills/*.py` 提供，並透過 Pydantic
自動反射成 tool schema。本文件只是 PAP-facing registry，負責把 runtime tool
映射到可攜式 skill contract。
