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
works without Tauri; native-only features use browser-safe fallbacks.

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

## Runtime integration

- `useTopology` reads `topology_state.json` through the Tauri bridge and
  consumes `topology_updated` events.
- The Admin surface calls LAS operator APIs when available.
- Offline fixtures exist for deterministic UI verification; they are not a
  production data source.

## License

The standalone viewer package is MIT licensed. See [`LICENSE`](LICENSE).
