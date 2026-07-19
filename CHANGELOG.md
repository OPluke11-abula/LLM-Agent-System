# Changelog

## Unreleased

### Security

- Hardened runtime authentication, secret handling, provider URL validation,
  filesystem containment, task lifecycle limits, and Docker exposure defaults.

### Developer Beta Productization P1

- Added the authenticated System Check and protected Mission control-plane API
  with durable SQLite persistence, optimistic revisions, bounded history, and
  owner isolation.
- Added the generated Python-to-TypeScript Mission contract seam, browser/Tauri
  session-auth boundary, first-run Mission intake, deterministic plan approval,
  evidence-backed verification, and Review surface.
- Added a real FastAPI + SQLite + built Viewer Playwright Golden Path with
  authentication, ownership, stale-revision, and immutable-approval checks.

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
