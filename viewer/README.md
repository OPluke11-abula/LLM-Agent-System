# AI Agent Topology Viewer

The viewer is the React 19, TypeScript, Vite, and Tauri 2 control plane for
LAS. It reads local topology state, listens for runtime updates, and exposes
task flow, activity, governance, configuration, memory, and token telemetry.

## Requirements

- Node.js 22 LTS+
- Rust stable and Tauri 2 Windows prerequisites for desktop builds
- A checkout of the parent LAS repository for runtime integration

## Install and run

From the repository root:

```powershell
npm.cmd --prefix viewer install
npm.cmd --prefix viewer run dev
```

For the desktop app:

```powershell
$env:AGENT_WORKSPACE_DIR="$PWD\workspace"
npm.cmd --prefix viewer run tauri -- dev
```

`AGENT_WORKSPACE_DIR` can point to another workspace directory. The web build
works without Tauri. The P1 Mission journey is browser-only; native Tauri
Mission authentication is unavailable and cannot enter that authenticated
journey. Other native-only viewer surfaces retain their existing browser-safe
fallbacks.

## Build and verify

```powershell
npm.cmd --prefix viewer run build
npm.cmd --prefix viewer run verify:ui
npm.cmd --prefix viewer run test:swarm-ui
```

Build a Windows NSIS installer with:

```powershell
npm.cmd --prefix viewer run tauri -- build --bundles nsis
```

The current tracked installer is version 0.1.1 and is unsigned. Its checksum
and verification evidence are recorded in [`../releases/README.md`](../releases/README.md).
MSI packaging requires a passing WiX/Windows Installer validation environment
and is not part of the current release.

Optional screenshot verification:

```powershell
npm.cmd --prefix viewer run verify:ui:screenshots
```

Set `UI_VERIFY_STRICT_SCREENSHOTS=1` to make unavailable or failed screenshot
capture fail the command.

## Developer Beta Mission control plane

The authenticated P1 Mission surface starts at `System Check`. In browser
development, enter a session credential for the current tab; it is held in
memory only. The Viewer then consumes the protected `/v1/missions` API and the
generated contract at `src/generated/missionContracts.ts`.

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

The standalone viewer package is MIT licensed. See [`LICENSE`](LICENSE).
