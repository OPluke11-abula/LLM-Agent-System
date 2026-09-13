# Project Agent Entry Point (AGENTS.md)

**Canonical Coordination Workspace**: `.agent/`
**Required Protocol Version**: `3.8.0` (`Universal_Coding_Agent_Development_Protocol.md`)
**Domain Authority**: Luke (PO / Domain Owner)

Use this file as the thin, authoritative entry point for Codex, Antigravity, and all collaborating coding agents.

---

## 1. Required Bootstrap Sequence

For every NEW agent thread or session that will read or write repository state:

1. **Protocol Identity Verification**:
   - Check `.agent/state.md` → `Protocol Baseline`. Verify required version is `3.8.0`.
   - If version is mismatched or ambiguous, **STOP** and report `PROTOCOL_MISMATCH`.
2. **Read Operating Contracts**:
   - Read [`AGENT.md`](AGENT.md) for local safety rules, loop limits, and work-completion steps.
   - Read [`.agent/agent.md`](.agent/agent.md) for current operating contracts and queue discipline.
   - Read [`.agent/ownership.md`](.agent/ownership.md) to identify your assigned mutable boundary. **Modifying files outside your assigned boundary is strictly forbidden.**
3. **Optional Context Preflight**:
   - For tasks requiring wiki context, run:
     ```powershell
     powershell -NoProfile -ExecutionPolicy Bypass -File .\.agent\knowledge_base\tools\start_agent_preflight.ps1 -Query "<task focus>" -Top 5
     ```
   - Treat context packs as orientation only; primary repository source files remain the sole truth.

---

## 2. Core Operational Invariants

### 0.1 Anti-Summary Invariant (調研先行)
Agents are strictly prohibited from generating architectural conclusions, refactoring proposals, or code modifications based solely on secondary summaries or handoff documents. You MUST inspect concrete primary source files and cite exact line numbers.

### 0.2 Stop-and-Wait Architecture Gate
After requirement analysis, submit a structured implementation plan detailing:
- Target files to modify, create, or delete.
- Structural diff and dependency impact.
- Edge cases and test strategy.
**You MUST STOP and wait for explicit Human confirmation before calling file-editing tools.**

### 0.3 Seven Universal Anti-Corruption Principles
1. **Zero Dead Code**: Purge unused functions and dead imports immediately.
2. **Extreme Single Responsibility**: UI does not touch SQL/IPC; Domain remains framework-agnostic.
3. **Concurrency & Race Elimination**: Enforce `latest-request-wins` on asynchronous operations.
4. **Typed Failures Only**: Never swallow exceptions with empty catches; use typed error models.
5. **Specification-First**: Domain contracts and unit tests lead UI implementation.
6. **Idempotence & Side-Effect Safety**: Cancellation and duplicate triggers must be side-effect free.
7. **Configuration over Hardcoding**: Zero magic numbers or hardcoded timeouts.

---

## 3. Three-Tier Cognitive Relay

- **Tier 1 (`stage.md`)**: Local real-time scratchpad for in-flight thoughts and draft code. Must be excluded by `.gitignore`. Never commit to Git.
- **Tier 2 (`handoff.md` + Git)**: Team cognitive relay for verified facts, PR status, and 3-line summaries. Updated **only** after automated tests pass 100%.
- **Tier 3 (`docs/obsidian/` + Vault)**: Full knowledge topology. Annotate module leaf notes with 3-line concise English annotations upon PR merge.

---

## 4. External-State Guardrails

- Do not commit, push, install dependencies, deploy, or change external services without explicit human instruction.
- Redact credentials: never print raw tokens, API keys, or `.env` secrets in terminal output or logs.
- Evidence before completion: only declare tasks complete after verifying test exit code 0 (`PASS`).
