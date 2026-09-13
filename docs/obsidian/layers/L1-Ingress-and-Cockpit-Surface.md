---
tags:
  - layer/l1
  - ingress/cockpit
  - frontend/surface
type: layer_topology
layer: L1-Ingress-and-Cockpit-Surface
sync_status: verified
---

# L1: Ingress & Cockpit Surface Subsystem Topology

> **Parent Index**: [[00 LLM-Agent-System Index]]
> **Layer ID**: Layer 1 (Presentation & Desktop Cockpit)
> **Physical Boundary**: `viewer/`, `nginx.conf`
> **Assigned Role**: `UI_UX_AGENT` (Joe)

---

## 1. Subsystem Architecture Map

```mermaid
graph TD
    classDef ui fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#f8fafc;
    classDef hook fill:#1e293b,stroke:#818cf8,stroke-width:2px,color:#f8fafc;
    classDef edge fill:#1e293b,stroke:#34d399,stroke-width:2px,color:#f8fafc;

    App["App.tsx (Root Shell)"]:::ui
    Sidebar["Sidebar.tsx (Navigation & Status)"]:::ui
    MC["MissionControlView.tsx"]:::ui
    TF["TaskFlowView.tsx"]:::ui
    Topo["TopologyView.tsx"]:::ui
    Gov["SwarmGovernanceConsole.tsx"]:::ui
    Admin["AdminDashboardView.tsx"]:::ui
    LTM["LongTermMemoryView.tsx"]:::ui
    Prim["ui/primitives.tsx (Radix UI Base)"]:::ui
    WS["useWebSocket.ts (Real-time Stream)"]:::hook
    Nginx["nginx.conf (Reverse Proxy)"]:::edge

    App --> Sidebar
    App --> MC
    App --> TF
    App --> Topo
    App --> Gov
    App --> Admin
    App --> LTM
    MC --> Prim
    TF --> Prim
    Topo --> Prim
    Gov --> Prim
    Admin --> Prim
    App --> WS
    WS --> Nginx
```

---

## 2. Leaf Notes Index (Component Level)

- [[viewer-app]]: Application root container, theme provider, and global layout (`viewer/src/App.tsx`).
- [[viewer-mission-control]]: Cockpit dashboard, system health meters, activity feed (`viewer/src/components/MissionControlView.tsx`).
- [[viewer-task-flow]]: Directed graph workflow execution and interactive node debugger (`viewer/src/components/TaskFlowView.tsx`).
- [[viewer-topology-view]]: Dynamic multi-agent topology visualizer with real-time edges (`viewer/src/components/TopologyView.tsx`).
- [[viewer-swarm-governance]]: Multi-agent debate, consensus voting quorum, and replay timeline (`viewer/src/components/SwarmGovernanceConsole.tsx`).
- [[viewer-admin-dashboard]]: Multi-tenant management, cryptographic audit verification, token billing (`viewer/src/components/AdminDashboardView.tsx`).
- [[viewer-primitives]]: Radix UI primitive hierarchy, button, card, dialog, badge components (`viewer/src/components/ui/primitives.tsx`).
