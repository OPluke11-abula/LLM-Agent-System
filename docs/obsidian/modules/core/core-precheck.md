---
tags:
  - architecture/leaf
  - security/precheck
  - quality/invariants
  - layer/l6
type: module_leaf
layer: L6-Verification-Matrix-and-Receipts
module: agent_workspace.core.precheck
file_path: agent_workspace/core/precheck.py
sync_status: verified
---

# Module: SkillsPrechecker (Preflight Verification & Anti-Corruption Scanner)

## 1. Three-Line Architectural Annotation
- **Responsibility**: Pre-execution verification engine enforcing protocol v3.8.0 operational invariants, CLI dependency presence, and credentials hygiene.
- **Invariant**: Verifies the Anti-Summary Invariant (調研先行), Stop-and-Wait Architecture Gate, and the Seven Anti-Corruption Principles before workflow dispatch.
- **Data Flow**: Scans local filesystem, AST trees, git status, and environment variables, emitting structured pass/fail receipts to [[core-audit-ledger]].

---

## 2. Source Code & Symbol Mapping

**Source Location**: [precheck.py](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/precheck.py) (148 lines)

### Symbol Table

| Symbol | Kind | Line Range | Description |
| :--- | :--- | :--- | :--- |
| SkillsPrechecker | class | L10-L148 | Core preflight verifier executing static and environment checks. |
| check_cli_dependencies | def | L14-L20 | Verifies required CLI executables (git, python,
pm) exist on system PATH. |
| check_credentials | def | L22-L27 | Validates required provider API keys are present in environment without leaking secrets. |
|
un_precheck | def | L29-L90 | Comprehensive runner validating tool manifests, imports, and system requirements. |
| check_anti_summary_preflight | def | L92-L118 | Enforces that research tasks verify concrete source files rather than secondary summaries. |
| check_stop_and_wait_gate | def | L120-L133 | Validates human confirmation before modifying files when required by protocol v3.8.0. |
| check_seven_anti_corruption | def | L136-L148 | Static code analysis verifying zero dead code, no swallowed exceptions, and typed failures. |

---

## 3. Seven Anti-Corruption Static Audit Matrix

| Principle | Verification Mechanism | Failure Handling |
| :--- | :--- | :--- |
| 1. Zero Dead Code | AST scan for unused imports & functions | Halts PR merge |
| 2. Extreme Single Responsibility | Directory boundary compliance check | Rejects commit |
| 3. Concurrency & Race Elimination | Timestamp monotonic ordering check | Re-orders queue |
| 4. Typed Failures Only | AST scan for bare except: or pass | Flags critical lint |
| 5. Specification-First | Schema validation in spec/ before code | Blocks workflow |
| 6. Idempotence & Side-Effect Safety | Rollback replay verification in sandbox | Reverts transaction |
| 7. Configuration over Hardcoding | Regex scan for hardcoded credentials / IP | Fails precheck |

---

## 4. Operational Invariants & Anti-Corruption Guardrails
1. **Secret Redaction**: Credential checks must NEVER print API key values or token fragments to logs or stdout.
2. **Mandatory Exit Code 0**: Preflight failure immediately aborts task dispatch with a descriptive, typed diagnostic.

---

## 5. Verification & Test Evidence
- **Test Suites**:
  - [	est_precheck.py](file:///d:/GitHub/LLM-Agent-System/agent_workspace/tests/test_precheck.py)
  - [	est_license_audit.py](file:///d:/GitHub/LLM-Agent-System/agent_workspace/tests/test_license_audit.py)
- **Execution Receipt**: Bytecode validated via compileall exit code 0.

---

## 6. Topological Linkage
- **Upstream Layer**: [[L6-Verification-Matrix-and-Receipts]]
- **Protocol Contract**: [[70 Multi-Agent Protocol v3.8.0 & 10 Grounded Roles Matrix]]
- **Collaborating Modules**:
  - [[core-policy-gate]]
  - [[core-audit-ledger]]
