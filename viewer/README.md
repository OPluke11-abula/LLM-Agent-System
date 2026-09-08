# AI Agent Topology Viewer (Desktop & Web Control Plane)

The AI Agent Topology Viewer is the high-performance React 19, TypeScript, Vite, and Tauri 2 desktop control plane for FindAi Studio / LLM Agent System (LAS).

It visualizes multi-agent topologies, streams live execution telemetry over WebSockets, enforces cryptographic swarm governance, and manages multi-tier agent memory.

## Architecture & Technology Stack

- **Runtime & Desktop Shell**: [Tauri 2](https://v2.tauri.app/) (Rust 1.97+, WebView2, Windows x64).
- **Frontend Framework**: [React 19](https://react.dev/) + [TypeScript 5](https://www.typescriptlang.org/).
- **Build & Bundler**: [Vite 8](https://vite.dev/) with Rolldown manual chunk splitting for optimal bundle size.
- **UI Design System**:
  - Radix UI unstyled headless primitives (Dialog, Tabs, Tooltip, Select, Dropdown).
  - Lucide React iconography.
  - Dark glassmorphism aesthetic with CSS custom properties and smooth hardware-accelerated transitions.
- **Quality & Health**: 100% passing build, React Doctor audited (**0 errors**, **0 array index keys**, **0 performance warnings**).

## Key View Modules

| View Component | Purpose & Features |
| --- | --- |
| **Mission Control** (`MissionControlView.tsx`) | Executive dashboard with system throughput, task queues, active agent statuses, and quick actions. |
| **Topology View** (`TopologyView.tsx`) | Interactive Directed Acyclic Graph (DAG) visualizing agent coordination, handoffs, and communication channels. |
| **Task Flow** (`TaskFlowView.tsx`) | Kanban-style and topological workflow execution monitor with real-time log inspector. |
| **Swarm Governance** (`SwarmGovernanceConsole.tsx`) | Cryptographic Merkle tree proof verification, ZK-audit logs, and role consensus voting. |
| **Long-Term Memory** (`LongTermMemoryView.tsx`) | Multi-tier memory browser (Ephemeral, Session, Persistent, Shared FTS5) with semantic search. |
| **Rules & PAP Contracts** (`RulesView.tsx`) | Live inspection of PAP v0.2 workflow schemas, system prompts, and tool permissions. |
| **Admin & Settings** (`AdminDashboardView.tsx`, `SettingsView.tsx`) | Provider credential management, model calibration, rate limits, and diagnostic health checks. |

## Requirements

- **Node.js**: 22 LTS or newer
- **Rust**: 1.85+ stable (with `x86_64-pc-windows-msvc` target)
- **C++ Build Tools**: Visual Studio 2022+ C++ build environment
- **WebView2**: Evergreen Runtime (pre-installed on Windows 10/11)

## Install and Run

From the parent repository root:

```powershell
# Install frontend dependencies
npm.cmd --prefix viewer install

# Run web development server (HMR enabled on port 5173)
npm.cmd --prefix viewer run dev
```

For the desktop app with local workspace binding:

```powershell
$env:AGENT_WORKSPACE_DIR="$PWD\workspace"
npm.cmd --prefix viewer run tauri -- dev
```

## Production Build & Verification

```powershell
# 1. Typecheck and production bundle build (Rolldown / Vite)
npm.cmd --prefix viewer run build

# 2. UI smoke check & chunk budget validation (all non-vendor chunks < 100 kB)
npm.cmd --prefix viewer run verify:ui

# 3. Swarm governance mock-service verification
npm.cmd --prefix viewer run test:swarm-ui

# 4. React Doctor code quality audit
npm.cmd --prefix viewer run doctor
```

## Desktop Packaging (NSIS Installer)

Generate an unsigned Windows x64 NSIS installer:

```powershell
npm.cmd --prefix viewer run tauri -- build --bundles nsis
```

The compiled setup executable is generated at:
`viewer/src-tauri/target/release/bundle/nsis/aai-agent-topology-viewer_0.1.1_x64-setup.exe`

Verified release artifacts and SHA-256 integrity proofs are cataloged in [`../releases/README.md`](../releases/README.md).

## License

The standalone viewer package is licensed under the **MIT License**. See [`LICENSE`](LICENSE) for details.
