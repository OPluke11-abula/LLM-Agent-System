---
protocol_version: "1.0.0"
min_runtime_version: "0.1.0"
name: findai-las
version: "0.3.0"
purpose: >
  Production-ready backend runtime for file-aware, tool-using LLM agents,
  maintained as the FindAi Studio reference application for PAP-compatible
  agent workspaces.
description: >
  LAS keeps runtime code, knowledge, skills, memory, topology events, and API
  adapters explicit and inspectable. This manifest declares the portable
  collaboration contract without moving PAP logic into the engine core.
language: zh-TW
authorization_level: interactive-approval
use_case_tags:
  - llm-agent-runtime
  - python
  - fastapi
  - topology-observability
  - pap-compatible
tools:
  - calculate
  - transfer_agent
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

這個檔案是 LAS 的 PAP manifest。它宣告可攜式協作契約，但不介入 LAS 的核心
runtime。LAS 仍由既有引擎負責 Pydantic tool 反射、Jinja2 prompt、session
memory、RBAC 與閉環狀態機。
