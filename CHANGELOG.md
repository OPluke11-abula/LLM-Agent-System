# Changelog

## Unreleased

### Security

- Hardened runtime authentication, secret handling, provider URL validation,
  filesystem containment, task lifecycle limits, and Docker exposure defaults.

### Developer Beta Productization P1

- Added the authenticated System Check and protected Mission control-plane API
  with durable SQLite persistence, optimistic revisions, bounded history, and
  owner isolation.
- Added the generated Python-to-TypeScript Mission contract seam, browser-only
  Mission session-auth boundary, first-run Mission intake, deterministic plan
  approval, and schema-mismatch blocking based on the actual backend version.
- Added an explicit production evidence form and gate-level Review metadata;
  production evidence is recorded through the normal API one gate at a time.
  The `test_fixture` evidence route is authenticated and disabled by default.
- Added a real FastAPI + SQLite + built Viewer Playwright Golden Path with
  authentication, ownership, stale-revision, immutable-approval, missing-ref,
  fixture-disabled, and Review linkage checks, plus offline/store/schema/abort
  and Tauri-unavailable UI checks.

### Runtime efficiency

- Added bounded token-encoding cache reuse, concurrent bounded WebSocket
  fan-out, and request-scoped provider token-count reuse.

### Reliability and cost bounds

- Bounded memory queries and debate provider calls, retries, healing calls,
  nested depth, and provider concurrency.
- Added permanent-error classification, cancellation propagation, and cleanup
  for nested and broker-delegated work.
- Safety defaults are 64 provider calls, 12 retries, 8 healing calls, nested
  depth 1, provider concurrency 3, 100 memory results, and 300 backend fetches;
  these are safety defaults, not benchmark guarantees.

## 0.1.1

- Published the Windows NSIS viewer installer tracked in `releases/`.
- Added the React/Tauri topology, task-flow, governance, memory, and telemetry
  surfaces described in the viewer documentation.
- Added repository verification through `scripts/verify.cmd`.

Unreleased changes are tracked in Git history and the project task queue.
