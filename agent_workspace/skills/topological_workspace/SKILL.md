---
name: topological-workspace
description: >
  建立並維護拓撲式視覺工作區。將多個 AI Agent 的任務節點
  以有向圖（DAG）形式組織，並輸出可讀的 Markdown 或 JSON。
  當使用者要求「建立任務圖」、「更新節點狀態」、「串接 Agent」時觸發。
triggers:
  - 建立任務圖
  - 更新節點
  - 拓撲視覺化
  - 工作區總覽
outputs:
  - workspace.md
  - workspace.json
---

# Topological Workspace Skill

This skill allows you to manage the project workspace by manipulating the task DAG.

## Usage Guidelines
1. **Adding Tasks**: Use the `workspace_add_task` tool to create a new task. The tool will auto-generate a TASK-ID if not provided.
2. **Updating Status**: Use `workspace_update_status` when you start working on a task (set to InProgress) or finish it (set to Done).
3. **Linking Tasks**: Use `workspace_link_tasks` to establish dependencies (e.g. TASK-002 depends on TASK-001). This helps the team understand the critical path.
4. **Rendering**: The workspace topology is automatically rendered and saved to `workspace/workspace.md` and `workspace/workspace.json` whenever you mutate the workspace.
