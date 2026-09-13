---
tags:
  - architecture/leaf
  - runtime/discussion
  - consensus/debate
  - layer/l3
type: module_leaf
layer: L3-Runtime-Execution-and-Swarm
module: agent_workspace.core.discussion_room
file_path: agent_workspace/core/discussion_room.py
sync_status: verified
---

# Module: DiscussionRoom (Multi-Agent Debate, Verifier & Consensus Engine)

## 1. Three-Line Architectural Annotation
- **Responsibility**: Orchestrates structured multi-agent deliberation, round-robin debate rounds, verifier verdicts, and cryptographic consensus generation (ProofOfConsensus).
- **Invariant**: Consensus decisions require unanimous or supermajority signatures from registered quorum roles before mutating actions can be approved.
- **Data Flow**: Consumes task briefs, coordinates turns across grounded roles, extracts verifier critiques via create_verifier_verdict, and packages signed proofs into ProofOfConsensus.

---

## 2. Source Code & Symbol Mapping

**Source Location**: [discussion_room.py](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/discussion_room.py) (1680 lines)

### Symbol Table

| Symbol | Kind | Line Range | Description |
| :--- | :--- | :--- | :--- |
| DiscussionRoleContract | class | L48-L64 | Schema defining participating agent constraints, persona prompts, and evaluation criteria. |
| VerifierVerdict | class | L68-L91 | Container holding verification score, critique points, passed/failed boolean, and citations. |
| DiscussionRoom | class | L94-L1461 | Primary orchestrator managing multi-agent debate sessions, turns, and context compaction. |
| _append_role_learning_guide | def | L109-L152 | Injects historical self-learning lessons and error post-mortems into agent role context. |
| _budgeted_complete | def | L270-L309 | LLM call wrapper enforcing strict token budget limits per discussion turn. |
| _invoke_llm_healing | def | L424-L505 | Autonomous reflection when agent outputs violate discussion formatting contracts. |
| _compact_transcript | def | L572-L647 | Compresses historical discussion turns using AST-aware summarization to prevent context overflow. |
|
un | def | L750-L1170 | Main debate loop driving structured rounds (Proposal -> Critique -> Rebuttal -> Consensus). |
|
un_corporate_audit | def | L1172-L1239 | Specialized multi-agent audit evaluating code against corporate governance standards. |
|
un_milestone_reflection | def | L1241-L1375 | End-of-milestone retrospectives extracting lessons learned for the persistent memory OS. |
|
un_governance_vote | def | L1392-L1461 | Quorum voting mechanism tallying agent votes on architectural decisions. |
| ProofOfConsensus | class | L1465-L1648 | Cryptographic proof generator signing consensus agreements using Ed25519/HMAC. |
| create_consensus_certificate| def | L1512-L1541 | Assembles signed certificate including round digest, voter signatures, and timestamp. |
|
erify_consensus_certificate| def | L1544-L1587 | Verifies cryptographic signatures of all voters against swarm public keys. |
| SwarmIDS | class | L1651-L1680 | Swarm Intrusion Detection System detecting Byzantine or hallucinating agents and applying quarantine. |

---

## 3. Deliberation & Consensus Sequence

`mermaid
sequenceDiagram
    autonumber
    participant Client as Workflow / User
    participant Room as DiscussionRoom
    participant PO as ProductOwner
    participant Arch as Architect
    participant QA as QAEngineer
    participant Proof as ProofOfConsensus

    Client->>Room: run(task, rounds=3)
    Room->>PO: Generate Proposal
    PO-->>Room: Proposal Draft
    Room->>Arch: Critique Architecture & Invariants
    Arch-->>Room: Architectural Critique
    Room->>QA: Review Edge Cases & Test Strategy
    QA-->>Room: Test Critique & Acceptance Plan
    Room->>Proof: create_consensus_certificate(digest, signatures)
    Proof-->>Room: Signed Consensus Certificate
    Room-->>Client: Final Consensus Agreement + Proof
`

---

## 4. Operational Invariants & Anti-Corruption Guardrails
1. **Mandatory Verifier Turn**: No proposal can be approved without at least one dedicated verifier critique turn.
2. **IDS Quarantine Threshold**: An agent producing 3 consecutive malformed outputs is automatically quarantined by SwarmIDS.
3. **Cryptographic Nonce**: Every consensus certificate embeds a unique monotonic nonce to prevent replay attacks.

---

## 5. Verification & Test Evidence
- **Test Suites**:
  - [	est_discussion_room.py](file:///d:/GitHub/LLM-Agent-System/agent_workspace/tests/test_discussion_room.py)
  - [	est_discussion_room_characterization.py](file:///d:/GitHub/LLM-Agent-System/agent_workspace/tests/test_discussion_room_characterization.py)
  - [	est_swarm_governance.py](file:///d:/GitHub/LLM-Agent-System/agent_workspace/tests/test_swarm_governance.py)
- **Execution Receipt**: Bytecode validated via compileall exit code 0.

---

## 6. Topological Linkage
- **Upstream Layer**: [[L3-Runtime-Execution-and-Swarm]]
- **Lifecycle Machine**: [[30 Concurrency Lifecycle & Swarm State Machine]]
- **Collaborating Modules**:
  - [[core-agent-crew]]
  - [[core-policy-gate]]
  - [[core-audit-ledger]]
  - [[core-memory]]
