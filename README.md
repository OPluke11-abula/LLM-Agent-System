# FindAi Studio — LLM Agent System

LAS is a local, contract-first agent runtime with a FastAPI service, a Python
operations CLI, Portable Agent Protocol (PAP) workspace contracts, and a
React/Tauri control plane.

## What is included

- Python runtime for routing, memory, governance, audit, sandboxing, providers,
  and multi-agent workflows (`agent_workspace/core`).
- PAP contracts, workflows, roles, and durable project knowledge (`.agent`).
- React 19 + Tauri 2 desktop viewer (`viewer`).
- Provider adapters for Google Gemini, Anthropic, OpenAI, and local Ollama.
  Configure only the provider you intend to use.

## Requirements

- Windows 10 or 11
- Python 3.11+
- Node.js 22 LTS+
- Rust stable and the Tauri 2 Windows prerequisites for desktop builds

## Quick start

```powershell
git clone https://github.com/OPluke11-abula/LLM-Agent-System.git
cd LLM-Agent-System
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\scripts\verify.cmd -SkipViewer
```

Optional hosted-provider dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-providers.txt
```

Set `GOOGLE_API_KEY`, `OPENAI_API_KEY`, or `ANTHROPIC_API_KEY` in the local
environment when using a hosted provider. Ollama does not require a hosted
key. Never commit credentials or local `.env` files.

Start the API:

```powershell
.\.venv\Scripts\python.exe -m uvicorn agent_workspace.api:app --host 127.0.0.1 --port 8000
```

Start the web viewer:

```powershell
npm.cmd --prefix viewer install
npm.cmd --prefix viewer run dev
```

Start the desktop viewer:

```powershell
$env:AGENT_WORKSPACE_DIR="$PWD\workspace"
npm.cmd --prefix viewer run tauri -- dev
```

## Release artifacts

The repository currently contains the 0.1.1 Windows NSIS installer at
`releases/ai-agent-topology-viewer_0.1.1_x64-setup.exe`. It is unsigned. Verify
the published SHA-256 before running it:

```powershell
Get-FileHash .\releases\ai-agent-topology-viewer_0.1.1_x64-setup.exe -Algorithm SHA256
```

Expected SHA-256:
`1D4A47DA57E60D641EFE729E7F347DBABCAE84033D1AF0EF45220CE0B6C49B47`.

Build a new NSIS installer locally:

```powershell
npm.cmd --prefix viewer run tauri -- build --bundles nsis
```

The output is under `viewer/src-tauri/target/release/bundle/nsis`. MSI packaging
is not part of the current release because the Windows WiX validation step is
not passing in the supported build environment. See
[`releases/README.md`](releases/README.md) for artifact evidence.

## CLI and verification

```powershell
.\.venv\Scripts\python.exe -m agent_workspace.cli --list-skills
.\.venv\Scripts\python.exe -m agent_workspace.cli --validate
.\.venv\Scripts\python.exe -m agent_workspace.cli lint .
.\.venv\Scripts\python.exe -m agent_workspace.tool_manifest validate
```

The authoritative repository gate is:

```powershell
.\scripts\verify.cmd
```

It compiles Python, runs tests, validates PAP contracts, checks tool parity and
secrets, builds the viewer, and runs UI/governance checks. Focused viewer checks
are `npm.cmd --prefix viewer run build`, `verify:ui`, and `test:swarm-ui`.

## Repository layout

| Path | Purpose |
| --- | --- |
| `agent_workspace/core` | Runtime business logic |
| `agent_workspace/routes` | FastAPI adapters |
| `agent_workspace/skills` | Runtime tool implementations |
| `.agent` | PAP contracts and durable project knowledge |
| `viewer` | React/Tauri control plane |
| `scripts/verify.cmd` | Authoritative verification gate |
| `releases` | Tracked Windows artifacts and evidence |

## Security and licensing

Read [`SECURITY.md`](SECURITY.md) before reporting a vulnerability. The root
runtime is licensed under Elastic License 2.0 (`LICENSE`). The standalone
viewer package is licensed under MIT (`viewer/LICENSE`); that boundary applies
only to files distributed as the viewer package.

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md) and the viewer-specific
[`viewer/CONTRIBUTING.md`](viewer/CONTRIBUTING.md). Please include the exact
verification command and result in pull requests.
