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

## Runtime configuration

The local profile is loopback-only, single-tenant, and does not start SaaS or
distributed workers. Boolean values accept `true`, `1`, `yes`, `on`, `false`,
`0`, `no`, or `off` (case-insensitive).

| Variable | Purpose and accepted value/type | Secure default | Example | Security or operational consequence |
| --- | --- | --- | --- | --- |
| `LAS_BIND_HOST` | API bind hostname or IP string | `127.0.0.1` | `LAS_BIND_HOST=127.0.0.1` | External binding requires configured secure authentication. |
| `LAS_JWT_SECRET` | JWT signing secret; non-empty string of at least 32 characters | unset; fail closed | `LAS_JWT_SECRET=<secret-manager-value>` | Required for authenticated external binding; never commit or log it. |
| `LAS_ENABLE_STRIPE` | Enable Stripe billing scheduler; boolean | `false` | `LAS_ENABLE_STRIPE=false` | SaaS billing is opt-in and otherwise creates no scheduler. |
| `LAS_ENABLE_REDIS_SWARM` | Enable Redis swarm listener; boolean | `false` | `LAS_ENABLE_REDIS_SWARM=false` | No Redis connection or retry loop is started when disabled. |
| `LAS_ENABLE_MULTI_WORKER` | Enable multi-worker coordination; boolean | `false` | `LAS_ENABLE_MULTI_WORKER=false` | Distributed workers remain off unless explicitly enabled with Redis. |
| `LAS_ENABLE_AUDIT_CONSENSUS` | Enable the audit/consensus daemon; boolean | `false` | `LAS_ENABLE_AUDIT_CONSENSUS=false` | Consensus background work is not started by the local profile. |
| `LAS_TASK_MAX_CONCURRENCY` | Maximum in-flight task count; integer | `8` | `LAS_TASK_MAX_CONCURRENCY=8` | The limit is process-local unless durable/distributed coordination is provided. |
| `LAS_TASK_TIMEOUT_SECONDS` | Per-task execution timeout in seconds; number | `300` | `LAS_TASK_TIMEOUT_SECONDS=300` | Long-running tasks are terminated after the limit. |
| `LAS_TASK_RECORD_TTL_SECONDS` | Retention for terminal task records in seconds; number | `3600` | `LAS_TASK_RECORD_TTL_SECONDS=3600` | Expired in-memory records are removed; this is not durable storage. |
| `LAS_POC_CONSENSUS_SECRET` | Consensus signing secret; non-empty secret string | unset; fail closed | `LAS_POC_CONSENSUS_SECRET=<secret-manager-value>` | Missing or test-only values prevent production consensus signing. |
| `LAS_POC_SECRET_<ROLE>` | Per-role consensus secret; non-empty secret string | unset; fail closed | `LAS_POC_SECRET_CEO=<secret-manager-value>` | Missing role secrets fail closed; never place real values in source or docs. |
| `LAS_ZK_SECRET_KEY` | Audit proof secret; non-empty secret string | unset; fail closed | `LAS_ZK_SECRET_KEY=<secret-manager-value>` | Missing values prevent proof verification instead of using a fallback. |
| `LAS_TEST_MODE` | Explicit non-production secret marker mode; `1`, `true`, or `yes` | unset/off | `LAS_TEST_MODE=1` | Test-only markers are permitted; never enable this in production. |

External hosts, including wildcard and non-loopback addresses, must have secure
authentication configured before startup. Stripe, Redis, multi-worker, and
audit-consensus services are opt-in. Task limits and records are process-local
unless the deployment supplies durable or distributed coordination.

## Hardened runtime profile

The current Unreleased hardening set protects runtime authentication and secret
handling, provider egress and filesystem containment, task lifecycle limits,
and Docker exposure defaults. It also adds bounded token-encoding reuse,
concurrent bounded WebSocket fan-out, and request-scoped provider token-count
reuse.

Reliability and cost controls include bounded memory queries, permanent-error
classification, finite debate budgets, cancellation propagation, and cleanup
of nested or broker-delegated work. The safety defaults are:

| Control | Default |
| --- | ---: |
| Debate provider calls | 64 |
| Debate retries | 12 |
| Debate healing calls | 8 |
| Debate nested depth | 1 |
| Debate provider concurrency | 3 |
| Memory results | 100 |
| Memory backend fetch | 300 |

These are safety defaults, not benchmark guarantees.

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
