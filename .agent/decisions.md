# Architectural Decisions Log (ADR)

This file records durable, project-wide architectural decisions. New entries must be agreed upon by PO Luke and verified against primary sources before being marked `ACCEPTED`.

---

## ADR-001: Adoption of Universal Coding Agent Development Protocol v3.8.0
- **Status**: ACCEPTED
- **Date**: 2026-09-10
- **Decision**: Formally adopt `Universal_Coding_Agent_Development_Protocol.md` (v3.8.0) as the repository multi-agent coordination standard.
- **Consequences**:
  - All new agent sessions must execute the standard bootstrap sequence starting from `AGENTS.md`.
  - Coordination state is grounded in `.agent/state.md` with explicit version lock.
  - Coordination mode is initialized as `STATIC_DOMAIN_OWNERSHIP`.

---

## ADR-002: Implementation of the Three-Tier Cognitive Relay Architecture
- **Status**: ACCEPTED
- **Date**: 2026-09-10
- **Decision**: Adopt the three-tier cognitive relay model proven in LingoLens:
  - **Tier 1 (`stage.md`)**: Real-time scratchpad for in-flight code and debug logs. Strictly `.gitignore`d.
  - **Tier 2 (`handoff.md` + Git)**: Team cognitive relay for verified facts, PR status, and plain-text summaries. Updated only after test suite passes 100%.
  - **Tier 3 (`docs/obsidian/` + Vault)**: Long-term knowledge topology. Updated with concise 3-line code annotations on leaf notes upon PR merge.
- **Consequences**: Eliminates context explosion, hallucination cascading, and session disconnects.

---

## ADR-003: Physical Grounding of 10 AI Agent Roles with Universal Memory
- **Status**: ACCEPTED
- **Date**: 2026-09-10
- **Decision**: Replace legacy toy roles (`CEO`, `Developer`, etc.) with 10 physical-grounded specialist roles:
  1. `UI_UX_AGENT`
  2. `BACKEND_INFRA_AGENT`
  3. `DOMAIN_LOGIC_AGENT`
  4. `APPLICATION_FLOW_AGENT`
  5. `INTEGRATION_MERGE_AGENT`
  6. `SECURITY_AUDIT_AGENT`
  7. `PERFORMANCE_LATENCY_AGENT`
  8. `QA_TEST_AGENT`
  9. `ARCHITECT_PLANNER_AGENT`
  10. `KNOWLEDGE_TOPOLOGY_AGENT`
- **Universal Baseline Memory**: Mount `obsidian-vault` and `obsidian-research-notes` across all Roles 1~10 as baseline memory skills.
- **Consequences**: Eliminates role hallucination; binds agents to concrete tools and strict mutable scope boundaries.

---

## ADR-004: Strict Enforcement of Seven Anti-Corruption Invariants
- **Status**: ACCEPTED
- **Date**: 2026-09-10
- **Decision**: Enforce Seven Anti-Corruption Principles across all code and pull requests:
  1. Dead Code Elimination
  2. Extreme Single Responsibility (KISS & High Cohesion)
  3. Concurrency & Race Elimination (`latest-request-wins`)
  4. Typed Failures Only (Zero empty catch blocks)
  5. Specification-First / Invariant-Driven
  6. Idempotence & Side-Effect Safety
  7. Configuration over Hardcoding
- **Consequences**: Halts code rot and prevents spaghetti debt from accumulating in LAS.

---

## ADR-005: Anti-Summary Invariant and Stop-and-Wait Architecture Gate
- **Status**: ACCEPTED
- **Date**: 2026-09-10
- **Decision**: Mandate bottom-up inspection of primary source files before formulating architecture plans. Require a concise diff proposal and explicit Human sign-off before modifying code.
- **Consequences**: Completely stops premature coding, hallucinated refactoring, and divergence from PO vision.

---

## ADR-006: Agent Strategy Integration & Task Environment Architecture
- **Status**: ACCEPTED
- **Date**: 2026-09-12
- **Decision**: Formally synthesize the engineering philosophies of Antigravity, Claude, and Codex into the LAS developer control plane:
  - **Antigravity (Design for Abundance)**: Agent capacity is abundant, parallelizable, and disposable. Useful parallelism over maximal parallelism; non-overlapping mutable scopes.
  - **Claude (Design for Failure & Containment)**: Never build autonomy on trust alone. Prompt is not a security boundary. Mandatory execution path: `Agent -> ToolCall -> Tool Registry -> Mission Policy -> ScopeGuard -> Approval Policy -> Sandbox -> Executor -> ToolResult -> Evidence`.
  - **Codex (Harness Amplification)**: Model intelligence is multiplied by environment quality. Invest heavily in Agent Legibility, structured feedback, and minimum sufficient context.
  - **Core Formula**: $\text{Verified Engineering Throughput} \approx \frac{\text{Accepted Engineering Work}}{\text{Time} \times \text{Compute} \times \text{Human Attention}}$.
  - **TaskEnvironment Abstraction**: Upgrade from pure `ContextPack` to `TaskEnvironment` (minimum sufficient engineering environment: intent, acceptance criteria, agent role, mutable scope, protected scope, relevant architecture/contracts/source/tests, failure evidence, governed tools, sandbox policy, execution environment, and stop conditions).
  - **Six Architecture Pillars**: Orchestrate, Contextualize, Contain, Observe, Verify, Recover.
  - **DO NOT BUILD**: Universal model router, free token rotation, agent marketplace, infinite swarm debate, auto-merge to main.
- **Consequences**: Unifies long-term vision; anchors P2-A through P2-D development; keeps agents bounded while maximizing engineering throughput.
