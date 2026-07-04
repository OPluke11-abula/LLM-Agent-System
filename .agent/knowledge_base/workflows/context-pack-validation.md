# Context Pack Validation Workflow

## Purpose

Validate generated context packs before agents rely on them.

This is a quality gate for the Context Pack Builder workflow. It checks that a pack is compact, references existing candidate notes, avoids likely credential values, and reminds agents to verify current-state claims live.

## Script

Run from `D:/GitHub/LLM-Agent-System`:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\.agent\knowledge_base\tools\validate_context_pack.ps1 -PackPath .\.agent\knowledge_base\handoffs\context-pack-latest-inventory-refresh.md
```

JSON output:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\.agent\knowledge_base\tools\validate_context_pack.ps1 -PackPath .\.agent\knowledge_base\handoffs\context-pack-latest-inventory-refresh.md -Format Json
```

## Procedure

1. Build or locate a context pack.
2. Run the validator against the pack.
3. Confirm all candidate files exist.
4. Confirm the pack says full note bodies are not copied.
5. Confirm the pack requires live verification.
6. Run a credential-value scan.
7. Fix the builder or pack if validation fails.

## Checks

- required sections exist
- `Contains full text: False` is present
- full-note-body exclusion notice is present
- live-verification notice is present
- line budget is respected
- read-order candidate files exist
- likely credential values are absent

## Safety

- Passing validation does not prove any repo state.
- Passing validation only means the context pack is a reasonable orientation artifact.
- Current code, config, tools, tests, builds, plugins, and external docs still require live verification.

## Related Notes

- [[../index]]
- [[context-pack-builder]]
- [[inventory-backed-query]]
- [[../handoffs/context-pack-latest-inventory-refresh]]
- [[../known-issues/memory-must-not-replace-verification]]
