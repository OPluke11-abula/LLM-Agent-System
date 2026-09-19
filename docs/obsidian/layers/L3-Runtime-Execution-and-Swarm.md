---
tags:
  - layer/l3
  - runtime/swarm
  - execution/dag
type: layer_topology
layer: L3-Runtime-Execution-and-Swarm
sync_status: verified
---

# L3: Runtime Execution & Swarm Subsystem Topology

> **Parent Index**: [[00 LLM-Agent-System Index]]
> **Layer ID**: Layer 3 (Runtime Engine & Swarm Dispatch)
> **Physical Boundary**: `agent_workspace/core/`, `agent_workspace/api.py`
> **Assigned Role**: `BACKEND_INFRA_AGENT` (Ethan) / `APPLICATION_FLOW_AGENT` (Eason)

---

## 1. Subsystem Architecture Map

```mermaid
graph TD
    classDef runtime fill:#1e293b,stroke:#34d399,stroke-width:2px,color:#f8fafc;
    classDef swarm fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#f8fafc;

    API["FastAPI Gateway (api.py)"]:::runtime
    ENG["AgentEngine (engine.py)"]:::runtime
    WFE["WorkflowEngine (workflow_engine.py)"]:::runtime
    RTR["AgentRouter (router.py)"]:::runtime
    CREW["AgentCrew & CrewRegistry (agent_crew.py)"]:::swarm
    DISC["DiscussionRoom (discussion_room.py)"]:::swarm
    SKL["SkillLoader (skill_loader.py)"]:::runtime

    API --> RTR
    RTR --> ENG
    ENG --> CREW
    CREW --> DISC
    CREW --> WFE
    ENG --> SKL
```

---

## 2. Leaf Notes Index (Core Runtime Level)

- [[core-engine]]: Dual-parser runtime executing Jinja2 prompt rendering and reflected tool calls (`agent_workspace/core/engine.py`).
- [[core-workflow-engine]]: Asynchronous step-by-step DAG execution engine with dynamic payload piping and checkpoint resumes (`agent_workspace/core/workflow_engine.py`).
- [[core-router]]: Intent classifier, active route latency tracking, and semantic dispatcher (`agent_workspace/core/router.py`).
- [[core-agent-crew]]: 10 Grounded Roles dispatching, CrewRegistry thread-safe topology tracking, and host skill bindings (`agent_workspace/core/agent_crew.py`).
- [[core-discussion-room]]: Swarm multi-agent debate, proposal synthesis, and Byzantine quorum voting (`agent_workspace/core/discussion_room.py`).
- [[core-pipeline]]: Autonomous developer agent coding pipeline lifecycle, Stop-and-Wait gate, and Draft PR generation (`agent_workspace/core/pipeline/`).
- [[core-pipeline-committee]]: Multi-agent committee consensus debate, dynamic role assembly, weighted scorecards, and veto protocol (`agent_workspace/core/pipeline/debate_protocol.py`).
- [[core-pipeline-benchmark]]: Autonomous coding golden benchmark engine, 3 canonical scenarios, ADR-006 6 KPIs scorecard (`scripts/run_golden_benchmark.py`).
- [[core-reasoning-router]]: Heterogeneous reasoning model adapters, dynamic thinking budgets, and air-gapped offline routing (`agent_workspace/core/reasoning_router.py`).
