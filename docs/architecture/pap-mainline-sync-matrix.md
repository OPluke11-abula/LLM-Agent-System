# PAP Mainline Sync Matrix for LAS

Status: Phase 66-01 source-grounded matrix

PAP source of truth: `OPluke11-abula/Portable-Agent-Protocol` main at
`2b6d6e3d8ff24ae22b43e3001aee43c180f86357`, verified with:

```powershell
git ls-remote https://github.com/OPluke11-abula/Portable-Agent-Protocol HEAD refs/heads/main
```

Local PAP checkout note: `D:\GitHub\Portable-Agent-Protocol` is not currently
checked out at that commit, so this matrix reads PAP files with
`git show 2b6d6e3d8ff24ae22b43e3001aee43c180f86357:<path>` instead of relying
on the local branch.

This is a compatibility matrix only. It does not change LAS runtime behavior,
provider routing, memory capture policy, external-state permissions, or viewer
surfaces.

## Classification Key

| Classification | Meaning |
| --- | --- |
| Already aligned | LAS already has a compatible runtime, schema, or documentation surface. |
| Additive LAS task | LAS should add support without replacing existing behavior. |
| Intentional deviation | LAS has a stricter or LAS-specific contract that should remain distinct. |
| Out of scope | Do not implement in LAS unless separately approved. |

## Sync Matrix

