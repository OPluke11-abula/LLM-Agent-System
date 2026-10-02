---
tags:
  - post-mortem/5-whys
  - engineering/retrospective
  - lessons-learned
type: retrospective
layer: L6-Verification-Matrix-and-Receipts
sync_status: verified
---

# Engineering Retrospective & 5-Whys Post-Mortem (71)

> **Parent Index**: [[00 LLM-Agent-System Index]]
> **Gold Standard Reference**: `LingoLens_Thread_Closure_and_LAS_Agent_Learnings.md` Section V
> **Invariant**: "檢討永久留存，不粉飾太平" (Incident retrospectives are preserved permanently in Git)

---

## 1. 5-Whys Root Cause Analysis of Context & Hallucination Failures

In complex multi-agent development sessions, agents often suffer from "Secondhand Summary Complacency (二手摘要滿足感)":

- **Why 1**: Why did previous agent sessions introduce regressions or hallucinated features?
  - *Answer*: The agent did not inspect underlying primary source code, relying instead on commit messages or high-level markdown notes.
- **Why 2**: Why did the agent skip primary sources?
  - *Answer*: The agent sought immediate completion velocity and mistook secondary summaries for definitive truth.
- **Why 3**: Why was there no guardrail?
  - *Answer*: The agent treated protocols as advisory text rather than strict gatekeeper invariants.
- **Why 4**: Why was there boundary drift between frontend and backend?
  - *Answer*: Roles were generic titles ("Developer") without concrete physical tool bindings or path-level write prohibitions.
- **Why 5 (Root Cause)**:
  - **Lack of Engineering Self-Discipline & Blurred Architectural Boundaries**: A failure to enforce "Code and live tests are the sole truth" and "Grounded tools define agent capability".

---

## 2. Four Supreme Engineering Invariants (四大最高鐵律)

1. **【Invariant 1: 調研先行，嚴禁純讀摘要】 (Mandatory Bottom-Up Research)**
   - Whenever performing architecture design, refactoring, or bug fixing, mandatory inspection of primary source code and schemas is required. Exact file paths and line numbers must be cited.
2. **【Invariant 2: 以 PO 戰略願景為唯一北極星】 (PO Vision as North Star)**
   - Strictly follow Luke's architectural guidance and product roadmap. Eliminate speculative dead code or unrequested scope expansions.
3. **【Invariant 3: 無證據不宣告完成】 (Evidence Before Assertions)**
   - Only five objective verification statuses are permitted: `PASS`, `FAIL`, `BLOCKED`, `NOT_RUN`, `UNVERIFIED`. A task without green test logs is unverified.
4. **【Invariant 4: 檢討永久留存，不粉飾太平】 (Permanent Incident Traceability)**
   - Engineering errors, retrospectives, and 5-Whys analyses remain permanently tracked in Git to ensure institutional memory across all agent generations.
