# Agent Start Guide

Use this file as the compact entry point for Codex and other coding agents.

## First Read

1. Read [`AGENT.md`](AGENT.md) for the repository's existing engineering and safety rules.
2. For any task that needs project context, run the knowledge preflight from the repository root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\.agent\knowledge_base\tools\start_agent_preflight.ps1 -Query "<task focus>" -Top 5
```

3. Read the generated context pack before opening its ranked candidate notes.
4. Treat the pack as orientation only. Verify current code, configuration, tests, and Git state before acting or reporting a current fact.

## Knowledge Base Contract

- The canonical agent-facing project wiki is `.agent/knowledge_base/`.
- Read `index.md` only for broad navigation; do not load the whole knowledge base by default.
- The generated inventory contains paths, headings, links, and search cues only; it must never contain full note bodies or credentials.
- Keep reusable decisions, verified recurring fixes, and compact handoffs in the relevant knowledge-base folders. Do not place tokens, credentials, cookies, private keys, or `.env` values in knowledge notes.
- Refresh the inventory through the preflight tool when starting a non-trivial task; it only updates local index and context-pack artifacts.

## Tool Compatibility

- Codex: this `AGENTS.md` is the repository entry point.
- Antigravity: the workspace rule at `.agents/rules/knowledge-base.md` points to the same repository-local knowledge base.

## Scope

Knowledge artifacts make discovery cheaper; they do not replace targeted code reading or verification. Do not commit, push, install dependencies, deploy, or change external services unless the user explicitly asks.
