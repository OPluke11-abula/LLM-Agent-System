# Sakana Fugu AI Study for LAS

Checked on: 2026-06-27

Scope: public Sakana Fugu materials, related Sakana multi-agent orchestration papers, and the current LAS architecture surface.

## Executive Summary

Sakana Fugu AI is closest to LAS at the orchestration layer, not at the single-model chat layer. The useful lesson is not to copy a proprietary model, but to make the conductor layer a first-class, measurable, policy-driven runtime capability.

Fugu presents a multi-agent-system-as-a-model pattern: one API surface coordinates multiple specialist models and tools, selects roles dynamically, and optimizes for task outcome rather than only token completion. LAS already has many of the primitives needed to absorb this pattern:

- `AgentRouter` for routing and agent loops.
- Provider and account managers for model selection, cost, failover, and budget decisions.
- `DiscussionRoom` for multi-agent deliberation and consensus.
- Long-term memory and semantic memory for reusable lessons.
- PAP contracts, tool manifests, and verification gates for governance.
- React/Tauri and zero-build viewers for traceable control-plane UI.

The gap is that LAS routing is still mostly framework-driven and rule-driven. Fugu's strongest product idea is to treat orchestration decisions as observable, benchmarkable, and eventually learnable.

## Public Source Notes

Primary public sources used for this planning pass:

- Sakana Fugu official page: https://sakana.ai/fugu/
- Fugu technical report: https://arxiv.org/abs/2606.21228
- Conductor public paper page: https://ar5iv.labs.arxiv.org/html/2512.04388
- TRINITY public paper page: https://ar5iv.labs.arxiv.org/html/2512.04695

Important constraint: this pass did not confirm an official public Fugu source repository or open model weights. Treat Fugu internals as product and paper claims unless independently verified later.

## What Fugu Appears To Do Well

### 1. Conductor as a first-class runtime

Fugu's main advantage is the conductor layer. Instead of hard-coding a fixed chain, the orchestrator chooses how to decompose the task, which specialist agent or model should act, and how intermediate context should move between participants.

LAS implication: `AgentRouter` should emit a structured conductor plan before execution. The plan should be durable, inspectable, and replayable.

### 2. Specialist model pool

Fugu's product framing treats multiple models as an orchestra. That points to capability-based routing rather than vendor-based routing.

LAS implication: provider selection should be driven by capabilities such as coding, reasoning, browser use, long-context synthesis, security review, low-latency response, and low-cost fallback.

### 3. Tiered execution modes

Fugu/Fugu Ultra suggests an execution-mode pattern: a cheaper/faster path for routine tasks and a deeper multi-agent path for difficult tasks.

LAS implication: introduce `fast`, `pro`, and `ultra` modes:

- `fast`: single route, minimal memory, no debate.
- `pro`: planner plus worker plus verifier.
- `ultra`: multi-agent room, verifier loop, memory retrieval, and proof-of-consensus gates.

### 4. Verifier-driven stopping

The related TRINITY pattern is especially relevant: Thinker decomposes, Worker acts, Verifier decides whether the result is acceptable.

LAS implication: `DiscussionRoom` should support explicit Thinker, Worker, and Verifier roles. The verifier should be able to stop, continue, or escalate.

### 5. Benchmark-first agent quality

Fugu is marketed through agent benchmarks, not only unit tests. This matters because agent regressions often do not show up in compile checks.

LAS implication: add agent-level evals that replay tasks and score completion, cost, latency, tool safety, and human intervention.

### 6. Compliance-aware model controls

Fugu's public materials emphasize model/provider selection controls. This aligns with enterprise adoption needs.

LAS implication: execution plans should include allow/deny lists for providers, tool scopes, memory scopes, and external network permissions.

## LAS Component Mapping

