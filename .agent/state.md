# Agent Coordination State

## Protocol Baseline
- Required Version: 3.8.0
- Loaded Version: 3.8.0
- Canonical Source: `Universal_Coding_Agent_Development_Protocol.md` (v3.8.0)
- Protocol Identity Status: VERIFIED

## Coordination Mode
- Mode: STATIC_DOMAIN_OWNERSHIP
- Task Sharding: `.agent/tasks/<DOMAIN>/` (preferred)
- Realtime Working Coordination: External surface optional; `.agent/` is durable canonical execution authority.

## Project Frontier
- Current Phase: Phase 105 - Golden Path Hardening & CI Remediation (HEAD: 858dfdb1b982)
- Active Milestone: Golden Path Gap Remediation & CI Green Alignment (Tasks B, C, D merged; Task A frozen)
- Slice Status:
  - Slice 1 (CI Collection Fix + Pipeline Auth/Token Redaction + Worktree Branch Protection): COMPLETED & VERIFIED (22 tests PASS, 965 collected).
  - Slice 2 (Gaps 1, 2, 4, 6: Real Mutation Execution, Unified Policy Chokepoint, MissionStore Authority, Mandatory Review Gate): COMPLETED & VERIFIED (39 tests PASS, Exit Code 0).
- Current Frontier Ref: LAS-GOLDEN-PATH-REMEDIATION-858dfdb
- Coordination Checkpoint: Slice 1 & Slice 2 Fully Completed & Verified (全部驗收通過)
- Working Tree Policy: High-rigor source-grounded verification; zero fake execution evidence; authority unified to SQLite MissionStore.

## Shared Workspace Registry
- Entry Point: `AGENTS.md`
- Operating Contract: `.agent/agent.md`
- Ownership Matrix: `.agent/ownership.md`
- Decisions Log: `.agent/decisions.md`
- Versions Manifest: `.agent/versions.md`
- Test Policy: `.agent/test_policy.md`
- Relay Baseline: `handoff.md` + Git + `stage.md` (gitignored)
