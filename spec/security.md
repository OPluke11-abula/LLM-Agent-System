# PAP Security Contract

Status: LAS-aligned PAP contract

This document records the security layers LAS applies when interpreting PAP manifests, skills, memory, workflows, and handoffs.

## Threat Layers

1. Prompt escaping and injection scans: user-provided or model-generated instructions must not override higher-priority project, workflow, or security rules.
2. Skill identity verification: skill calls must map to declared skill contracts and stay inside the active allowlist.
3. Memory key sandboxing: memory reads and writes must validate path, tier, key format, and workspace containment.
4. Granular permissions and autonomy levels: high-impact actions require explicit authorization or an approved governance certificate before execution.

## LAS Enforcement Points

| Layer | LAS enforcement |
|---|---|
| Prompt and instruction safety | Source-of-truth workflow policy and review/security gates |
| Skill identity | `.agent/skills/*.md`, `tool_manifest.py validate`, and `AgentEngine.execute_tool()` allowlists |
| Memory sandboxing | Memory managers, handoff path guards, and workspace-contained evidence refs |
| Permissions | `UnifiedPolicyGate`, ProofOfConsensus hooks, and explicit approval boundaries |

## Handoff Integrity

Machine handoff packets must include a checksum over canonical task, pending-step, context, and memory fields. Importers must fail closed on malformed JSON, missing core fields, path traversal, or checksum mismatch. Backward-compatible legacy import is allowed only when the legacy checksum verifies against the exact legacy payload.

## Reporting Rules

- Redact credentials, tokens, API keys, personal contact details, and payment identifiers from logs and user-facing output.
- Keep security findings structured with entrypoint, sink, evidence, impact, remediation, and validation status.
- Treat high-risk workflow paths as blocked until the required trigger and approval evidence exists.
