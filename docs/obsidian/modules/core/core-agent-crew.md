---
tags:
  - architecture/leaf
  - runtime/swarm
  - grounded_roles
  - layer/l3
type: module_leaf
layer: L3-Runtime-Execution-and-Swarm
module: agent_workspace.core.agent_crew
file_path: agent_workspace/core/agent_crew.py
sync_status: verified
---

# Module: AgentCrew (10 Grounded Swarm Roles & Checkpoint Registry)

## 1. Three-Line Architectural Annotation
- **Responsibility**: Houses the 10 Grounded Swarm Agent definitions (PO, Architect, BackendDev, FrontendDev, DevOps, QAEngineer, SecurityAuditor, DocWriter, CodeReviewer, RefactoringSpecialist) with host skill bindings and checkpoint signatures.
- **Invariant**: Every role possesses an explicit, non-overlapping mutable boundary (allowed_patterns); modifications outside assigned boundaries are blocked by policy gate.
- **Data Flow**: Accepts task assignments, synthesizes specialized role prompts grounded in protocol v3.8.0, invokes LLM providers, and signs intermediate checkpoints with HMAC-SHA256.

---

## 2. Source Code & Symbol Mapping

**Source Location**: [agent_crew.py](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/agent_crew.py) (621 lines)

### Symbol Table

| Symbol | Kind | Line Range | Description |
| :--- | :--- | :--- | :--- |
| GROUNDED_ROLES | dict | L16-L89 | Grounded dictionary defining the 10 roles, responsibilities, allowed mutable patterns, and host skills. |
| CrewRegistry | class | L92-L201 | In-memory swarm node topology registry tracking alive status, heartbeat timestamps, and peer roles. |
| clear | def | L102-L104 | Resets registry state between test fixtures. |
|
egister_node | def | L107-L150 | Registers an agent node in the swarm with role metadata, host port, and capabilities. |
| update_node_status | def | L153-L157 | Updates active node heartbeat and health state (ONLINE, BUSY, OFFLINE). |
| get_topology | def | L160-L201 | Exports live swarm topology dictionary formatted for frontend graph renderers. |
| AgentCrew | class | L204-L621 | Execution engine dispatching prompts to grounded roles and verifying checkpoint integrity. |
| _async_dispatch_to_role | def | L218-L265 | Async worker executing role-specific inference loops with retry backoff. |
| dispatch_to_role | def | L267-L519 | Primary dispatch entry point; prepares prompts, binds skills, and streams role execution. |
| generate_checkpoint_signature | def | L522-L537 | Signs task checkpoint payload using HMAC-SHA256 to ensure tamper-proof handoff states. |
|
erify_checkpoint_signature | def | L540-L561 | Verifies checkpoint signature against stored public/secret keys before resuming execution. |
| save_checkpoint | def | L563-L602 | Persists signed checkpoint JSON to .agent/runs/ with state digest. |
| get_checkpoint | def | L604-L616 | Hydrates verified checkpoint from disk. |
| get_grounded_roles | def | L619-L621 | Returns immutable copy of the 10 Grounded Roles definitions. |

---

## 3. 10 Grounded Roles Topology & Boundary Table

`
+-------------------------------------------------------------------------------+
|                             10 Grounded Roles Matrix                          |
+----------------------+-----------------------------+--------------------------+
| Role                 | Mutable Boundary Pattern    | Primary Host Skills      |
+----------------------+-----------------------------+--------------------------+
| ProductOwner         | docs/prd/**, .agent/**      | to-prd, to-issues        |
| Architect            | docs/obsidian/**, .agent/** | design-markdown          |
| BackendDev           | agent_workspace/core/**     | tdd, test-driven-dev     |
| FrontendDev          | viewer/src/**               | aesthetic-design-system  |
| DevOpsEngineer       | scripts/**, .github/**      | setup-pre-commit         |
| QAEngineer           | agent_workspace/tests/**    | verification-before-comp |
| SecurityAuditor      | security/**, spec/security* | security-audit, pentest  |
| DocumentationWriter  | docs/**, *.md               | doc-coauthoring, unslop  |
| CodeReviewer         | Read-only (Review Findings) | code-review, open-review |
| RefactorSpecialist   | Refactor targets only       | goal-sloc, unslop        |
+----------------------+-----------------------------+--------------------------+
`

---

## 4. Operational Invariants & Anti-Corruption Guardrails
1. **Zero Swallowed Exceptions**: Exception handlers in dispatch loops must log explicit debug traces (logger.debug(...)); bare pass is strictly banned.
2. **Signed Checkpoint Verification**: Resuming any execution state without a valid HMAC signature raises SecurityCheckpointViolation.
3. **Role Boundary Enforcement**: A role attempting to edit outside its designated pattern triggers an immediate policy abort via [[core-policy-gate]].

---

## 5. Verification & Test Evidence
- **Test Suites**:
  - [	est_discussion_room.py](file:///d:/GitHub/LLM-Agent-System/agent_workspace/tests/test_discussion_room.py)
  - [	est_runtime_features.py](file:///d:/GitHub/LLM-Agent-System/agent_workspace/tests/test_runtime_features.py)
- **Execution Receipt**: Bytecode validated via compileall exit code 0.

---

## 6. Topological Linkage
- **Upstream Layer**: [[L3-Runtime-Execution-and-Swarm]]
- **Roles Matrix**: [[70 Multi-Agent Protocol v3.8.0 & 10 Grounded Roles Matrix]]
- **Collaborating Modules**:
  - [[core-policy-gate]]
  - [[core-discussion-room]]
  - [[core-audit-ledger]]