| PAP mainline artifact | PAP contract observed at `2b6d6e3` | LAS current surface | Classification | Required LAS action |
| --- | --- | --- | --- | --- |
| `docs/FORMAL_SEMANTICS.md` | Defines four memory tiers: `ephemeral`, `session`, `persistent`, `shared`; mandates pessimistic locking for file-backed memory; defines strict-forward-compatibility rules for skill changes. | `spec/agent-schema.json` and `.agent/agent.md` already declare `schema_evolution` plus the four memory tiers. `agent_workspace/pap_validate.py` validates the manifest schema, protocol paths, and local skill contracts. | Additive LAS task | Phase 66-02 should add semantic validation for supported tier backends and strict-forward-compatibility expectations. Keep automatic self-mutation disabled unless separately approved. |
| `spec/agent-schema.json` | Requires core manifest fields and supports `mcp_servers`, `schema_evolution`, protocol paths, and memory tiers. | LAS `spec/agent-schema.json` already contains those major surfaces. LAS `.agent/agent.md` uses `authorization_level: interactive-approval`, protocol entrypoints, and memory tiers `ephemeral/session/persistent/shared`. | Already aligned with additive validation gap | Keep the existing schema shape. Phase 66-02 should add tests for PAP conformance YAML cases and unsupported tier rejection. |
| `conformance/schema-validation.yaml` | Defines accept/reject cases for valid `agent.md`, missing `protocol_version`, and valid memory tiers plus schema evolution. | No LAS conformance runner consumes upstream YAML today. Existing validation is direct Python/pytest around `pap_validate.py`. | Additive LAS task | Phase 66-03 should parse upstream YAML into pytest fixtures and validate expected accept/reject behavior against `agent_workspace/pap_validate.py`. |
| `conformance/layout-validation.yaml` | Defines accept/reject cases for required `.agent` layout files and directories. | LAS `pap_validate.py` checks declared protocol entrypoints/directories from `.agent/agent.md`, but does not consume upstream layout YAML cases. | Additive LAS task | Phase 66-03 should cover layout cases and document ambiguity where PAP examples use placeholder file contents. |
| `spec/workflow-manifest.schema.json` | Opt-in workflow manifest with `schema_version`, `workflow_id`, stages, directors, canonical artifacts, allowed actions, and approval policy. | LAS uses `spec/workflow-stage.schema.json`, `.agent/workflows/codex-development.yaml`, and `agent_workspace/workflow_lint.py`. The LAS shape uses `id`, `version`, `stages`, `requires`, `produces`, `director_doc`, checkpoint policy, and risk level. | Intentional deviation with partial alignment | Keep the LAS stage schema for current workflows. Treat PAP `workflow-manifest.schema.json` as an upstream shape to map in docs/tests rather than replacing LAS stage manifests in Phase 66. |
| `spec/workflow-checkpoint.schema.json` | Checkpoint records carry workflow/stage ids, artifact hash/status, evidence refs, verifier, and unresolved risks. | LAS has `spec/checkpoint.schema.json` and `workflow_lint.py` validates optional checkpoint records without executing stages. | Already aligned with naming/shape deviation | No immediate runtime change. Future work may add a compatibility adapter only if PAP checkpoint files are imported directly. |
| `docs/las-interop-validation-plan.md` | Documents LAS consumption of PAP workflow governance, checkpoint, evidence memory, and review-gate fields as a validation plan, not a runtime bridge. | LAS Phase 64 implemented workflow docs, optional `ConductorPlan` workflow metadata, memory packing, review findings validation, and workflow UI visibility. | Already aligned | Preserve as documentation-only interop. Do not introduce runtime bridge behavior in Phase 66-01. |
| `spec/evidence-memory.schema.json` | Defines L0 raw evidence refs, canonical artifacts, L1 atoms, L2 scenarios, L3 profile, Mermaid canvases, and trace refs. | `agent_workspace/memory_pack.py` explicitly writes raw refs, L1 atoms, L2 scenarios, optional L3 persona, and Mermaid canvases. `LongTermMemoryStore.add_workflow_memory()` accepts `evidence_ref`, `workflow_atom`, `workflow_scenario`, and `workflow_persona`. | Additive LAS task | Phase 66-06 should add schema-backed parity checks for PAP field names and trace requirements while preserving explicit, command-driven capture only. |
| `spec/review-findings.schema.json` | Report-only schema requires `report_id`, `execution_policy.mode=report_only`, `parallel_audit_agents=false`, `source_trace`, `impact`, optional `exploit_path`, remediation, and validation status. | LAS `spec/review-findings.schema.json` currently requires `review_id`, `target`, top-level verdict/risk, `changed_paths`, `security_triggers`, evidence traces, and LAS code graph evidence for high/critical findings. `review_findings_validate.py` is report-only and enforces workspace-contained evidence. | Additive LAS task | Phase 66-05 should implement dual-shape compatibility. Keep LAS code graph evidence as a stricter extension, but accept PAP `report_id`/`execution_policy`/`source_trace`/`exploit_path`. |
| `docs/HUB_SPEC.md` | Defines Git-backed `.agent` Hub, `pap hub clone`, and safe packaging that includes public config/docs while excluding `memory/`, `.env`, SQLite files, `.git/`, and runtime logs. | LAS has no registry/hub pack validator. `tool_manifest.py` validates local skills, manifests, dependency/licenses, and secret scanning, but not PAP registry indexes or hub package contents. | Additive LAS task | Phase 66-04 should add read-only registry/hub validation and report-only packaging audit before any future pack/clone behavior. Do not implement clone/install behavior in this phase. |
| `registry/index.json` and `spec/registry-schema.json` | Registry index has `registry_version` and a map of skill descriptors with id, name, version, description, author, and path. Current index is empty. | LAS has `.agent/skills/*.md` capability contracts and `agent_workspace/tool_manifest.py`, but no PAP registry index validator. | Additive LAS task | Phase 66-04 should validate registry schema and public packaging exclusions. Empty registries should be accepted. |
| `agent_runtime_ts/` | TypeScript runtime stubs parse `.agent/agent.md`, expose `schema_evolution`, memory tiers, `mcp_servers`, tools, and a minimal router. | LAS runtime is Python-first: `AgentEngine`, Python skill registration, `ConductorPlan`, `UnifiedPolicyGate`, `LongTermMemoryStore`, and audit ledger. No TypeScript runtime is part of default verification. | Additive audit task | Phase 66-07 should produce a parity checklist only. Do not introduce a second runtime or TypeScript execution into the default LAS verify path without explicit approval. |
| PAP `mcp_servers` declaration | PAP manifest supports MCP server declarations for runtimes to mount. | LAS `.agent/agent.md` schema supports `mcp_servers`, but the current manifest does not declare concrete servers. LAS tool access is primarily through local skills and runtime tool allowlists. | Already aligned with no active servers | No action in 66-01. Future MCP mounting must remain explicit and must not read or expose secrets from external MCP configs. |
| PAP review `exploit_path` for high/critical findings | High-risk review reports can carry explicit exploit paths. | LAS high/critical review findings currently require concrete impact, declared triggers, and `code_graph_evidence`; exploit path is not part of the current LAS schema. | Additive LAS task | Phase 66-05 should require exploit path or code graph evidence for high/critical dual-shape inputs, with report-only behavior preserved. |
| LAS code graph extensions | PAP does not define LAS structural code graph evidence, `code_graph_refs`, `impact_summary`, or code graph query tools. | Phase 65 added read-only SQLite code graph tools, review `code_graph_evidence`, `ConductorPlan.code_graph_refs`, and viewer structural memory summaries. | Intentional deviation | Keep as LAS-only extension. Do not force it into upstream PAP conformance, but allow review/security gates to cite it as stronger local evidence. |
| LAS policy/audit enforcement | PAP review and hub docs emphasize report-only safety and packaging exclusions. | `UnifiedPolicyGate` fail-closes sensitive actions with ProofOfConsensus where required and records `policy_gate_decision` events in `AuditLedger`. `AuditLedger` chains events and supports Merkle/ZK proof paths. | Already aligned with stricter LAS runtime controls | Preserve fail-closed behavior. Phase 66 work should not loosen policy gates or turn report-only PAP findings into automatic actions. |

