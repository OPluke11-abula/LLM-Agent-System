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
- Active Milestone: Phase 105 - Task A (Tauri 2 Ambient Companion & 1-Click HITL) + Tasks B, C, D Completed & Verified
- Slice Status:
  - Task B (Protocol Repair Loop): COMPLETED & VERIFIED.
  - Task C (Delegation Packet): COMPLETED & VERIFIED.
  - Task D (Responses API Gateway): COMPLETED & VERIFIED.
  - Slices 1 & 2 (Golden Path Hardening Gaps 1~6): COMPLETED & VERIFIED (PR #16 merged).
  - Task A (Tauri 2 Ambient Companion & 1-Click HITL Approval): COMPLETED & VERIFIED (companion-window, useAmbientCompanion, AmbientCompanion UI, verify:companion green).
  - Deep Optimization Pack (Pipeline 9-Stage Stepper Sync + Gate Approved Receipt + Responses API Structured Tools + Secret Redaction at Rest): COMPLETED & VERIFIED.
- Current Frontier Ref: LAS-PHASE-105-DEEP-OPTIMIZATION-COMPLETE
- Coordination Checkpoint: Phase 105 核心與深度優化全數驗證通過 (100% Green CI & Clean Build)
- Working Tree Policy: High-rigor source-grounded verification; zero fake execution evidence; authority unified to SQLite MissionStore.

## Shared Workspace Registry
- Entry Point: `AGENTS.md`
- Operating Contract: `.agent/agent.md`
- Ownership Matrix: `.agent/ownership.md`
- Decisions Log: `.agent/decisions.md`
- Versions Manifest: `.agent/versions.md`
- Test Policy: `.agent/test_policy.md`
- Relay Baseline: `handoff.md` + Git + `stage.md` (gitignored)
