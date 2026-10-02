# ConductorPlan Architecture Draft

Status: draft

Related research: `docs/research/fugu-ai-study.md`

## Goal

Add a Fugu-style conductor surface to LAS while preserving LAS principles:

- Separation between runtime core, adapters, presentation, and persistence.
- PAP contract parity for skills and tools.
- Clean handoff state in `.agent/`.
- Bilingual documentation when user-facing capabilities change.
- Verified changes before claiming completion.

## Design Principle

The conductor should make routing decisions explicit before work starts. It should not hide orchestration inside prompts or ad hoc control flow.

## Proposed Data Model

```python
class ConductorPlan(BaseModel):
    task_id: str
    task_summary: str
    execution_mode: Literal["fast", "pro", "ultra"]
    risk_level: Literal["low", "medium", "high"]
    topology: Literal[
        "single_worker",
        "planner_worker_verifier",
        "parallel_specialists",
        "debate_consensus",
    ]
    subtasks: list[ConductorSubtask]
    roles: list[ConductorRole]
    candidate_models: list[ModelCandidate]
    selected_models: list[SelectedModel]
    tool_allowlist: list[str]
    memory_scope: MemoryScope
    verification_strategy: VerificationStrategy
    budget: ExecutionBudget
    fallbacks: list[FallbackRule]
    routing_memory_hints: list[RouteOutcomeHint]
    decision_rationale: str
```

## Placement

Recommended module placement:

- `agent_workspace/core/conductor.py`: schema and pure planning helpers.
- `agent_workspace/core/router.py`: plan creation and execution handoff.
- `agent_workspace/core/discussion_room.py`: topology execution for pro/ultra modes.
- `agent_workspace/long_term_memory.py`: outcome memory storage and retrieval.
- `agent_workspace/tool_manifest.py`: future tool capability validation if plan scopes tools.

Avoid placing HTTP, WebSocket, React, or serialization-only concerns inside `core/conductor.py`.

## Execution Modes

### fast

Use when the task is simple, low-risk, or latency-sensitive.

- One worker.
- Minimal memory retrieval.
- No debate.
- Verifier optional.

### pro

Use for normal engineering tasks.

- Planner/worker/verifier topology.
- Bounded memory retrieval.
- Tool allowlist enforced.
- Verifier produces a durable verdict.

### ultra

Use for difficult or high-impact tasks.

- Multi-agent topology.
- Explicit verifier loop.
- ProofOfConsensus for sensitive decisions.
- Budget and approval gates are mandatory.

## Verification Strategy

Every conductor execution should report:

- whether the plan was followed
- which tools were used
- which model/provider handled each role
- verifier decision
- tests or checks run
- unresolved risks

Adaptive routing starts in audit-only mode: recent same-task-type `routing_outcome` records are attached to the plan as bounded `routing_memory_hints`. They must not change provider selection until scoring policy and tests explicitly enable that behavior.

The first implementation should only log plans. Behavior changes should happen after schema and telemetry are stable.

## Safety Rules

- High-risk plans must fail closed when required approvals are missing.
- Tool access must be the intersection of PAP-declared capabilities and caller allowlist.
- Provider fallbacks must respect tenant, privacy, cost, and model opt-out policy.
- Memory retrieval must be scoped to the current tenant/session unless explicitly authorized.
- Ultra mode must not broaden file, network, or external API access.

## Minimum Test Plan

- Schema accepts valid `fast`, `pro`, and `ultra` plans.
- Schema rejects unknown modes and topologies.
- Router can emit a plan without changing the selected provider.
- Tool allowlist cannot include undeclared tools.
- High-risk ultra plan requires approval metadata.
- Plans serialize to stable JSON for audit logs and UI replay.
