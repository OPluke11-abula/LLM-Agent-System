# Contributing to the LAS viewer

The viewer is maintained as a package inside the LAS repository. Read the
parent [`AGENT.md`](../AGENT.md) and [`CONTRIBUTING.md`](../CONTRIBUTING.md)
before making changes.

## Prerequisites

| Tool | Minimum | Notes |
| --- | --- | --- |
| Node.js | 22 LTS | Use `npm.cmd` on Windows PowerShell |
| Rust | stable | Required for Tauri builds |
| WebView2 | current | Windows desktop runtime |

## Local development

```powershell
npm.cmd --prefix viewer install
npm.cmd --prefix viewer run dev
```

For Tauri development, set `AGENT_WORKSPACE_DIR` and run
`npm.cmd --prefix viewer run tauri -- dev` from the repository root.

## Code and data compatibility

- Keep TypeScript strict and avoid `any` unless an external API requires it.
- Format Rust with `cargo fmt`.
- Preserve backward compatibility for `agent_memory.json`; add optional fields
  rather than making existing fields mandatory.
- Keep UI changes focused and update `viewer/README.md` for changed commands.

## Verification

Run the focused checks during development and report their output in the pull
request:

```powershell
npm.cmd --prefix viewer run build
npm.cmd --prefix viewer run verify:ui
npm.cmd --prefix viewer run test:swarm-ui
```

Run `..\scripts\verify.cmd` before merging changes that affect the integrated
runtime. Do not commit `node_modules`, build output, credentials, or local
workspace state.

## Pull requests and issues

Use the repository pull-request template. Include the problem, the smallest
safe change, verification commands, and screenshots only when a visual change
needs them. Report vulnerabilities privately using [`../SECURITY.md`](../SECURITY.md).

The viewer is MIT licensed under [`LICENSE`](LICENSE); the parent runtime uses
Elastic License 2.0. Keep those package boundaries intact.
