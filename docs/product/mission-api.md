# Mission API and Viewer seam

P1 exposes a protected, local-first control-plane API under `/v1/missions` and
`/v1/system/capabilities`. The API stores Mission state and evidence; it does
not execute an Agent, call a provider, inspect a repository, mutate Git, create
a Draft PR, or merge.

## Authentication

Every Mission and System Check request requires either a validated `x-api-key`
or a validated Bearer session. The actor is derived from authentication, never
from the request body. A valid actor can only read or mutate its own Missions;
a second authenticated actor receives `404` for a Mission it cannot see.

The browser Viewer keeps a development credential in memory for the current
tab. Tauri obtains session headers through the native auth provider. API keys
are not persisted by the Viewer and are not embedded in the production bundle.

## First-run flow

1. Open `System Check` and run the read-only capability check.
2. Continue only when authentication, storage, and schema compatibility pass.
3. Define a requirement, repository reference, relative scope, permissions, and
   budget in `New mission`.
4. Start planning, attach the deterministic P1 plan, submit it, and approve its
   canonical SHA-256 subject.
5. Record bounded evidence and verification gates, then enter `Review`.

The deterministic plan/evidence control is a P1 verification seam. It is not an
Agent execution button and cannot create code, commits, pushes, pull requests,
or merges.

## Contract and persistence

Python Pydantic models are the source of truth. Regenerate checked-in artifacts
with:

```powershell
python -m agent_workspace.mission_schema
python -m agent_workspace.mission_schema --typescript viewer/src/generated/missionContracts.ts
```

The generated JSON is `schemas/mission_api.json`. Mission aggregates persist in
`memory/missions.db` under the configured workspace. Mutations require an
expected revision, use optimistic conflict detection, and accept an idempotency
key where the operation has replay semantics. Stale revisions and conflicting
immutable decisions return `409`; malformed or semantically invalid contract
payloads return `422`.

## Verification commands

```powershell
python -m pytest --no-cov -q agent_workspace/tests/test_mission_api.py
npm.cmd --prefix viewer run build
npm.cmd --prefix viewer run test:e2e:missions
```

The authenticated E2E script starts a real FastAPI process with SQLite, serves
the built Viewer, exercises the Golden Path in Playwright, reloads Review, and
checks unauthenticated access, cross-owner isolation, stale revision, and
conflicting approval paths.
