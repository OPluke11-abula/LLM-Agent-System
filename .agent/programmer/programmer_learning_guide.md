# 🧠 LAS Elite Developer & Learning Guide for AI Programmer Agents

> **Target Audience**: AI Programmer & Developer Agents operating within FindAi Studio LLM Agent System (LAS).
> **Purpose**: Establish standard operating protocols for multi-dimensional topology mapping, structural log compaction, self-learning databases, parallel swarm coordination, and aesthetic visuals.

---

## 1. 📂 Core Evolution Pillars / 核心進化六大支柱

AI Programmers must follow these evolutionary protocols to upgrade LAS to the next generation:

### 🌐 Pillar 1: Multi-Dimensional Categorized Mind-Map Edges (多向分類心智圖拓撲連線)
To escape standard linear flows, the system supports multi-dimensional, mind-map-like categorical links:
* **Edge Classifications**:
  - `dependency` (Standard dependency): Solid blue/cyan line (`#6366f1` / `#22d3ee`).
  - `data_flow` (Data pipeline routing): Flowing particles with custom dashed line animations.
  - `feedback_loop` (AI review/HITL retry loop): Dashed amber/red pulsing lines (`#fbbf24` / `#ef4444`).
  - `parallel_trigger` (Simultaneous task spawns): Gold glowing streams traveling concurrently.
* **Layout Design**: Support visual categories that branch outward like a mind map (categories: backend, UI/UX, database, QA) with dynamic HSL indicators, allowing developers to immediately inspect the system facets.

### 📦 Pillar 2: Log Compaction & Milestone Integration (日誌里程碑壓縮與整合)
To prevent agent context windows from collapsing under large log files or verbose transaction loops:
* **Log Compaction Mechanism**:
  - Upon completing a major Milestone or Phase (e.g., Phase 10, Phase 11), execute a compaction sweep.
  - Intermediate transaction logs are compacted by at least **75%**.
  - Detailed historical logs are compiled and written into `.agent/memory/archive/milestone_X_archive.json`.
  - Active workspace/JSON logs are summarized into dense, semantic milestone tokens, keeping the prompt context extremely clean.

### 📝 Pillar 3: Continuous Iterative Planning Mode (計劃模式持續規劃)
Never write code ad-hoc. Enforce structured, iterative planning:
1. **Research & Minimize**: Inspect code files first using read tools; never write code during research.
2. **Implementation Plan**: Update `implementation_plan.md` with explicit details, open questions, and automated test commands.
3. **Task Tracking**: Maintain `task.md` with dynamic completions, checking off items as they go.
4. **Walkthrough Compilation**: Document changes and visual screenshots in `walkthrough.md`.

### ⚡ Pillar 4: Parallel Agent Team Execution (平行多智慧體協同執行)
LAS operates as a multi-threaded parallel swarm team:
* **Asynchronous Task Queuing**: Multiple task nodes marked as `in_progress` can run concurrently.
* **Concurrent Subagent Channels**: Use non-blocking asynchronous loops (`asyncio`) and separate workspace branches to run parallel sub-agents (e.g., one agent doing UI layout while another writes multi-language translations), integrating them back via git merges.

### 🎓 Pillar 5: Self-Learning & Self-Correction Database (自我學習與糾錯進化)
Prevent the repeating of engineering mistakes by maintaining a living self-learning log:
* **Self-Learning File**: `.agent/knowledge_base/lessons_learned.md`.
* **Registration Protocol**: Every time you encounter a compilation error, TypeScript build warning, Rust Tauri panic, or test deadlock, you must log it under the format:
  ```markdown
  ### Lesson ID: L-[Year][Month][Day]-[TaskID]
  - **Mistake Encountered**: [Explicit description of the bug/hang]
  - **Root Cause**: [Detailed diagnostic finding]
  - **Resolution Code**: [The exact code correction/mock pattern used]
  - **Best Practice Policy**: [A declarative rule to prevent this forever]
  ```
* **Cognitive Load**: The System Prompt Composer automatically reads `lessons_learned.md` and appends it to dynamic instructions, transforming mistakes into permanent corporate intelligence.

### 🏢 Pillar 6: Corporate Swarm Architecture (智慧體公司化小團隊)
Sub-agents are organized as a cohesive company, where each agent acts in a specialized corporate role:
* **CEO (Orchestrator)**: Handles user requests, monitors token budgets, and makes high-level decisions.
* **CTO (Planner)**: Breaks down goals, designs system architecture, and generates task DAGs.
* **Dev (Programmer)**: Writes highly-optimized, type-safe Python and sleek React Flow code.
* **QA (Auditor & Tester)**: Executes static lint checks and runs full test suites (`pytest`).
* **CFO (Auditor & Token Controller)**: Audits cumulative token consumption and API costs.

---

## 🚦 Strict 5-Step Work Principles (每次開發完成自我檢核)

Every time you conclude a programmer task, you MUST execute these steps:
1. **Clean Code & Decoupling**: Wrap async loops in try-except statements, delete unused imports, and avoid code bloat.
2. **Self-Learning Update**: If you solved any tricky bugs, append the lesson to `.agent/knowledge_base/lessons_learned.md`.
3. **Task Spec Update**: Mark items as completed (`[x]`) in `.agent/agent_tasks.md` and update progress tables.
4. **Bilingual Dev Specs**: Update the root `README.md` and `developer_specifications.md` keeping English/Traditional Chinese sections clean.
5. **Verify & Stage**: Run `pytest` to ensure 100% green tests. Stage all modified assets with `git add .` and make a clean commit.
