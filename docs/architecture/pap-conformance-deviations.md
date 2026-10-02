# PAP Conformance Deviations

Date: 2026-07-02

Source: `OPluke11-abula/Portable-Agent-Protocol` `origin/main` commit `2b6d6e3d8ff24ae22b43e3001aee43c180f86357`.

LAS runner:

```bash
.\.venv\Scripts\python.exe -m agent_workspace.pap_conformance agent_workspace\tests\fixtures\pap_conformance\schema-validation.yaml agent_workspace\tests\fixtures\pap_conformance\layout-validation.yaml
```

## Tracked Deviations

| Upstream case | Upstream expected | LAS actual | Status | Reason |
|---|---:|---:|---|---|
| `schema-validation.yaml` / `Accept valid agent.md` | accept | reject | deviation | The upstream fixture omits `tools`, while LAS requires declared tools and matching `.agent/skills/<tool>.md` contracts. It also uses `authorization_level: read_only`, while the current LAS schema accepts `read-only`. |
| `layout-validation.yaml` / `Accept default layout structure` | accept | accept | deviation | The upstream layout fixture uses placeholder `...` file content, so the LAS runner synthesizes a valid `agent.md` before calling `pap_validate.py`. It also names `knowledge/`, while LAS uses `.agent/knowledge_base/`. |
| `layout-validation.yaml` / `Reject missing critical files` | reject | accept | deviation | Upstream treats `persona.md` and `memory.md` as critical default layout files. LAS `pap_validate.py` currently validates `.agent/agent.md`, declared protocol paths, and skill contracts, but does not require persona or memory files unless declared in the manifest. |

## Passing Cases

- `schema-validation.yaml` / `Reject missing protocol_version`
- `schema-validation.yaml` / `Accept valid memory tiers and schema evolution`

## Policy

These deviations are not skipped tests. They are executable conformance outcomes that must remain visible until LAS either aligns with the upstream default contract or explicitly records the difference as an intentional LAS compatibility profile.
