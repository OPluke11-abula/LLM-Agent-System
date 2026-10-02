# Project Test and Verification Policy

**Protocol Version**: 3.8.0
**Verification Philosophy**: Evidence before assertions always. No task may be marked complete without verifiable terminal output receipts.

---

## 1. Five Standard Verification Statuses

All verification claims must strictly map to one of these five objective status labels:

1. `PASS`: Test or check executed, exited with code 0, all assertions green.
2. `FAIL`: Test executed and failed; requires root-cause diagnosis.
3. `BLOCKED`: Preconditions missing (e.g., missing CLI binary, invalid credentials, environment unreachable).
4. `NOT_RUN`: Test suite has not been executed yet.
5. `UNVERIFIED`: Change made but lacks targeted test suite or host runtime execution.

---

## 2. Verification Ladder

Before declaring a change complete or preparing a PR, progress through the ladder:

1. **Ladder 1: Documentation & Governance Changes**
   - Command: `git diff --check`
   - Contract Validation: `python agent_workspace/tool_manifest.py validate`
   - Gate: 0 trailing whitespaces, 0 contract schema violations.

2. **Ladder 2: Backend Core & Runtime Logic Changes**
   - Focused Test: `pytest agent_workspace/tests/test_<focused>.py -v`
   - Security / Manifest Precheck: `python agent_workspace/core/precheck.py`
   - Gate: 100% green tests in focused area.

3. **Ladder 3: Presentation & Viewer Changes**
   - Linter / React Doctor: `npm run lint` or `npm run doctor` inside `viewer/`
   - UI build: `npm run build`
   - Gate: 0 errors, 0 warnings.

4. **Ladder 4: Integration & Milestone Verification**
   - Full script: `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify.ps1`
   - Gate: Full repository passes all tests and lint gates.

---

## 3. Mandatory Receipt Capture

Verification evidence must record:
- The exact command line invoked.
- Timestamp of execution.
- Terminal output snippet showing exit code and summary (e.g., `X passed in Y seconds`).
