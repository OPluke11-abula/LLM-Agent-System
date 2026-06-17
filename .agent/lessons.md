# Lessons — Agent Self-Learning Memory
> Auto-maintained by the self-learning skill. Do not delete.
> Workspace scope: applies to the LLM-Agent-System project.

## [2026-06-16] Systems Analyst and Software Architect Role Boundary Enforcements

**Before**: Proceeding directly to execute backend/frontend code changes, creating new files, and modifying endpoints when the user has approved the implementation plan, even when operating in an Analyst/Architect role.
**After**: Strict enforcement of role boundaries. When operating as the Systems Analyst & Software Architect, do NOT modify code files, create codebase scripts, or execute git commits directly. Instead:
  1. Produce the detailed designs, implementation plans (`implementation_plan.md`), and checklists (`task.md`).
  2. Ask the user for explicit approval on the architectural design.
  3. Formulate and present the exact Programmer Agent `/goal` command, letting the user trigger the specialized developer agent execution in a separate thread.
**Why**: Overstepping the role boundary by directly writing code violates the clean separation between analysis/architecture and implementation tasks, causing developer track pollution and context drift.
**Tags**: #role-calibration #architect #analyst #boundary-control #self-audit

## [2026-06-03] Agent Role Boundary Calibration

**Before**: Automatically transitioning from planning to codebase modifications, code generation, and test execution upon workflow triggers.
**After**: Strict enforcement of the Systems Analyst and Software Architect boundaries. Prioritize high-level architecture design, interface contract specifications, dynamic cost-accounting reviews, and security gate audits. Do not proceed to codebase execution or modification unless explicitly instructed by the user.
**Why**: The user corrected the agent's role, emphasizing that the primary function is that of an Analyst and Architect rather than a programmer.
**Tags**: #role-calibration #architect #analyst #boundary-control

## [2026-06-03] High-Fidelity Prompt Delegation in Multi-Agent Swarms

**Before**: Writing brief, generic, or summary-only task delegation prompts when passing objectives to downstream executors or providing task descriptions.
**After**: Construct highly detailed, structural, and complete task dispatches that specify precise file scopes, API specifications, fallback behaviors, concurrency requirements, security guidelines, and mocked test assertions.
**Why**: Downstream child agents or execution engines require high context density and explicit operational boundaries to prevent low-quality code generation, shallow implementations, or design regressions.
**Application to LAS**:
- **Structured Delegation in Swarms**: In Phase 34's `AgentCrew` and `AgentRouter`, the task delegation prompt templates (used by the moderator or parent agent) should not be free-form text. Instead, they should enforce a structured schema requiring parent agents to list:
  1. Input/Output specifications.
  2. Mock requirements (preventing real API costs during tests).
  3. Security sandbox constraints.
  4. Precise file paths and exit criteria.
- **Dynamic Checklists**: PromptComposer templates can be updated to automatically inject a verification checklist into the child agent's prompt to enforce rigorous quality gates.
**Tags**: #prompt-engineering #swarms #multi-agent #delegation-safety

## [2026-06-04] Destructive Working Directory Checkout and Actor Synchronization Safeguards

**Before**: Running git checkouts (`git checkout <commit> -- <files>`) or file removals based solely on local working directory status (`git status`), without checking the recent commit logs for changes submitted by other actors.
**After**: Before executing any checkout, reset, or file deletion command targeting historical commits, the agent MUST:
  1. Inspect the recent commit logs (`git log -n 5`) to check if other actors (humans or other AI agents) have committed files.
  2. If committed work from other actors is detected, verify with the user before performing any git checkouts or overwrites that would overwrite those files in the working directory.
  3. Never assume a "clean" status relative to HEAD means there is no other work, since HEAD itself might have advanced with commits from other actors.
**Why**: Blind checkouts to historical commits can overwrite or delete committed files of other actors in the active working directory, causing immediate code loss fears and coordination friction.
**Application to LAS**:
- **Swarm Conflict Auditing**: In multi-agent environments or multi-cloud systems (Phase 31+), before an agent rolls back workspace snapshots or overwrites shared files, it must execute a consensus-based file integrity log audit to verify that it is not overwriting concurrent commits made by peer agents.
**Tags**: #git-safety #actor-coordination #destructive-operations #lessons-learned

## [2026-06-04] Zero-Dependency JWT, WebSocket Testing Lifecycles, and Dynamic Module Paths

**Before**: Using external packages (`PyJWT`, `python-jose`) for token auth, relying on `websocket_connect` to raise errors during handshakes, and caching module-level variables at import time in test cases.
**After**:
  1. **Zero-Dependency JWT**: Implement standard base64url HMAC-SHA256 JWT checks using standard modules (`hmac`, `hashlib`, `base64`) to prevent packaging overhead.
  2. **WebSocket Test Assertions**: In Starlette `TestClient`, server-side connection closures (e.g. code `4001`) must be checked by expecting a `WebSocketDisconnect` during message reads rather than expecting `websocket_connect` context entry to fail.
  3. **Dynamic Variable Access**: Access globally patched module variables (like `api.workspace`) dynamically via `import api; api.workspace` instead of caching them via `from api import workspace` at import time to prevent path mismatches across concurrent tests.
**Why**: Ensures robust multi-tenant authorization coverage, zero dependencies, and flawless test suites execution.
**Tags**: #multi-tenancy #websockets #jwt #pytest #path-resolution

## [2026-06-18] SQLite Concurrency Deadlocks, Thread-local Connection Leaks, and OpenTelemetry Shutdown

**Before**: Using `threading.Lock()` (non-reentrant) for connection tracking leading to deadlocks, closing connections globally across threads inside concurrent workers causing active connections to close early or leak file handles, and letting OpenTelemetry ConsoleSpanExporter run after stdout closes.
**After**:
  1. **Reentrant Locking**: Always use `threading.RLock()` instead of `threading.Lock()` for database classes that perform nested thread-local database queries or connection caching to prevent self-deadlocks.
  2. **Thread-specific Close vs Global Close**: Implement a thread-specific `close()` that only closes the calling thread's connection (removing it from the tracked list) to prevent concurrent workers from closing each other's connections. Use a distinct `close_all()` method at the very end of the test suite (or class lifecycle) to release all connection handles.
  3. **OTel Graceful Shutdown**: Register a session-level autouse fixture in `conftest.py` that checks for `TracerProvider` and calls `provider.shutdown()` to flush and close span processors before pytest exits and closes standard I/O streams.
**Why**: Prevents infinite deadlocks, resolves Windows `PermissionError` (access denied) when deleting test directories, and cleans up test stdout pollution from closed file trace logs.
**Tags**: #sqlite #concurrency #deadlock #opentelemetry #pytest #resource-cleanup
