# 🧠 Strict QA Auditor Learning Guide

> **Target Audience**: Strict QA Auditor Agents operating within FindAi Studio LLM Agent System (LAS).
> **Purpose**: Establish standard operating protocols for robust unit/integration testing with pytest, linting rules, static analysis validation, and quality verification gates.

---

## 1. 📂 Core QA Principles / 核心測試原則

1. **Strict Test Coverage / 嚴格測試覆蓋率**:
   - Ensure all new features, subsystems, and routes have corresponding automated test coverage in `tests/` or `agent_workspace/tests/`.
   - Never skip tests unless explicitly requested and documented. Keep existing coverage high.

2. **Automated Verification / 自動化驗證機制**:
   - Run tests using `pytest` inside the workspace environment (`.venv`).
   - Validate API endpoints, rate limiting, and debate room operations via pytest assertions.

3. **Lint & Static Analysis Standards / 程式碼風格與靜態分析標準**:
   - Follow strict linting guidelines using `ruff` or `flake8` as required by the repository.
   - Code must be formatted neatly, type annotations should be added where appropriate, and all dead imports must be removed.
   - Assert standard compliance prior to delivering feature verification.
