---
tags:
  - architecture/topology
  - system/7-layers
  - control-plane
type: system_architecture
layer: control-plane-topology
sync_status: verified
---

# 7-Layer System Architecture & Control Plane Topology (10)

> **Parent Index**: [[00 LLM-Agent-System Index]]
> **Strategic Compass**: [[01 Agent Strategy Integration & TaskEnvironment Architecture]]
> **Related Architecture**: [[20 Feature DAG & Feature-Based Ownership Topology]], [[30 Concurrency Lifecycle & Swarm State Machine]], [[40 4-Tier Memory OS & SQLite FTS5 Persistence Topology]]
> **Scale**: 516+ tracked files, 96,000+ LOC, 101 REST endpoints, 9 WebSockets, 10 Grounded Roles

---

## 1. 7-Layer Topological Hierarchy

The system enforces a strict unidirectional Directed Acyclic Graph (DAG) across seven distinct architectural layers:

```mermaid
graph TD
    classDef client fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#f8fafc;
    classDef gate fill:#1e293b,stroke:#818cf8,stroke-width:2px,color:#f8fafc;
    classDef runtime fill:#1e293b,stroke:#34d399,stroke-width:2px,color:#f8fafc;
    classDef memory fill:#1e293b,stroke:#f59e0b,stroke-width:2px,color:#f8fafc;
    classDef security fill:#1e293b,stroke:#f43f5e,stroke-width:2px,color:#f8fafc;
    classDef test fill:#1e293b,stroke:#a855f7,stroke-width:2px,color:#f8fafc;
    classDef kb fill:#1e293b,stroke:#06b6d4,stroke-width:2px,color:#f8fafc;

    subgraph L1["Layer 1: Ingress & Cockpit Surface (React 19 + Tauri 2 + Nginx)"]
        UI_Dash["Viewer Desktop App (Mission Control, TaskFlow, Topology)"]:::client
        UI_Components["Radix UI Primitives + Lucide Design System"]:::client
        Nginx_Proxy["Nginx Ingress (Port 8080/8000, Security Headers)"]:::client
    end

    subgraph L2["Layer 2: Protocol & Governance Gateways (PAP v0.2 + Protocol v3.8.0)"]
        PAP_Schemas["spec/ (workflow, stage, skill contracts, checkpoint)"]:::gate
        Gov_Baseline[".agent/state.md, ownership.md, decisions.md, test_policy.md"]:::gate
        Gatekeeper["tool_manifest.py, precheck.py, policy_gate.py"]:::gate
    end

    subgraph L3["Layer 3: Runtime Execution & 10 Grounded Roles (FastAPI Core)"]
        FastAPI_App["FastAPI Engine (101 Endpoints, 9 Authenticated WebSockets)"]:::runtime
        Workflow_Engine["Workflow Engine (PAP DAG Execution & Concurrency)"]:::runtime
        Router["Intent Classifier & Semantic Dispatcher"]:::runtime
        Grounded_Swarm["10 Grounded AI Agent Roles (UI, Backend, Domain, Flow, Merge, Security, Perf, QA, Architect, Topology)"]:::runtime
    end

    subgraph L4["Layer 4: Cognitive & 4-Tier Memory OS"]
        L1_Ephemeral["Tier 1: Ephemeral Memory (In-Memory Run Context)"]:::memory
        L2_Session["Tier 2: Session Memory (SQLite Sessions & Message History)"]:::memory
        L3_Persistent["Tier 3: Persistent Memory (SQLite FTS5 + BM25 Reranking)"]:::memory
        L4_Shared["Tier 4: Shared Memory (Obsidian Vault + Knowledge Graph)"]:::memory
    end

    subgraph L5["Layer 5: Security, Zero-Trust Sandbox & Merkle Consensus"]
        Sandbox["Execution Sandbox (AST Restriction & Resource Quotas)"]:::security
        Policy_Gate["Unified Policy Gate (Scope Guard, Proof of Consensus)"]:::security
        Merkle_Ledger["Audit Ledger (Tamper-Proof SHA-256 Merkle Trail)"]:::security
        Billing_Ledger["Elastic Billing & Token Consumption Meter"]:::security
    end

    subgraph L6["Layer 6: Verification Ladder & Quality Matrix"]
        Test_Suites["118 Test Suites (Core, Swarm, Memory, Sandbox, Ledger, API)"]:::test
        Verify_Scripts["scripts/verify.ps1 (8-step Golden Verification Ladder)"]:::test
    end

    subgraph L7["Layer 7: Distributed Mesh & Cross-Cloud Sync"]
        mTLS["mTLS Certificate Rotation & Revocation"]:::kb
        Broker["Distributed Message Broker (Redis / InMemory / P2P)"]:::kb
        Federated["Cross-Cloud Gateway & Multi-Region Sync"]:::kb
    end

    UI_Dash --> Nginx_Proxy
    Nginx_Proxy --> FastAPI_App
    FastAPI_App --> Gatekeeper
    Gatekeeper --> PAP_Schemas
    Gatekeeper --> Gov_Baseline
    Gatekeeper --> Router
    Router --> Grounded_Swarm
    Grounded_Swarm --> Workflow_Engine
    Workflow_Engine --> Sandbox
    Sandbox --> L1_Ephemeral
    L1_Ephemeral --> L2_Session
    L1_Ephemeral --> L3_Persistent
    L1_Ephemeral --> L4_Shared
    Workflow_Engine --> Policy_Gate
    Policy_Gate --> Merkle_Ledger
    Policy_Gate --> Billing_Ledger
    FastAPI_App --> Broker
    Broker --> mTLS
    Broker --> Federated
    Test_Suites -.->|Guarantees Behavior| L3
    Verify_Scripts -.->|Enforces Gate| L2
```

---

## 2. Primary Source Directory Mapping

- **Layer 1 (Presentation)**:
  - `viewer/src/components/`: MissionControlView, TaskFlowView, TopologyView, Sidebar.
  - `viewer/src/components/ui/primitives.tsx`: Radix UI accessible button, card, dialog, badge primitives.
- **Layer 2 (Protocol Boundary)**:
  - `.agent/state.md`, `ownership.md`, `decisions.md`, `test_policy.md`, `versions.md`.
  - `spec/`: JSON Schema specifications (`workflow.schema.json`, etc.).
- **Layer 3 (Runtime Engine)**:
  - `agent_workspace/core/agent_crew.py`: Grounded agent registry, 10 roles, skill bindings.
  - `agent_workspace/core/engine.py`: Agent execution engine.
  - `agent_workspace/core/workflow_engine.py`: DAG execution, task state transitions.
  - `agent_workspace/core/router.py`: Adaptive task router.
- **Layer 4 (Memory OS)**:
  - `agent_workspace/core/memory.py`: 4-tier storage abstraction, SQLite FTS5 index.
- **Layer 5 (Security & Consensus)**:
  - `agent_workspace/core/policy_gate.py`: Scope validation, consensus proof verification.
  - `agent_workspace/core/audit_ledger.py`: Merkle tree cryptographic receipt trail.
  - `agent_workspace/core/sandbox.py`: Isolated process & filesystem transaction execution.
