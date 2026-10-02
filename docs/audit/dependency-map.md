# LAS Module Dependency Map

**Audit Phase**: Phase 1 — Architecture Reconstruction  
**Inspection Date**: 2026-09-14  
**Protocol Version**: 3.8.0  
**Authority**: Invariant 0.1 (調研先行 / Anti-Summary Invariant)  
**Deliverable**: Gate 1 — Dependency Map

---

## 1. Dependency Analysis Framework

This dependency map documents the concrete invocation and mutation hierarchy across the codebase, formatted strictly as:

$$\text{Module} \longrightarrow \text{Depends on} \longrightarrow \text{Calls} \longrightarrow \text{Mutates}$$

All citations reference primary source code and line numbers in `agent_workspace/`.

---

## 2. Core Dependency Matrix

| Module | Depends on (Imports / Components) | Calls (Functions / Methods / APIs) | Mutates (In-Memory State / Persistent State / System) |
| :--- | :--- | :--- | :--- |
| **`mission_model.py`**<br>([`agent_workspace/core/mission_model.py`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/mission_model.py)) | `dataclasses`, `enum`, `datetime`, `uuid`, `typing` | `uuid4()` (`:228`)<br>`datetime.now()` (`:230`)<br>`_validate_actor()` (`:294`) | Mutates `Mission` aggregate: `current_state`, `approval_gates`, `evidence_history`, `updated_at`. |
| **`mission_state_machine.py`**<br>([`agent_workspace/core/mission_state_machine.py`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/mission_state_machine.py)) | `mission_model.py`, `mission_contracts.py` | `_LEGAL_TRANSITIONS.get()` (`:220`)<br>`_require_plan_approval()` (`:142`)<br>`_require_scope_approval()` (`:162`)<br>`_subject_or_error()` (`:119`) | Mutates `Mission.current_state` (`:235`), appends to `Mission.transition_history`, appends to `Mission.approval_gates` (`:298`). |
| **`mission_store.py`**<br>([`agent_workspace/core/mission_store.py`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/mission_store.py)) | `sqlite3`, `json`, `pathlib.Path`, `mission_model.py` | `sqlite3.connect()` (`:218`)<br>`cursor.execute()` (`:238`)<br>`json.dumps()` / `json.loads()` (`:143,248`)<br>`tempfile.NamedTemporaryFile` + `replace()` (`:156`) | Mutates SQLite DB (`missions` table rows in `missions.db`) or filesystem JSON files (`missions/{mission_id}.json`). |
| **`mission_contracts.py`**<br>([`agent_workspace/core/mission_contracts.py`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/mission_contracts.py)) | `pydantic.BaseModel`, `pydantic.field_validator` | `field_validator()` (`:187`)<br>`prevent_self_approval()` (`:188`) | Immutable validation contracts; mutates zero external state. |
| **`pipeline/manager.py`**<br>([`agent_workspace/core/pipeline/manager.py`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/pipeline/manager.py)) | `git_worktree.py`, `agent_executor.py`, `audit_ledger.py`, `committee.py`, `precheck.py` | `WorktreeManager.create_worktree()` (`:293`)<br>`IScopedExecutor.execute_plan()` (`:301`)<br>`IVerificationRunner.run_verification_ladder()` (`:311`)<br>`WorktreeManager.commit_changes()` (`:390`)<br>`AuditLedger.record_event()` (`:102`) | Creates Git worktree on disk (`.worktrees/{session_id}`), mutates Git repository state via commits, records rows in `audit_ledger.db`. |
| **`pipeline/committee.py`**<br>([`agent_workspace/core/pipeline/committee.py`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/pipeline/committee.py)) | `pydantic.BaseModel`, `logging`, `typing` | `_evaluate_reviewer()` (`:58`)<br>`_compute_consensus()` (`:110`) | Read-only evaluation; returns immutable `CommitteeDebateRecord` / `ReviewVote`. Mutates zero persistent state. |
| **`pipeline/benchmark.py`**<br>([`agent_workspace/core/pipeline/benchmark.py`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/pipeline/benchmark.py)) | `pipeline/manager.py`, `git_worktree.py`, `tempfile` | `CodingPipelineManager.execute_pipeline()` (`:120`)<br>`tempfile.mkdtemp()` (`:115`) | Creates transient test repositories, invokes Git CLI, executes verification ladders. |
| **`agent_executor.py`**<br>([`agent_workspace/core/agent_executor.py`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/agent_executor.py)) | `subprocess`, `pathlib.Path`, `audit_ledger.py`, `sandbox.py` | `ScopeGuard.validate_tool_call()` (`:166,226,244`)<br>`run_sandboxed_command()` (`:248`)<br>`AuditLedger.record_event()` (`:288`) | Mutates files on disk via `filesystem_write` (`:228`), mutates worktree state via shell commands. |
| **`git_worktree.py`**<br>([`agent_workspace/core/git_worktree.py`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/git_worktree.py)) | `subprocess`, `pathlib.Path`, `shutil` | `subprocess.run(["git", "worktree", ...])` (`:82`)<br>`subprocess.run(["git", "commit", ...])` (`:104`)<br>`subprocess.run(["git", "worktree", "remove", ...])` (`:116`) | Creates/deletes directories at `.worktrees/{session_id}`; mutates local git reflog, branch pointers, and HEAD. |
| **`sandbox.py`**<br>([`agent_workspace/core/sandbox.py`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/sandbox.py)) | `subprocess`, `os`, `sys`, `shlex` | `subprocess.run(cmd, cwd=..., timeout=...)` (`:55`) | Mutates environment variables and child OS process table. |
| **`audit_ledger.py`**<br>([`agent_workspace/core/audit_ledger.py`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/audit_ledger.py)) | `sqlite3`, `hashlib`, `json`, `datetime` | `hashlib.sha256()` (`:112,168`)<br>`cursor.execute("INSERT INTO audit_events...")` (`:118`)<br>`conn.commit()` (`:124`) | Appends immutable rows into `audit_events` table in `memory/audit_ledger.db`. |
| **`policy_gate.py`**<br>([`agent_workspace/core/policy_gate.py`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/policy_gate.py)) | `ast`, `pydantic`, `re`, `pathlib.Path` | `ast.parse()` (`:105`)<br>`ast.walk()` (`:108`)<br>`_check_role_scope()` (`:120`) | Read-only static analysis and AST traversal. Mutates zero persistent state. |
| **`precheck.py`**<br>([`agent_workspace/core/precheck.py`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/precheck.py)) | `subprocess`, `ast`, `shutil`, `psutil` | `subprocess.run(["git", "status", ...])` (`:82`)<br>`ast.parse()` (`:210`)<br>`check_stop_and_wait_gate()` (`:120`) | Read-only pre-flight checks; mutates zero external or persistent state. |
| **`runtime_events.py`**<br>([`agent_workspace/core/runtime_events.py`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/runtime_events.py)) | `sqlite3`, `json`, `datetime` | `cursor.execute("INSERT INTO runtime_events...")` (`:110`)<br>`conn.commit()` (`:115`) | Appends telemetry event rows into `memory/runtime_events.db`. |
| **`api.py` & `routes/missions.py`**<br>([`agent_workspace/api.py`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/api.py), [`routes/missions.py`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/routes/missions.py)) | `fastapi`, `pydantic`, `mission_store.py`, `mission_state_machine.py` | `MissionStore.save()` (`routes/missions.py:102`)<br>`MissionStateMachine.transition()` (`routes/missions.py:145`) | Triggers domain mutations via HTTP; persists mission rows to SQLite. |
| **`cli.py`**<br>([`agent_workspace/cli.py`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/cli.py)) | `argparse`, `sys`, `pipeline/manager.py`, `mission_store.py` | `CodingPipelineManager.execute_pipeline()` (`:140`)<br>`run_all_prechecks()` (`:98`) | Dispatches CLI tasks, printing outputs to stdout/stderr. |

---

## 3. Coupling & Architectural Integrity Analysis

1. **Clean Separation of Concerns**:
   - `policy_gate.py`, `precheck.py`, and `committee.py` are strictly **read-only evaluators**. They compute invariants and return structured receipts without side-effect mutations.
   - All state mutations are channeled into explicit persistence boundaries: `SqliteMissionStore` (aggregate states), `AuditLedger` (audit logs), and `WorktreeManager` (git mutations).
2. **Hardened Enforcement Points (P0/P1)**:
   - Tool execution (`agent_executor.py:226,244`) binds directly to `ScopeGuard.validate_tool_call` before calling `filesystem_write` or `shell_exec`.
   - Direct calls to `GovernedToolRegistry` without going through `AgentExecutor` are intercepted and validated.
3. **Anti-Self-Approval Isolation**:
   - `ApprovalRequest.prevent_self_approval` ([`mission_contracts.py:188`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/mission_contracts.py#L188)), `Mission.add_approval_gate` ([`mission_model.py:294`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/mission_model.py#L294)), and `check_stop_and_wait_gate` ([`precheck.py:120`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/precheck.py#L120)) strictly reject approvals submitted by agent roles or matching requester IDs.
