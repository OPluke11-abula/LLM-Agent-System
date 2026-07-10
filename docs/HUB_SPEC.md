# PAP Hub Safety Notes for LAS

LAS treats PAP Hub behavior as report-only until separately approved. This local mirror records the Phase 66 safety gate used before any future pack, clone, or publish behavior is considered.

Public package audits must exclude:

- `.git/`
- `memory/`
- `.env` and `.env.*`
- SQLite/database artifacts such as `.sqlite`, `.sqlite3`, `.db`, and sidecar WAL/SHM files
- runtime log directories or `.log` files

The validator does not package, clone, install, or publish anything. It validates `registry/index.json` against `spec/registry-schema.json` and can audit a staged package directory with:

```powershell
python -m agent_workspace.pap_registry --root . --registry registry/index.json --package-root <staged-package-dir>
```
