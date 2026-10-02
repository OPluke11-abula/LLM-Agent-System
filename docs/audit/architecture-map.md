# LAS Architecture Map: Logical, Execution & Persistence Models

**Audit Phase**: Phase 1 — Architecture Reconstruction  
**Inspection Date**: 2026-09-14  
**Protocol Version**: 3.8.0  
**Authority**: Invariant 0.1 (調研先行 / Anti-Summary Invariant)  
**Deliverable**: Gate 1 — Architecture Map

---

## 1. Logical Architecture

The LLM Agent System (LAS) follows a layered governance architecture. Domain rules and verification invariants strictly lead execution, tool dispatch, and state persistence.

```mermaid
graph TD
    subgraph Presentation & Control Layer
        API["FastAPI REST Endpoints<br>agent_workspace/api.py:32<br>routes/missions.py:35"]
        CLI["CLI Command Hub<br>agent_workspace/cli.py:53"]
    end

    subgraph Governance & Policy Layer
        PolicyGate["UnifiedPolicyGate<br>agent_workspace/core/policy_gate.py:85"]
        Prechecker["SkillsPrechecker & AstTaint<br>agent_workspace/core/precheck.py:315"]
        Committee["ReviewCommittee<br>agent_workspace/core/pipeline/committee.py:40"]
        ScopeGuard["ScopeGuard<br>agent_workspace/core/agent_executor.py:166"]
    end

    subgraph Orchestration & Lifecycle Layer
        PipelineMgr["CodingPipelineManager<br>agent_workspace/core/pipeline/manager.py:60"]
        MissionSM["MissionStateMachine<br>agent_workspace/core/mission_state_machine.py:44"]
        AgentEngine["AgentEngine & Router<br>agent_workspace/core/engine.py:68<br>core/router.py:202"]
        WorkflowEngine["WorkflowEngine<br>agent_workspace/core/workflow_engine.py:125"]
    end

    subgraph Execution & Tool Boundary
        AgentExec["AgentExecutor<br>agent_workspace/core/agent_executor.py:270"]
        ToolReg["GovernedToolRegistry<br>agent_workspace/core/agent_executor.py:222"]
        WorktreeMgr["WorktreeManager<br>agent_workspace/core/git_worktree.py:73"]
        SubprocessSandbox["Subprocess Sandbox<br>agent_workspace/core/sandbox.py:44"]
    end

    subgraph Persistence & Audit Layer
        MissionStore["SqliteMissionStore / JsonFileMissionStore<br>agent_workspace/core/mission_store.py:82,210"]
        AuditLedger["AuditLedger (SHA-256 Hash Chain & Merkle Tree)<br>agent_workspace/core/audit_ledger.py:42"]
        RuntimeEvents["RuntimeEventsLedger<br>agent_workspace/core/runtime_events.py:40"]
    end

    Presentation & Control Layer --> Governance & Policy Layer
    Presentation & Control Layer --> Orchestration & Lifecycle Layer
    Orchestration & Lifecycle Layer --> Governance & Policy Layer
    Orchestration & Lifecycle Layer --> Execution & Tool Boundary
    Execution & Tool Boundary --> Governance & Policy Layer
    Execution & Tool Boundary --> Persistence & Audit Layer
    Orchestration & Lifecycle Layer --> Persistence & Audit Layer
```

### 1.1 Layer Definitions & Interface Contracts

