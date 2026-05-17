# Skill Contract: transfer_agent

## Runtime Mapping

- Module: `agent_workspace/skills/transfer_agent.py`
- Function: `transfer_agent`
- Argument model: `TransferToAgentArgs`

## Purpose

Signal that the current task should be handed off to a specialized agent.

## Input

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `target_agent` | string | yes | Name of the specialized agent |
| `reason` | string | yes | Reason for the handoff |

## Output

`HANDOFF_TO: <target_agent>`

The router interprets this prefix as a handoff signal.

## Safety Notes

- This skill does not execute the target agent by itself.
- Downstream routing and authorization remain runtime responsibilities.

## 中文說明

`transfer_agent` 只產生 handoff signal，不直接執行目標 Agent。實際路由與授權
仍由 LAS runtime 負責。
