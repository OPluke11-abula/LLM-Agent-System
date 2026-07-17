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

The machine-readable Mission API schema is generated from these Python contracts
at `schemas/mission_api.json`. A drift test compares the checked-in artifact to
fresh output, so a future Viewer representation must consume this seam rather
than introduce a manually divergent contract. P1 changes no Viewer types.

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
  `MissionBudgetPolicy`, `MissionUsageSummary`, `DraftPullRequestDelivery`,
  and deterministic JSON.
- `agent_workspace/core/mission_model.py`: `MissionState`, `MissionEvent`,
  transition errors and audit records, and the immutable `Mission` aggregate.
- `agent_workspace/core/mission_state_machine.py`: the central transition map,
  guards, terminal behavior, pause/resume behavior, and idempotency behavior.

`VerificationGateName` covers requirement, scope, architecture, tests, security,
quality, CI, and cost. Completion requires every required gate to be either
`passed` or `not_applicable`; a passed gate requires evidence. Evidence output is
bounded and linked to requirements and tasks rather than treated as an unbounded
log payload. Approval subjects bind plan, scope, and Draft PR decisions to the
exact revision or request being approved.

## Mission persistence and API seam

The Mission aggregate is durably stored in SQLite at `memory/missions.db`. The
store uses optimistic revision checks and an atomic transaction for each state
transition, including its transition audit receipt and idempotency replay
record. Listing is bounded and deterministic. Store recovery validates the
versioned serialized aggregate and fails closed on corruption.

The protected `/v1/missions` API exposes create, get, bounded list, transition
history, plan attachment, approval recording, evidence recording, and
verification-gate recording. Authentication supplies the actor identity; a
request-body actor cannot override it. These routes persist control-plane state
only. They do not execute providers, mutate Git, create pull requests, or
perform merge operations.

This P1 boundary does not implement GitHub connection, real Mission execution,
plan-generation provider calls, Agent scheduling, pause/cancel runtime
integration, scope-expansion UI, full Viewer pages, Draft PR creation,
database migrations, or installer changes.
