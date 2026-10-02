# PAP TypeScript Runtime Parity Checklist for LAS

Status: Phase 66-07 runtime parity audit

PAP source of truth: `OPluke11-abula/Portable-Agent-Protocol` main at
`2b6d6e3d8ff24ae22b43e3001aee43c180f86357`.

Local checkout note: `D:\GitHub\Portable-Agent-Protocol` was observed at
`ababc0b654e77111c057a279e8256d685a503381`, so this audit treats the Phase 66
commit recorded in `.agent/agent_tasks.md` as authoritative. The audited PAP
runtime files from that commit are:

- `agent_runtime_ts/src/engine.ts`
- `agent_runtime_ts/src/router.ts`

This checklist is documentation-only. It does not add a TypeScript runtime,
does not execute `agent_runtime_ts`, and does not place TypeScript runtime
builds or tests into the default LAS verification path.

## Scope

66-07 asks for parity review across five runtime expectations:

- Engine initialization
- Tool routing
- Memory tier config
- Schema evolution handling
- MCP server declarations

The goal is compatibility awareness, not runtime replacement. LAS remains
Python-first through `agent_workspace/core/engine.py`,
`agent_workspace/tool_manifest.py`, `agent_workspace/pap_validate.py`, local
skill contracts, and the existing verification ladder.

## PAP Runtime Surface Observed

| PAP TS surface | Observed behavior at `2b6d6e3` | Compatibility meaning for LAS |
| --- | --- | --- |
| `AgentConfig` | Declares optional `protocol_version`, `name`, `version`, `tools`, `mcp_servers`, `schema_evolution`, and `memory` with `tiers`, `path`, and legacy `backend`. | Matches the top-level LAS manifest fields already represented in `.agent/agent.md` and `spec/agent-schema.json`. |
| `AgentEngine.constructor()` | Resolves `.agent/agent.md`, parses YAML frontmatter, creates `Router` from `tools` and `mcp_servers`, logs memory tier/backend state, and logs strict schema evolution when enabled. | LAS initializes from `.agent/agent.md`, but also performs Python tool discovery, onboarding policy, prechecks, version compatibility, markdown contexts, and auto-handoff setup. |
| `AgentEngine.loadConfig()` | Requires YAML frontmatter and throws on missing file, missing frontmatter, or YAML parse failure. | LAS `pap_validate.py` is stricter and should remain the compatibility gate for schema, semantic fields, protocol paths, versions, and skill contracts. |
| `AgentEngine.run()` | Dispatches a tool name plus params to `Router.route()`. | LAS equivalent is `AgentEngine.execute_tool()`, which validates allowed tools, unknown tools, pydantic args, prechecks, context passing, telemetry, and handoff limits. |
| `Router` | Stores declared tool names and MCP server declarations, allows handler registration, routes registered handlers, and throws when a handler is missing. | LAS already uses reflected Python skill registration plus manifest validation. PAP TS handler-map routing is a reference model, not a feature gap requiring a second runtime. |
| `mcpServers` | Stored on the router for future MCP routing; no MCP client execution is implemented in the observed `router.ts`. | LAS schema supports `mcp_servers`, but current operation should keep concrete MCP mounting explicit and separate from external Antigravity MCP credentials. |

## Parity Checklist

