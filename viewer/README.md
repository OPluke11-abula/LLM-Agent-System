# AI Agent Topology Viewer

The LAS viewer is a React 19, TypeScript, Vite, and Tauri 2 desktop control
plane. It reads local topology state, listens for runtime updates, and presents
task flow, activity, governance, configuration, token-mode, and design-agent
surfaces.

## Requirements

- Node.js 22 LTS or newer
- Rust stable
- Tauri 2 Windows prerequisites
- LAS repository dependencies installed

## Install

Run commands from the repository root:

~~~powershell
npm.cmd --prefix viewer install
~~~

## Web development

~~~powershell
npm.cmd --prefix viewer run dev
~~~

## Tauri development

Point the desktop application at the LAS workspace, then start Tauri:

~~~powershell
$env:AGENT_WORKSPACE_DIR="$PWD\workspace"
npm.cmd --prefix viewer run tauri -- dev
~~~

Generate a dry-run topology event from another terminal:

~~~powershell
.\.venv\Scripts\python.exe -m agent_workspace.topology_stream stream --msg "viewer smoke test" --session viewer-smoke --dry-run
~~~

## Production build

Build the frontend:

~~~powershell
npm.cmd --prefix viewer run build
~~~

Build the verified Windows NSIS installer:

~~~powershell
npm.cmd --prefix viewer run tauri -- build --bundles nsis
~~~

The verified NSIS installer is written under:

- viewer/src-tauri/target/release/bundle/nsis

MSI builds target viewer/src-tauri/target/release/bundle/msi and require a
working WiX/Windows Installer validation environment. The current published
NSIS release version is 0.1.1.

The direct `@tauri-apps/api` dependency is pinned to the 2.10 release line to
match the Rust Tauri 2.10 crate checked by the bundler. Plugin-private API
dependencies remain isolated by npm.

## Verification

~~~powershell
npm.cmd --prefix viewer run build
npm.cmd --prefix viewer run verify:ui
npm.cmd --prefix viewer run test:swarm-ui
~~~

Optional screenshot verification:

~~~powershell
npm.cmd --prefix viewer run verify:ui:screenshots
~~~

Set UI_VERIFY_STRICT_SCREENSHOTS=1 to make unavailable or failed screenshot
capture fail the command.

## Runtime integration

- useTopology reads topology_state.json through the Tauri bridge and consumes
  topology_updated events.
- AGENT_WORKSPACE_DIR overrides the shared workspace directory.
- The web development build can run without Tauri; unavailable native features
  use the viewer's documented browser-safe fallbacks.
- The Admin surface calls the LAS operator APIs when available and retains
  deterministic offline fixtures for UI verification.

## Main surfaces

- Mission Control and topology DAG
- Task Flow and Activity Log
- Admin and Swarm governance
- Rules, MODs, and Settings
- Long-term memory and intelligence map
- Token-efficient work-mode telemetry
- Design Agent art-direction and evidence state

## 專案說明

LAS Viewer 使用 React 19、TypeScript、Vite 與 Tauri 2，顯示本地 Agent
拓撲、任務流程、活動記錄、治理、設定、Token 模式與 Design Agent 狀態。

常用命令：

~~~powershell
npm.cmd --prefix viewer install
npm.cmd --prefix viewer run dev
npm.cmd --prefix viewer run build
npm.cmd --prefix viewer run verify:ui
npm.cmd --prefix viewer run tauri -- build --bundles nsis
~~~

如需讀取指定 LAS workspace，先設定 AGENT_WORKSPACE_DIR。正式提交前應從
repo root 執行完整的 .\scripts\verify.cmd。

## License

MIT. See viewer/LICENSE.