| Layer | Primary Responsibilities | Concrete Source Files | Exposed Contracts & Interfaces |
| :--- | :--- | :--- | :--- |
| **Presentation & Control** | Ingress of user requirements, mission creation, approval handling, REST routing, and CLI interaction. | [`agent_workspace/api.py:32`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/api.py#L32)<br>[`agent_workspace/routes/missions.py:35`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/routes/missions.py#L35)<br>[`agent_workspace/cli.py:53`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/cli.py#L53) | `create_app()` -> `FastAPI`<br>`missions_router` -> HTTP endpoints<br>`cli.main()` -> Subcommand parsers |
| **Governance & Policy** | Invariant enforcement: AST taint checking, role boundaries, scope validation, anti-self-approval, and committee consensus. | [`agent_workspace/core/policy_gate.py:85`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/policy_gate.py#L85)<br>[`agent_workspace/core/precheck.py:315`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/precheck.py#L315)<br>[`agent_workspace/core/pipeline/committee.py:40`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/pipeline/committee.py#L40)<br>[`agent_workspace/core/agent_executor.py:166`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/agent_executor.py#L166) | `UnifiedPolicyGate.evaluate(request)`<br>`run_all_prechecks(task_dir)`<br>`ReviewCommittee.evaluate(worktree, diff, receipts)`<br>`ScopeGuard.validate_tool_call(tool, params)` |
| **Orchestration & Lifecycle** | Deterministic stage progression (Plan -> Code -> Verify -> Review -> Deliver), state transition control, and event triggering. | [`agent_workspace/core/pipeline/manager.py:60`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/pipeline/manager.py#L60)<br>[`agent_workspace/core/mission_state_machine.py:44`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/mission_state_machine.py#L44)<br>[`agent_workspace/core/engine.py:68`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/engine.py#L68)<br>[`agent_workspace/core/workflow_engine.py:125`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/workflow_engine.py#L125) | `CodingPipelineManager.execute_pipeline(request)`<br>`MissionStateMachine.transition(mission, request)`<br>`AgentEngine.execute_task(task)`<br>`WorkflowEngine.run(graph, state)` |
| **Execution & Tool Boundary** | Filesystem isolation via Git worktrees, governed tool registry dispatch, command execution sandboxes. | [`agent_workspace/core/agent_executor.py:270`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/agent_executor.py#L270)<br>[`agent_workspace/core/agent_executor.py:222`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/agent_executor.py#L222)<br>[`agent_workspace/core/git_worktree.py:73`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/git_worktree.py#L73)<br>[`agent_workspace/core/sandbox.py:44`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/sandbox.py#L44) | `AgentExecutor.execute_step(tool, params)`<br>`GovernedToolRegistry.dispatch(tool_name, args)`<br>`WorktreeManager.create_worktree(...)`<br>`run_sandboxed_command(cmd, cwd, timeout)` |
| **Persistence & Audit** | Durable mission aggregate store, cryptographically chained audit events (SHA-256), Merkle root calculation, telemetry events. | [`agent_workspace/core/mission_store.py:210`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/mission_store.py#L210)<br>[`agent_workspace/core/audit_ledger.py:42`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/audit_ledger.py#L42)<br>[`agent_workspace/core/runtime_events.py:40`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/runtime_events.py#L40) | `SqliteMissionStore.save(mission)` / `.get(id)`<br>`AuditLedger.record_event(...)` / `.verify_chain_integrity()`<br>`RuntimeEventsLedger.append(event)` |

---

## 2. Execution Architecture

The execution architecture governs thread execution, process boundaries, asynchronous event loops, and concurrency constraints.

### 2.1 Process and Thread Isolation Model

```mermaid
sequenceDiagram
    participant MainProc as Main Python Process (FastAPI / CLI / Script)
    participant ThreadPool as AnyIO / asyncio ThreadPoolExecutor
    participant SubProc as Subprocess Sandbox (git / pytest / ruff)
    participant SQLite as SQLite3 Engine (WAL Mode)

    MainProc->>ThreadPool: Dispatch synchronous blocking I/O (MissionStore, Git)
    ThreadPool->>SubProc: subprocess.run(cmd, capture_output=True, timeout=30-60s)
    SubProc-->>ThreadPool: exit_code, stdout, stderr
    ThreadPool->>SQLite: PRAGMA journal_mode=WAL; BEGIN IMMEDIATE
    SQLite-->>ThreadPool: Commit Transaction
    ThreadPool-->>MainProc: Return async response
```

1. **Process Boundary**:
   - The LAS server or test runner operates as a single OS process running Python 3.11+.
   - Tool operations that modify files, run verification tests, or manipulate git branches execute as **child subprocesses** via `subprocess.run` inside [`agent_workspace/core/sandbox.py:44`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/sandbox.py#L44) and [`agent_workspace/core/git_worktree.py:42`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/git_worktree.py#L42).
   - Subprocesses are strictly bounded by timeout limits (default `30s` to `120s` for pytest) to prevent runaway execution or deadlocks.

2. **Async Loops vs. Synchronous Execution**:
   - **Async HTTP Tier**: [`agent_workspace/routes/missions.py`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/routes/missions.py#L65) uses `async def` endpoints running on Uvicorn's `asyncio` event loop.
   - **Synchronous Domain Engine**: `MissionStateMachine.transition()` ([`mission_state_machine.py:44`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/mission_state_machine.py#L44)) and `CodingPipelineManager.execute_pipeline()` ([`pipeline/manager.py:295`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/pipeline/manager.py#L295)) are synchronous deterministic functions. In the web server, blocking operations are executed synchronously or dispatched to workers.

3. **Concurrency Control & Race Elimination**:
   - **State Machine Atomicity**: Transitions in `MissionStateMachine` are pure synchronous mutations validated against current state and transition request.
   - **Database Concurrency**: `SqliteMissionStore` uses SQLite with `PRAGMA foreign_keys = ON;` and WAL mode support. Transactions ensure atomicity for mission status transitions.
   - **Worktree Isolation**: Each pipeline session runs in a dedicated directory `.worktrees/<session_id>` preventing concurrent git branch collisions.

---

## 3. Persistence Architecture

LAS enforces strict data durability across mission aggregates, verification receipts, and cryptographic audit records.

### 3.1 Storage Schema & Durability Guarantees

| Storage Target | Engine & Physical Path | Data Model & Format | Durability & Integrity Guarantees |
| :--- | :--- | :--- | :--- |
| **Mission State** | SQLite: `missions.db`<br>Fallback: `missions/{mission_id}.json` | `(mission_id TEXT PK, state TEXT, data TEXT, created_at TEXT, updated_at TEXT)` | ACID transactions via SQLite. JSON store writes atomically via temporary files (`.tmp`) before renaming. |
| **Audit Ledger** | SQLite: `memory/audit_ledger.db` | `(event_id TEXT PK, timestamp TEXT, session_id TEXT, task_id TEXT, stage TEXT, event_type TEXT, payload TEXT, prev_hash TEXT, current_hash TEXT)` | Cryptographic SHA-256 hash chaining: `current_hash = SHA256(prev_hash + timestamp + payload)`. Built-in Merkle root verification. |
| **Runtime Events** | SQLite: `memory/runtime_events.db` | `(event_id TEXT PK, session_id TEXT, step_index INT, event_type TEXT, data TEXT, timestamp TEXT)` | Append-only event store for telemetry and live dashboard streaming. |
| **Verification Receipts** | Embedded in `CodingPipelineResult` & persisted in `AuditLedger` payload | JSON serialized `VerificationReceipt(step_name, command, exit_code, stdout, stderr, duration_ms, status)` | Verifiable exit codes and outputs linked to git commit hash and PR payload. |
| **Source Code Worktrees** | Git worktree directories: `.worktrees/{session_id}` | Git commit objects and isolated branch trees | Git SHA-1/SHA-256 commit tree immutability. Uncommitted work protected from main branch contamination. |

### 3.2 Audit Chain Cryptographic Integrity

Each event in `AuditLedger` enforces the cryptographic chain:

$$\text{Hash}_0 = \text{SHA-256}("0" + \text{timestamp}_0 + \text{payload}_0)$$
$$\text{Hash}_n = \text{SHA-256}(\text{Hash}_{n-1} + \text{timestamp}_n + \text{payload}_n)$$

The `calculate_merkle_root(session_id)` function ([`audit_ledger.py:155`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/audit_ledger.py#L155)) compiles all event hashes into a single root signature:
- Any alteration to past event payloads invalidates both the sequential hash chain and the final Merkle root.
- Verification is performed programmatically via `AuditLedger.verify_chain_integrity(session_id)` ([`audit_ledger.py:180`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/audit_ledger.py#L180)).

---

## 4. Verification & Validation Summary

- **Logical Layer Isolation**: Presentation, Lifecycle, Policy, Execution, and Persistence are cleanly segregated.
- **Synchronous Governance**: All policy enforcement gates are synchronous checks executed before any I/O side effects occur.
- **Audit Tamper-Evidence**: Built-in cryptographic hash verification and Merkle tree roots guarantee non-repudiation.