## Phase 66 Task Mapping

| Phase task | Matrix-driven scope |
| --- | --- |
| 66-02 Agent Manifest Formal Semantics | Add semantic validation for memory tier backends and strict-forward-compatibility expectations around skill evolution. |
| 66-03 PAP Conformance Runner | Consume `conformance/schema-validation.yaml` and `conformance/layout-validation.yaml` as pytest fixtures. |
| 66-04 Registry and Hub Safety Gate | Validate `spec/registry-schema.json`, `registry/index.json`, and packaging exclusions from `docs/HUB_SPEC.md`; keep report-only. |
| 66-05 Review Findings Dual-Shape Compatibility | Support both LAS and PAP review schemas while preserving high/critical evidence requirements and workspace containment. |
| 66-06 Evidence Memory Schema Parity | Reconcile LAS explicit memory packing and long-term workflow memory with PAP evidence-memory schema fields. |
| 66-07 Runtime Parity and TypeScript Surface Audit | Document parity against `agent_runtime_ts/` without adding a second runtime to default verification. |

## Current Deviation Register

| Deviation | Reason | Owner phase |
| --- | --- | --- |
| LAS workflow schema uses `workflow-stage.schema.json` and `id` rather than PAP `workflow-manifest.schema.json` and `workflow_id`. | LAS already has a stage-oriented governance manifest and linter. Replacing it would break current `.agent/workflows/codex-development.yaml` without adding immediate runtime value. | 66-03 may document import mapping only. |
| LAS review schema is stricter and includes code graph evidence. | LAS security gates need structural evidence for high-impact findings. This is a local strengthening, not a PAP incompatibility. | 66-05 should keep the stricter path for LAS-native reports. |
| LAS code graph tools are not PAP standard artifacts. | They are local structural memory tools from Phase 65 and should remain optional extension evidence. | No Phase 66 standardization required. |
| PAP TypeScript runtime is not executed by LAS. | LAS runtime is Python-first and the task explicitly forbids introducing a second runtime into default LAS verification. | 66-07 audit only. |

## Ready Criteria for 66-01

- Remote PAP main commit is verified.
- PAP artifacts are read from that exact commit.
- LAS current surfaces are mapped to each PAP mainline area.
- Each item is classified as already aligned, additive LAS task, intentional deviation, or out of scope.
- No runtime, schema, or validator behavior is changed by this matrix.
