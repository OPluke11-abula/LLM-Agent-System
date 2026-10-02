# Phase 0 Baseline Report: LLM Agent System (LAS)

**Audit Phase**: Phase 0 — Baseline Establishment (Milestone M0)  
**Execution Date**: 2026-09-14  
**Protocol Version**: 3.8.0  
**Authority**: Invariant 0.1 (調研先行 / Anti-Summary Invariant)  

---

## 1. Repository State Baseline

| Dimension | Baseline Value | Verification Method |
| :--- | :--- | :--- |
| **Git Branch** | `main` | `git branch --show-current` |
| **Base Commit SHA** | `0dd78a0185019316f4a7494e1cf9b2fa871c3bb6` | `git rev-parse HEAD` |
| **Protocol Specification** | Version `3.8.0` | `.agent/state.md` & `AGENTS.md` |
| **Python Runtime** | Python `3.14.7` (Windows x86_64) | `uv run python --version` |
| **Package / Environment Manager** | `uv` (Fast Python Package Manager) | `uv --version` |
| **Host Workspace Path** | `D:\GitHub\LLM-Agent-System` | `Get-Location` |
| **Build / Compile Status** | Clean (All 15 core python files compiled) | `scripts\verify.ps1` Step 1 |

---

## 2. Test Suite Baseline

A complete static collection and regression run across the test inventory under `agent_workspace/tests/` yields the following baseline:

| Metric | Measured Value | Notes |
| :--- | :--- | :--- |
| **Total Collected Tests** | **888** | Collected via `pytest --collect-only -q` across 54 test modules |
| **Core Architecture Regression Tests** | **75 / 75 PASSED (100%)** | `test_agent_executor_p2c`, `test_coding_pipeline_p1`, `test_policy_gate`, `test_git_guard`, `test_mission_integrity`, `test_mission_contracts`, `test_mission_store` |
| **Governance Negative Tests** | **7 / 7 PASSED (100%)** | `agent_workspace/tests/test_governance_negative.py` |
| **Adversarial Governance Tests** | **6 / 6 PASSED (100%)** | `agent_workspace/tests/test_adversarial_governance.py` |
| **State & Recovery Tests** | **5 / 5 PASSED (100%)** | `agent_workspace/tests/test_state_recovery.py` |
| **Golden Benchmark Suite** | **3 / 3 Scenarios PASSED** | Suite `GBS-1789320554` (`GOLDEN_FLOW_VERIFIED`) |
| **Full LAS Verification Ladder** | **PASS (Exit Code 0)** | `.\scripts\verify.ps1 -SkipViewer` |

---

## 3. Runtime Mission Lifecycle Baseline

A standard reference mission lifecycle execution was recorded under `scripts/run_golden_benchmark.py`:

```
1. INTAKE:
   - Requirement accepted: "Implement divide(a, b) with zero-division validation..."
   - Preflight verified: Anti-Summary Invariant checked across primary source files.
   - Assigned Specialist Role: DOMAIN_LOGIC_AGENT.

2. PLANNING & GATING:
   - ScopedMutationPlan generated: Target files ["src/math_service.py", "tests/test_math.py"].
   - Stop-and-Wait Architecture Gate: Confirmed with human token BENCHMARK_TOKEN_APPROVED.
   - Role Scope Restriction: Confirmed compliant with ROLE_SCOPE_RESTRICTIONS.

3. ISOLATED MUTATION:
   - Worktree created at isolated branch: bench/scenario_happy_path_feature.
   - Host workspace canonical checkout: 100% PRESERVED (0 host modifications).
   - Scoped executor applied minimal diffs to target files only.

4. VERIFY & EVIDENCE:
   - Verification ladder executed: "python -m unittest tests/test_math.py".
   - Exit Code: 0 (All tests passed).
   - Receipt generated and recorded to AuditLedger with Merkle hash.

5. REVIEW & DELIVERY:
   - Multi-agent committee evaluated diff lines (< 500 lines) and verification evidence.
   - Draft PR branch generated: feat(BM-SCENARIO_HAPPY_PATH_FEATURE): Verified by LAS Autonomous Pipeline.
   - Event logged: pipeline_stage_completed.
```

---

## 4. Known Limitations & Gaps Identified Pre-Optimization

1. **Policy Gate Disconnection (GAP-01)**: Legacy `AgentEngine.execute_tool` does not invoke `UnifiedPolicyGate`.
2. **Self-Approval Risk (GAP-02)**: Without contract guards, autonomous agents could approve their own approval gates.
3. **Direct Tool Reference Bypass (GAP-03)**: Direct method calls to `GovernedToolRegistry` bypassed `ScopeGuard`.
4. **Reviewer Role Scope (GAP-04)**: `QA_TEST_AGENT` and `PERFORMANCE_LATENCY_AGENT` were missing from `ROLE_SCOPE_RESTRICTIONS`.
5. **Empty Ladder False Green (GAP-05)**: Empty verification ladder produced 0 receipts, trivially passing.
6. **Dual Ledgers (GAP-07)**: Separate SQLite ledgers (`memory/audit_ledger.db` vs `memory/runtime_events.db`).

---

## 5. Gate 0 Evaluation & Sign-off

- [x] Repository state, commit SHA, and branch unambiguously recorded.
- [x] Test baseline collected (888 tests) and core regression baseline verified (100% pass).
- [x] Runtime mission lifecycle end-to-end execution verified and reproducible.
- [x] Known limitations and risk areas cataloged.

**Gate 0 Status**: **`PASSED`** (Proceeding to Phase 1: Architecture Reconstruction).