| Area | PAP expectation | LAS current surface | Status | LAS action |
| --- | --- | --- | --- | --- |
| Engine initialization | Runtime can load `.agent/agent.md` frontmatter and expose manifest fields. | `AgentEngine.__init__()` reads `.agent/agent.md` frontmatter when present; `pap_validate.py` validates the same manifest before compatibility claims. | Aligned with stricter LAS runtime behavior | Keep Python-first initialization. Do not add TS runtime boot to default verification. |
| Manifest parse failure | Missing config, missing frontmatter, or malformed YAML should fail clearly. | `pap_validate.py` raises for missing `.agent/agent.md`, missing frontmatter, YAML parse failure, schema failure, version mismatch, missing protocol paths, and missing skill contracts. | LAS stricter than PAP TS stub | Preserve `pap_validate.py` as the source of truth for import/interop checks. |
| Tool list ingestion | Runtime reads `tools` from the manifest. | `.agent/agent.md` declares enabled tools; `AgentEngine` discovers Python tools; `ToolManifest.from_engine()` emits the live manifest and contract mapping. | Aligned with richer implementation | Continue validating with `agent_workspace/tool_manifest.py validate`. |
| Tool routing | Runtime dispatches named tools through a router and errors on unknown tools. | `AgentEngine.execute_tool()` enforces onboarding, handoff limits, allowed tool filters, unknown-tool rejection, prechecks, pydantic argument validation, context passing, and telemetry. | LAS exceeds PAP TS reference | No TS router integration required. Future parity tests should assert LAS unknown-tool and allowed-tool behavior, not duplicate TS stubs. |
| Handler registration | PAP TS requires explicit `registerTool()` before routing can execute. | LAS registration is reflection-driven from `agent_workspace/skills/` and markdown skills, then cross-checked against `.agent/skills/*.md`. | Intentional implementation difference | Keep reflection plus contract validation. Do not introduce a second handler registry. |
| Memory tiers | Runtime exposes `memory.tiers.ephemeral/session/persistent/shared` and legacy `memory.backend`. | `.agent/agent.md` declares all four tiers; `pap_validate.py` rejects unknown tiers and unsupported tier backends. | Aligned | Existing 66-02 tests cover supported and rejected tier semantics. |
| Memory persistence | PAP formal semantics require tier boundaries and locking for file-backed persistent/shared writes. | LAS uses SQLite-backed long-term memory and explicit evidence memory packing; 66-06 added schema-backed evidence memory and trace requirements. | Partially aligned with LAS-specific backends | Track file-lock semantics only if LAS adds file-backed shared/persistent writers. No action for current SQLite path. |
| Schema evolution | Runtime surfaces `allow_self_evolution` and `strict_forward_compatibility`; strict mode is logged by TS runtime. | `.agent/agent.md` sets `allow_self_evolution: false` and `strict_forward_compatibility: true`; `pap_validate.py` rejects unsafe self-evolution config. | Aligned and stricter | Keep self-mutation disabled unless separately approved. |
| MCP declarations | Runtime accepts `mcp_servers` and passes them into `Router`. | `spec/agent-schema.json` accepts `mcp_servers`; current LAS manifest does not declare concrete servers. Codex-native tools and local skills remain primary. | Schema aligned, inactive by default | Do not auto-import Antigravity MCP registry. Future MCP mounting must be explicit and secret-redacted. |
| Runtime execution path | PAP TS package is a standalone reference runtime. | LAS default verify path is Python tests, PAP validation, manifest validation, viewer build, and smoke checks. | Intentional deviation | Keep TS runtime execution out of `scripts/verify.cmd` unless the user explicitly approves a future advisory check. |

## Guardrails

- Do not copy or translate PAP `agent_runtime_ts` into LAS runtime code during
  Phase 66.
- Do not add `npm install`, `tsc`, `jest`, or other PAP TS runtime commands to
  `scripts/verify.cmd`.
- Do not mount MCP servers from user-level Antigravity config as part of this
  parity work.
- Do not loosen LAS `AgentEngine.execute_tool()` checks to match the thinner PAP
  TS router.
- Treat LAS code graph evidence, audit ledger, policy gate, onboarding, and
  handoff behavior as LAS runtime extensions, not PAP incompatibilities.

## Future Optional Checks

These are intentionally not part of Phase 66 completion:

| Optional future check | Trigger condition |
| --- | --- |
| Advisory TS compile of `agent_runtime_ts` | Only if LAS starts vendoring or publishing PAP runtime packages. |
| Golden manifest fixture shared between Python and TS runtime | Only if PAP runtime interop becomes a release requirement. |
| MCP declaration mount test | Only after LAS has an explicit local MCP server contract and redaction policy. |
| Runtime parity CI job | Only after user approval to add non-Python runtime checks to CI or default verification. |

## 66-07 Ready Criteria

- `agent_runtime_ts/src/engine.ts` and `agent_runtime_ts/src/router.ts` are
  reviewed from the Phase 66 source-of-truth commit.
- LAS Python runtime surfaces are mapped to PAP TS initialization and routing
  concepts.
- Memory tiers, schema evolution, and MCP declaration behavior are classified.
- No TypeScript runtime is introduced into LAS.
- No default verification path is expanded to execute PAP TS runtime code.
