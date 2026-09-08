# NotebookLM Source Manifest

## Purpose

This manifest prepares a low-risk NotebookLM research notebook for LLM Agent System. It is supplementary to the local Markdown wiki; coding agents must continue to use `AGENTS.md` and the local context-pack workflow for implementation work.

## Approved Starting Sources

Review each file immediately before import and import only the current version:

1. `README.md` — product overview and local setup.
2. `DESIGN.md` — architecture and design rationale.
3. `AGENT.md` — engineering and safety conventions.
4. `.agent/knowledge_base/projects/LLM-Agent-System.md` — compact project orientation.
5. `.agent/knowledge_base/decisions/local-markdown-agent-os.md` — local wiki decision record.

## Do Not Import

- `.env` files, credentials, API keys, cookies, private keys, or tokens.
- Git history, generated context packs, runtime logs, databases, user data, or production exports.
- Billing, security, authorization, or target-package material without an explicit separate review.

## Notebook Blueprint

- Title: `LLM Agent System — Architecture & Agent Workflow`
- Research question: `What are LAS's current architectural boundaries, operating rules, and safe agent workflows?`
- Use for: design rationale, onboarding questions, and document-grounded summaries.
- Do not use for: live code status, implementation verification, secrets, or deployment decisions.

## Import Verification

After manual import in an authorized NotebookLM session:

1. Confirm every source name and source count.
2. Ask for a cited architecture summary.
3. Check at least two named files or symbols against the live repository.
4. Record source names and the import date in a non-sensitive handoff if the notebook becomes part of the team workflow.