| Fugu advantage | LAS surface today | Recommended LAS upgrade |
|---|---|---|
| Dynamic conductor | `agent_workspace/core/router.py` | Add `ConductorPlan` schema and route trace |
| Model orchestra | `providers.py`, `account_manager.py` | Add model capability registry and policy scoring |
| Deep multi-agent mode | `discussion_room.py` | Add Thinker/Worker/Verifier topology |
| Adaptive memory | `long_term_memory.py` | Store outcome memory and route lessons |
| Agent benchmarks | `scripts/verify.ps1`, pytest suite | Add `scripts/eval_agents.*` and golden tasks |
| Auditability | PAP manifests, audit ledger, viewer | Show conductor trace in UI |
| Safety gates | ProofOfConsensus, HITL, sandbox | Bind execution mode to policy and risk level |

## Recommended Architecture

### ConductorPlan

The conductor plan should be generated before execution and persisted with the run trace.

Required fields:

- `task_id`
- `task_summary`
- `execution_mode`: `fast | pro | ultra`
- `risk_level`: `low | medium | high`
- `subtasks`
- `roles`
- `candidate_models`
- `selected_models`
- `tool_allowlist`
- `memory_scope`
- `verification_strategy`
- `budget`
- `fallbacks`
- `decision_rationale`

### Role Topology

Start with four topologies:

- `single_worker`: direct execution for simple tasks.
- `planner_worker_verifier`: default pro mode.
- `parallel_specialists`: multiple workers compare approaches.
- `debate_consensus`: ultra mode with ProofOfConsensus.

### Outcome Memory

Each run should write a compact outcome record:

- task type
- mode
- selected model set
- tools used
- token cost
- wall time
- verifier result
- failures and recoveries
- human approval count
- reusable lesson

This turns memory from only "what happened" into "what worked".

## Implementation Plan

### Phase 0: Research and design foundation

Status: complete for the documentation baseline.

Deliverables:

- Fugu research note.
- ConductorPlan architecture note.
- `.agent/agent_tasks.md` Phase 61 task queue.

### Phase 1: No-behavior-change telemetry

Add structured conductor decision logging without changing runtime routing. This keeps the blast radius narrow and gives us data before policy changes.

Deliverables:

- `ConductorPlan` Pydantic model.
- Router trace generation.
- Unit tests for schema and serialization.

### Phase 2: Execution modes

Add `fast`, `pro`, and `ultra` mode selection while keeping current behavior as the default fallback.

Deliverables:

- Mode config.
- Safe defaults.
- Tests proving high-risk modes require explicit approval.

### Phase 3: Thinker/Worker/Verifier

Refactor `DiscussionRoom` orchestration so participant roles are explicit and verifier decisions are durable.

Deliverables:

- Role schema.
- Verifier stop/continue/escalate decisions.
- Consensus integration tests.

### Phase 4: Adaptive outcome memory

Persist route outcomes and use them as a retrieval input for future routing.

Deliverables:

- Outcome memory schema.
- Memory write path.
- Retrieval budget and ranking tests.

### Phase 5: Agent eval harness

Add reproducible agent-level evaluation tasks.

Deliverables:

- Golden task fixtures.
- Cost/latency/quality output report.
- CI-friendly smoke subset.

### Phase 6: Control-plane UX

Expose conductor traces in the viewer without overloading the dashboard.

Deliverables:

- Plan timeline.
- Model selection rationale.
- Memory hits.
- Verifier verdict.
- Cost and latency summary.

## First PR Recommendation

The first implementation PR should be intentionally small:

1. Add `ConductorPlan` schema.
2. Add route decision telemetry in `AgentRouter`.
3. Add serialization tests.
4. Do not change model selection behavior yet.

This gives LAS a Fugu-style conductor surface without risking routing regressions.

## Non-Goals

- Do not claim Fugu-equivalent benchmark performance.
- Do not assume private Fugu implementation details.
- Do not replace PAP contracts with opaque orchestration.
- Do not bypass existing HITL, sandbox, tenant, or consensus gates.
- Do not let `ultra` mode perform broader tool actions than the caller explicitly allowed.
