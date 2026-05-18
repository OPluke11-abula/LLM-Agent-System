# Skills Entry Point

This file is the PAP-facing skill registry for LAS.

LAS discovers executable tools from `agent_workspace/skills/*.py` through
Pydantic model reflection. This document maps runtime tools to portable skill
contracts.

## Runtime Skill Modules

| Skill | Runtime module | Function | Contract |
| --- | --- | --- | --- |
| `delegate_task` | `agent_workspace/skills/delegate_task.py` | `delegate_task` | `.agent/skills/delegate_task.md` |
| `calculate` | `agent_workspace/skills/example_skill_template.py` | `calculate` | `.agent/skills/calculate.md` |
| `transfer_agent` | `agent_workspace/skills/transfer_agent.py` | `transfer_agent` | `.agent/skills/transfer_agent.md` |

## Adding New Skills

1. Add or update a Python module under `agent_workspace/skills/`.
2. Expose a function whose first argument is a Pydantic `BaseModel`.
3. Let `AgentEngine` reflect the tool schema.
4. Run `python agent_workspace/tool_manifest.py sync` to update contracts.
5. Review and refine generated `.agent/skills/<skill_name>.md` files.

## Contract Rule

Runtime tools and PAP skill contracts must remain one-to-one. A tool without a
contract is not AI-maintainable; a contract without a runtime tool is stale.
Run `python agent_workspace/tool_manifest.py validate` before release.

## 中文說明

LAS 會從 `agent_workspace/skills/*.py` 反射可執行工具，並用本文件把 runtime
工具對應到 `.agent/skills/*.md` 的 PAP contract。新增工具後請執行 `sync`，
再人工檢查安全邊界與輸入輸出格式。
