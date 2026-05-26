---
schema_version: "1.0.0"
---

# Skills Entry Point

This file is the PAP-facing skill registry for LAS.

LAS discovers executable tools from `agent_workspace/skills/*.py` through
Pydantic model reflection. This document maps those runtime tools to portable
skill contracts.

## Runtime Skill Modules

| Skill | Runtime module | Function | Contract |
| --- | --- | --- | --- |
| `delegate_task` | `agent_workspace/skills/delegate_task.py` | `delegate_task` | `.agent/skills/delegate_task.md` |
| `calculate` | `agent_workspace/skills/example_skill_template.py` | `calculate` | `.agent/skills/calculate.md` |
| `run_tests` | `agent_workspace/skills/system_verification.py` | `run_tests` | `.agent/skills/run_tests.md` |
| `verify_workspace` | `agent_workspace/skills/system_verification.py` | `verify_workspace` | `.agent/skills/verify_workspace.md` |
| `log_append` | `agent_workspace/skills/tool_log.py` | `log_append` | `.agent/skills/log_append.md` |
| `log_archive_month` | `agent_workspace/skills/tool_log.py` | `log_archive_month` | `.agent/skills/log_archive_month.md` |
| `log_compress_done` | `agent_workspace/skills/tool_log.py` | `log_compress_done` | `.agent/skills/log_compress_done.md` |
| `memory_query` | `agent_workspace/skills/tool_memory.py` | `memory_query` | `.agent/skills/memory_query.md` |
| `memory_store_knowledge` | `agent_workspace/skills/tool_memory.py` | `memory_store_knowledge` | `.agent/skills/memory_store_knowledge.md` |
| `memory_store_preference` | `agent_workspace/skills/tool_memory.py` | `memory_store_preference` | `.agent/skills/memory_store_preference.md` |
| `workspace_add_task` | `agent_workspace/skills/tool_workspace.py` | `workspace_add_task` | `.agent/skills/workspace_add_task.md` |
| `workspace_cancel_task` | `agent_workspace/skills/tool_workspace.py` | `workspace_cancel_task` | `.agent/skills/workspace_cancel_task.md` |
| `workspace_link_tasks` | `agent_workspace/skills/tool_workspace.py` | `workspace_link_tasks` | `.agent/skills/workspace_link_tasks.md` |
| `workspace_render_topology` | `agent_workspace/skills/tool_workspace.py` | `workspace_render_topology` | `.agent/skills/workspace_render_topology.md` |
| `workspace_update_status` | `agent_workspace/skills/tool_workspace.py` | `workspace_update_status` | `.agent/skills/workspace_update_status.md` |
| `transfer_agent` | `agent_workspace/skills/transfer_agent.py` | `transfer_agent` | `.agent/skills/transfer_agent.md` |
| `governed_memory` | `agent_workspace/core/skill_loader.py` | `governed_memory` | `.agent/skills/governed_memory.md` |
| `structured_log` | `agent_workspace/core/skill_loader.py` | `structured_log` | `.agent/skills/structured_log.md` |
| `topological_workspace` | `agent_workspace/core/skill_loader.py` | `topological_workspace` | `.agent/skills/topological_workspace.md` |

## Adding New Skills

1. Add or update a Python module under `agent_workspace/skills/`.
2. Expose a function whose first argument is a Pydantic `BaseModel`.
3. Let `AgentEngine` reflect the tool schema.
4. Run `python agent_workspace/tool_manifest.py sync` to update contracts.
5. Review and refine generated `.agent/skills/<skill_name>.md` files.

## Contract Rule

Runtime tools and PAP skill contracts must remain one-to-one. A tool without
a contract is not AI-maintainable; a contract without a runtime tool is stale.
Run `python agent_workspace/tool_manifest.py validate` before release.

## 中文說明

LAS 會從 `agent_workspace/skills/*.py` 反射可執行工具，並用本文件把 runtime
工具對應到 `.agent/skills/*.md` 的 PAP contract。新增工具後請執行 `sync`，
再人工檢查安全邊界與輸入輸出格式。
