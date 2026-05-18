---
name: "delegate_task"
description: "[Supervisor Tool] Delegate a complex sub-task to a specialized worker agent. The worker will run autonomously and return its final response."
version: "1.0.0"
author: "LAS Tool Manifest Auto-Sync"
---

# delegate_task

> **PAP Skill Contract**: This document defines execution boundaries, inputs, and outputs for supervisor-worker delegation.

## 1. Purpose

Delegate a bounded sub-task to a named worker agent.

## 2. Required Inputs

- `worker_name` (string, **Required**): The specialized worker agent to delegate to.
- `task_instructions` (string, **Required**): Detailed instructions for what the worker needs to accomplish.

## 3. Expected Outputs

- **Success format**: Plain text final response from the worker.
- **Error format**: String prefixed with `Error:`.

## 4. Execution Boundaries and Safety

- The supervisor remains responsible for deciding whether delegation is allowed.
- Worker execution must remain traceable by session ID.
- Future versions should add cancellation, replay, cost, and tool-limit metadata.

## 5. Runtime Mapping

- Module: `agent_workspace/skills/delegate_task.py`
- Function: `delegate_task`
- Argument model: Pydantic `BaseModel` (see input schema)
- Wants context: `True`

## 中文說明

`delegate_task` 的重點不是追求 swarm 數量，而是建立可靠 delegation contract：
可追蹤、可審計、可限制工具，未來還應支援取消、回放與成本衡量。
