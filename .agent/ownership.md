# Team Ownership and Responsibility Matrix

**Protocol Version**: 3.8.0
**Coordination Model**: Feature-Based Ownership (一人一功能垂直切片全棧負責制)
**Governance Authority**: Luke (PO / Domain Owner)

---

## 1. Domain Ownership & Mutable Boundaries

| Owner | Primary Feature / Scope | Mutable Repository Boundary | Designated Specialist Agent |
|---|---|---|---|
| **Luke** | PO, Domain Architecture, Review, Consensus & Integration | `agent_workspace/core/`, `.agent/`, `spec/`, global RFCs | `DOMAIN_LOGIC_AGENT`, `ARCHITECT_PLANNER_AGENT`, `INTEGRATION_MERGE_AGENT` |
| **Joe** | Control Plane UI/UX, Presentation, Desktop Experience | `viewer/`, `viewer/src/`, UI tests | `UI_UX_AGENT` |
| **Ethan** | Backend Runtime, Data Persistence, IPC & Network Gateways | `agent_workspace/core/`, `agent_workspace/db/`, `agent_workspace/api/`, backend tests | `BACKEND_INFRA_AGENT` |
| **Eason** | State Flow, Concurrency Lifecycle, Request Orchestration | `agent_workspace/core/workflow_engine.py`, `agent_workspace/core/engine.py` | `APPLICATION_FLOW_AGENT` |
| **Jimmy** | Verification Automation, CI & Regression Integration | `agent_workspace/tests/`, `scripts/`, `docs/evidence/` | `QA_TEST_AGENT`, `INTEGRATION_MERGE_AGENT` |

---

## 2. Universal Reviewer Roles (Shared by All)

The following roles operate with read-only authority across all boundaries unless explicitly authorized for a specific remediation task:

- **`SECURITY_AUDIT_AGENT`**: Read-only audit authority. Scans for hardcoded tokens, SQL injections, IPC leaks, and secret exposure.
- **`PERFORMANCE_LATENCY_AGENT`**: Resource lifecycle governance. Investigates thread lockups, connection leaks, IPC roundtrips, and token overhead.
- **`QA_TEST_AGENT`**: Verification authority. Enforces "Evidence before completion invariant" (`PASS`, `FAIL`, `BLOCKED`, `NOT_RUN`, `UNVERIFIED`).
- **`KNOWLEDGE_TOPOLOGY_AGENT`**: Knowledge graph topology, Obsidian/Notion sync, code annotations freshness, and anti-rot governance.

---

## 3. Hard Invariants & Cross-Boundary Prohibitions

1. **`UI_UX_AGENT`**: Strictly prohibited from writing SQL, modifying backend DB schemas, touching IPC pipes, or altering core backend runtime logic.
2. **`BACKEND_INFRA_AGENT`**: Strictly prohibited from editing frontend React/Tauri view widgets or leaking raw SQL to presentation surfaces.
3. **`DOMAIN_LOGIC_AGENT`**: Must remain framework-agnostic. Strictly prohibited from introducing direct Flutter, Tauri, Win32, or raw ORM dependencies into the pure domain core.
4. **`APPLICATION_FLOW_AGENT`**: Strictly prohibited from issuing raw SQL or raw OS syscalls; must enforce `latest-request-wins` race elimination.
5. **`INTEGRATION_MERGE_AGENT`**: Prohibited from executing fast-forward merges without green regression evidence across all suites.
6. **No Boundary Crossing**: No Agent may modify files outside its assigned mutable boundary without explicit PO approval.
