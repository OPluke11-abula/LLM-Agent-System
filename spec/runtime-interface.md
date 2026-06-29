# PAP Runtime Interface

Status: LAS-aligned PAP contract

This document defines the stable runtime surface LAS exposes or maps to when interoperating with Portable Agent Protocol workspaces.

## Core Methods

Runtimes should expose these operations with deterministic errors and without leaking secrets in returned messages.

| Method | Purpose |
|---|---|
| `load_manifest(path)` | Load and validate `.agent/agent.md` front matter and declared entrypoints. |
| `list_skills()` | Return available skill contracts declared by the manifest. |
| `call_skill(skill_id, params, context)` | Execute one skill under the active allowlist and context policy. |
| `read_memory(key, tier)` | Read memory from an allowed tier. |
| `write_memory(key, value, tier)` | Write memory after key and tier validation. |
| `run_workflow(workflow_id, params)` | Execute or validate a declared workflow. |

## LAS Mappings

| PAP method | LAS implementation |
|---|---|
| `load_manifest` | `agent_workspace/pap_validate.py` and `AgentEngine` PAP document parsing |
| `list_skills` | `AgentEngine.get_tool_schemas()` and `agent_workspace/tool_manifest.py` |
| `call_skill` | `AgentEngine.execute_tool()` |
| `read_memory` | `agent_workspace/core/memory.py` managers and memory query tools |
| `write_memory` | Memory managers and governed memory tools |
| `run_workflow` | `agent_workspace/workflow_lint.py` for validation; executable workflows remain opt-in |

## Standard Errors

| Code | Meaning |
|---|---|
| `MANIFEST_NOT_FOUND` | The manifest file is missing. |
| `MANIFEST_INVALID` | The manifest does not satisfy schema or semantic checks. |
| `SKILL_NOT_FOUND` | A requested skill is not declared or cannot be loaded. |
| `VALIDATION_ERROR` | Input, schema, path, or policy validation failed. |
| `WORKFLOW_NOT_FOUND` | The requested workflow cannot be resolved. |
| `WORKFLOW_CYCLE` | A workflow dependency graph contains a cycle. |
| `EXECUTION_ERROR` | Runtime execution failed after validation passed. |

## Compatibility Notes

- LAS treats `.agent/agent.md` as the source of truth for entrypoints and directories.
- Workflows are validated in read-only mode unless an explicit execution path is implemented for a workflow.
- Handoff packets use the PAP memory schema plus LAS-compatible metadata and checksum fields.
- Runtime adapters must keep FastAPI, CLI, UI, and topology concerns outside `agent_workspace/core/`.
