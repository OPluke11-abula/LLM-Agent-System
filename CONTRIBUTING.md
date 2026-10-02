# Contributing to LAS

Thank you for improving the LLM Agent System. Keep changes small, contract-first,
backward-compatible, and easy to verify.

## Before you change code

1. Read [`AGENT.md`](AGENT.md) and the relevant `.agent` contract.
2. Check the queue in [`.agent/agent_tasks.md`](.agent/agent_tasks.md) before
   starting a new task.
3. For a new runtime tool, add or update its PAP contract under
   `.agent/skills/<skill_id>.md` before implementing Python code.

## Local setup

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -r requirements-providers.txt  # optional
```

Keep API keys in environment variables. Do not commit `.env` files, generated
build output, credentials, or local agent-tool directories.

## Development workflow

After changing a runtime skill, synchronize and validate the manifest:

```powershell
.\.venv\Scripts\python.exe agent_workspace/tool_manifest.py sync
.\.venv\Scripts\python.exe agent_workspace/tool_manifest.py validate
.\.venv\Scripts\python.exe agent_workspace/cli.py lint .
```

Run the smallest relevant test while iterating, then run the authoritative gate
before opening a pull request:

```powershell
.\.venv\Scripts\python.exe -m pytest --no-cov -q path\to\relevant_test.py
.\scripts\verify.cmd
```

For viewer changes, also run `npm.cmd --prefix viewer run build` and the focused
UI checks documented in [`viewer/README.md`](viewer/README.md). Use `cargo fmt`
for Rust changes.

## Pull requests

- Explain the user-visible problem and the smallest safe change.
- List exact verification commands and their results.
- Update documentation for changed commands, APIs, or release behavior.
- Never include secrets, generated artifacts, or unrelated formatting churn.

The root runtime is Elastic License 2.0; the standalone viewer remains MIT
under `viewer/LICENSE`. Do not change either license without maintainer review.

## Reporting security issues

Do not open a public issue for a suspected vulnerability. Follow
[`SECURITY.md`](SECURITY.md).
