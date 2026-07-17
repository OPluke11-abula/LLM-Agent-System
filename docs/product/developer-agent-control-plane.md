# Developer Agent Control Plane

This document is the authoritative Developer Beta product contract for LAS.
It defines the product boundary and the P1 Mission and contract vocabulary;
it does not claim that the later runtime, API, or Viewer batches are complete.

## Product identity

- **Product category:** Developer Agent Control Plane
- **Deployment posture:** local-first
- **Primary user:** AI-native solo developers and small technical teams
- **Core principle:** AI output is a proposal; the developer remains accountable.
- **Product pillars:** Observe, Control, Verify

The control plane makes proposed work, authorization, execution evidence, and
delivery state visible. A Mission is not permission for invisible or unlimited
autonomy.

## Developer Beta Golden Path

The official flow is:

1. **System Check**
2. **Connect Repository**
3. **Define Mission**
4. **Review Plan**
5. **Execute and Observe**
6. **Resolve Decisions and Scope Expansion**
7. **Verify Evidence**
8. **Review Draft PR**
9. **Human Decision**

P1 defines the contract vocabulary and Mission transitions used by this flow.
Repository connection, execution, Draft PR creation, and Viewer presentation
remain later implementation work.

## Core guarantees

Developer Beta preserves these guarantees at its contract boundary:

- no invisible Agent action
- no unbounded execution
- no unsupported completion claim
- no scope expansion without approval
- no auto-merge by default
- every PASS claim links to evidence
- cancellation and pause remain explicit
- human merge authority is always preserved

## Product boundaries

Developer Beta explicitly excludes:

- no-code application generation for non-developers
- automatic production merge
- unrestricted autonomous execution
- multi-repository missions
- large-enterprise IAM
- public SaaS billing product
- arbitrary distributed swarm administration
- general-purpose consumer chatbot behavior

The supported Developer Beta scope is Windows 10 and 11, one developer, one
repository, a local workspace, GitHub repository delivery, Python, TypeScript,
or Python plus React, Draft PR output, and either local Ollama or one configured
hosted provider.

## Source of truth

Python Pydantic v2 models under `agent_workspace/core` are the runtime source of
truth for the P1 contracts. The canonical JSON representation is deterministic:
JSON keys are sorted, separators are stable, enum values are serialized as
their lowercase contract strings, and every model carries `schema_version` when
it is a versioned aggregate or plan.

The P1 schema version is `1.0`. Contracts reject unknown fields. Repository
paths are repository-relative, credentials in remote URLs are rejected, and a
profile's machine-local `local_path` is excluded from serialized output. No
secret-bearing field is part of the canonical model surface. Existing API and
workflow models remain compatibility boundaries; P1 does not replace them.

TypeScript synchronization is deferred until a Viewer contract is needed. A
future generated or validated TypeScript representation must consume this
Python source and verify enum values and required fields rather than introduce
a manually divergent contract. P1 changes no Viewer types.

## Mission state machine

### States

Primary states are `draft`, `planning`, `awaiting_approval`, `running`,
`needs_decision`, `verifying`, `review_ready`, `draft_pr_created`, and `closed`.
Exceptional states are `paused`, `cancelled`, `failed`, `budget_exhausted`,
`scope_blocked`, and `ci_failed`.

Terminal states are `closed`, `cancelled`, `failed`, and `budget_exhausted`.
Cancellation is terminal; continuing cancelled work requires a new Mission.
The recoverable states are the active planning, approval, execution, decision,
verification, review, scope-blocked, and CI-failed states. A paused Mission
records its prior recoverable state and can resume only to that state.

### Allowed transitions

| Current state | Event | Next state | Guard |
| --- | --- | --- | --- |
| `draft` | `start_planning` | `planning` | none |
| `planning` | `submit_plan` | `awaiting_approval` | none |
| `awaiting_approval` | `approve_plan` | `running` | approved plan gate |
| `awaiting_approval` | `reject_plan` | `planning` | none |
| `running` | `begin_verification` | `verifying` | none |
| `running` | `request_scope_expansion` | `needs_decision` | none |
| `running` or `needs_decision` | `block_scope` | `scope_blocked` | none |
| `needs_decision` or `scope_blocked` | `approve_scope` | `running` | approved scope request |
| `needs_decision` or `scope_blocked` | `reject_scope` | `planning` | none |
| `verifying` | `complete_verification` | `review_ready` | all gates passed or not applicable |
| `verifying` | `fail_ci` | `ci_failed` | none |
| `ci_failed` | `retry_verification` | `verifying` | none |
| `review_ready` | `create_draft_pr` | `draft_pr_created` | Draft PR permission and approval |
| `review_ready` or `draft_pr_created` | `close` | `closed` | none |
| recoverable state | `pause` | `paused` | none |
| recoverable state | `cancel` | `cancelled` | none |
| recoverable state | `fail` | `failed` | none |
| `planning`, `running`, or `verifying` | `exhaust_budget` | `budget_exhausted` | none |
| `paused` | `resume` | recorded prior state | prior state exists |

There is no `merged` state or merge event. A Draft PR delivery records
mergeability and the human decision state, but LAS never treats merge as an
automatic Mission transition.

### Invariants and failure behavior

The central `MissionStateMachine` enforces these invariants:

1. A Mission cannot enter `running` before plan approval.
2. A Mission cannot enter `review_ready` without completed verification gates.
3. A Mission cannot enter `draft_pr_created` without explicit Draft PR
   permission.
4. No Mission state represents automatic merge.
5. Cancellation is terminal unless an explicit new Mission is created.
6. Scope-blocked work cannot continue before a developer decision.
7. Budget exhaustion cannot silently return to `running`.
8. State transitions are deterministic and auditable.
9. Replaying the same transition request returns the recorded audit and does not
   append a second transition.
10. Reusing an idempotency key for a different event, or requesting an event
    that is not legal in the current state, fails closed.

Each successful transition appends a typed audit record containing the actor,
event, source and target states, timestamp, and idempotency key. Transition
guards raise a typed error code for missing plan approval, verification
evidence, Draft PR permission or approval, scope decision, terminal state, or
idempotency conflict.

## Canonical P1 contracts

The implementation is split by responsibility:

- `agent_workspace/core/product_contracts.py`: strict immutable base model,
  stable enums, identifiers, `RepositoryProfile`, `ScopePolicy`, and
  `MissionPolicy`.
- `agent_workspace/core/mission_contracts.py`: `AgentAssignment`, `PlanTask`,
  `ExecutionPlan`, `ApprovalRequest`, `ApprovalDecision`, `ApprovalGate`,
  `ScopeExpansionRequest`, `EvidenceRecord`, `VerificationGate`,
  `MissionCostSummary`, `DraftPullRequestDelivery`, and deterministic JSON.
- `agent_workspace/core/mission_model.py`: `MissionState`, `MissionEvent`,
  transition errors and audit records, and the immutable `Mission` aggregate.
- `agent_workspace/core/mission_state_machine.py`: the central transition map,
  guards, terminal behavior, pause/resume behavior, and idempotency behavior.

`VerificationGateName` covers requirement, scope, architecture, tests, security,
quality, CI, and cost. A passed gate requires at least one evidence reference.
Evidence output is bounded and linked to requirements and tasks rather than
treated as an unbounded log payload.

This P1 boundary does not implement GitHub connection, real Mission execution,
plan-generation provider calls, Agent scheduling, pause/cancel runtime
integration, scope-expansion UI, full Viewer pages, Draft PR creation, durable
Mission persistence, database migrations, or installer changes.
