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

`AGENT_WORKSPACE_DIR` can point to another workspace directory. The web build
works without Tauri. The P1 Mission journey is browser-only; native Tauri
Mission authentication is unavailable and cannot enter that authenticated
journey. Other native-only viewer surfaces retain their existing browser-safe
fallbacks.

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

Optional screenshot verification:

```powershell
npm.cmd --prefix viewer run verify:ui:screenshots
```

Set `UI_VERIFY_STRICT_SCREENSHOTS=1` to make unavailable or failed screenshot
capture fail the command.

## Developer Beta Mission & Coding Pipeline Control Plane

The authenticated P1 Mission surface starts at `System Check`. In browser
development, enter a session credential for the current tab; it is held in
memory only. The Viewer then consumes the protected `/v1/missions` API and the
generated contract at `src/generated/missionContracts.ts`. The Autonomous Coding Pipeline
is accessible via the `Coding Pipeline` view (`CodingPipelineView.tsx`).

The complete local Golden Path can be verified with a real FastAPI process,
SQLite Mission store, built Viewer, and Playwright:

```powershell
npm.cmd --prefix viewer run build
npm.cmd --prefix viewer run test:e2e:missions
```

The P1 Viewer exposes no Agent execution, repository mutation, Git push, Draft
PR creation, or merge control. Those unavailable features are labeled in the
Mission and Review surfaces. Running Mission evidence is entered explicitly in
the production form and linked to one required verification gate at a time;
the deterministic `test_fixture` route is disabled by default and reserved for
focused E2E setup.

## Runtime integration

- `useTopology` reads `topology_state.json` through the Tauri bridge and
  consumes `topology_updated` events.
- The Admin surface calls LAS operator APIs when available.
- Offline fixtures exist for deterministic UI verification; they are not a
  production data source.

## License

The standalone viewer package is licensed under the **MIT License**. See [`LICENSE`](LICENSE) for details.
