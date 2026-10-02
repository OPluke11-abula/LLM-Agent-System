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
- Current Phase: Phase 109 - Dual-Track Release Pipeline & Desktop Packaging (COMPLETED & CERTIFIED)
- Active Milestone: Milestone T-036 (Production Deployment & Swarm Mesh Drill Certified)
- Release Version: `v0.6.0`
- Slice Status:
  - Phase 107 (Multimodal Swarm Mesh & 16-Node P2P Stress Drill): COMPLETED & CERTIFIED (320 ops, 0 errors, 100% Merkle attestation).
  - Phase 108 (Docker Multi-Arch Buildx & GHCR Registry Pipeline): COMPLETED & CERTIFIED (.github/workflows/docker-publish.yml, .env.production.example).
  - Phase 109 (Dual-Track Release Pipeline & Desktop Packaging): COMPLETED & CERTIFIED (.github/workflows/release.yml, verify_release_readiness.py).
- Current Frontier Ref: LAS-PHASE-109-MILESTONE-T036-CLOSED
- Coordination Checkpoint: Swarm Multimodal Mesh, Docker GHCR Publishing & Dual-Track Release Certified (70/70 Tests PASS, 0 React Doctor warnings, Vite build clean).
- Working Tree Policy: High-rigor source-grounded verification; zero fake execution evidence; authority unified to SQLite MissionStore.


## Shared Workspace Registry
- Entry Point: `AGENTS.md`
- Operating Contract: `.agent/agent.md`
- Ownership Matrix: `.agent/ownership.md`
- Decisions Log: `.agent/decisions.md`
- Versions Manifest: `.agent/versions.md`
- Test Policy: `.agent/test_policy.md`
- Relay Baseline: `handoff.md` + Git + `stage.md` (gitignored)
