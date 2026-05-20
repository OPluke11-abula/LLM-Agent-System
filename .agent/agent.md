---
protocol_version: "1.0.0"
min_runtime_version: "0.1.0"
name: programmer-agent
version: "0.3.0"
purpose: >
  負責系統開發、程式碼重構、單元測試編寫與合約驗證的專業程序員 Agent。
description: >
  本 Agent 遵循 Contract-First 哲學，專注於 LLM-Agent-System (LAS) 系統與 Portable Agent Protocol (PAP) 協定的開發、演進與測試。
language: zh-TW
authorization_level: interactive-approval
use_case_tags:
  - programmer-agent
  - python
  - fastapi
  - topology-observability
  - pap-compatible
tools:
  - delegate_task
  - calculate
  - log_append
  - log_archive_month
  - log_compress_done
  - memory_query
  - memory_store_knowledge
  - memory_store_preference
  - workspace_add_task
  - workspace_cancel_task
  - workspace_link_tasks
  - workspace_render_topology
  - workspace_update_status
  - transfer_agent
  - governed_memory
  - structured_log
  - topological_workspace
protocol:
  root: .agent/
  manifest: .agent/agent.md
  entrypoints:
    overview: .agent/README.md
    skills: .agent/skills.md
    prompts: .agent/prompts.md
    memory: .agent/memory.md
    workflows: .agent/workflows.md
  directories:
    core: .agent/core/
    skills: .agent/skills/
    prompts: .agent/prompts/
    memory: .agent/memory/
    workflows: .agent/workflows/
    knowledge_base: .agent/knowledge_base/
memory:
  backend: local
  path: agent_workspace/memory/
prompts:
  path: .agent/prompts.md
workflows:
  path: .agent/workflows.md
---

# LAS PAP Manifest

This file is the executable PAP manifest for FindAi Studio LAS.

It is a protocol-facing contract, not an engine module. The LAS runtime still
discovers Python tools from `agent_workspace/skills/`, prompts from
`agent_workspace/agent.jinja2`, and memory from `agent_workspace/memory/`.

## Read Order

1. `.agent/agent.md`
2. `.agent/README.md`
3. `.agent/skills.md`, `.agent/prompts.md`, `.agent/memory.md`, or `.agent/workflows.md`
4. Task-specific documents in `.agent/skills/`, `.agent/core/`, or other detail directories

## 中文說明

這個檔案是 LAS 的 PAP manifest，用來宣告 repo 的協作合約與可攜式入口。
它不取代 LAS runtime；真正的工具反射、Jinja2 prompt、session memory、RBAC
與 closed-loop 行為仍由 `agent_workspace/core/` 和 adapter 層負責。
