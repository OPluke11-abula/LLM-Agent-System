---
tags:
  - architecture/leaf
  - skills/inventory
  - tools/manifest
  - layer/l2
type: module_leaf
layer: L2-Protocol-and-Contract-Gateways
module: skills
file_path: agent_workspace/core/skill_loader.py
sync_status: verified
---

# Module: SkillsInventoryAndTools (Host Skills & Sandboxed Tool Catalog)

## 1. Three-Line Architectural Annotation
- **Responsibility**: Catalogs and dynamic-binds all host skills, custom Markdown SKILL.md specifications, and sandboxed primitive tools available to the 10 Grounded Swarm Roles.
- **Invariant**: Tools executing file modifications or shell commands must execute within `SandboxGuard` and enforce role mutable boundary constraints.
- **Data Flow**: Parsed by `SkillLoader` from YAML frontmatter and Markdown definitions, compiled into JSON tool schemas, and registered with `AgentRouter`.

---

## 2. Host Skills & Tool Catalog Matrix

| Tool / Skill Identifier | Scope / Category | Mutable Boundary | Assigned Role(s) |
| :--- | :--- | :--- | :--- |
| `to-prd` | Requirements & Specs | `docs/prd/**` | ProductOwner |
| `to-issues` | Task Breakdown | `.agent/**` | ProductOwner |
| `design-markdown` | System Architecture | `docs/obsidian/**` | Architect |
| `tdd` | Test-First Development | `agent_workspace/core/**` | BackendDev |
| `test-driven-development` | Unit / Integration Tests | `agent_workspace/core/**` | BackendDev |
| `aesthetic-design-system` | UI/UX & Design Tokens | `viewer/src/**` | FrontendDev |
| `motion-design` | CSS Transitions & Animations| `viewer/src/**` | FrontendDev |
| `setup-pre-commit` | Git Hooks & CI Pipeline | `scripts/**, .github/**` | DevOpsEngineer |
| `verification-before-comp` | Verification Matrix | `agent_workspace/tests/**` | QAEngineer |
| `security-audit` | Vulnerability Scanning | Read-only | SecurityAuditor |
| `pentest` | Penetration & Fuzz Testing | Security sandbox | SecurityAuditor |
| `doc-coauthoring` | Documentation | `docs/**, *.md` | DocumentationWriter |
| `unslop` | Anti-AI Slop Humanizer | Memory & Docs | DocumentationWriter |
| `code-review` | Standards & Spec Review | Read-only findings | CodeReviewer |
| `open-code-review` | AI Pull Request Review | Read-only findings | CodeReviewer |
| `goal-sloc` | SLOC Reduction Refactor | Target refactor modules | RefactoringSpecialist |
| `read_file` | System Primitive | Read-only | All Roles |
| `write_file` | System Primitive | Role Boundary Only | Mutating Roles |
| `run_command` | System Primitive (Bash/PS) | High-Risk Sandbox | DevOpsEngineer, BackendDev |
| `list_directory` | System Primitive | Read-only | All Roles |
| `grep_search` | System Primitive | Read-only | All Roles |
| `manage_task` | System Primitive | Task Registry | All Roles |
| `ask_question` | Interactive Primitive | User TTY | ProductOwner, Architect |
| `schedule` | Timer Primitive | Background Queue | DevOpsEngineer |
| `call_mcp_tool` | MCP Protocol Bridge | Registered MCP servers | Specialized Roles |
| `generative_spec_generator` | Multi-Modal Prompt Specs | `agent_workspace/skills/**` | ProductOwner, Architect, FrontendDev |
| `generative-spec-pipeline` | Spec-Driven Generative Skill | `skills/**` | ProductOwner, Architect, FrontendDev |

---

## 3. Operational Invariants & Anti-Corruption Guardrails
1. **Dynamic AST Safety Verification**: Any dynamically generated skill code must pass AST validation in `validate_generated_skill` prior to import.
2. **Explicit Role Whitelist**: A role attempting to invoke a tool outside its allowed skill bindings is blocked by `UnifiedPolicyGate`.

---

## 4. Verification & Test Evidence
- **Test Suites**:
  - [`test_skill_loader.py`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/tests/test_skill_loader.py)
  - [`test_skill_discovery.py`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/tests/test_skill_discovery.py)
- **Execution Receipt**: Bytecode validated via `compileall` exit code 0.

---

## 5. Topological Linkage
- **Upstream Layer**: [[L2-Protocol-and-Contract-Gateways]]
- **Roles Matrix**: [[70 Multi-Agent Protocol v3.8.0 & 10 Grounded Roles Matrix]]
- **Collaborating Modules**:
  - [[core-router]]
  - [[core-agent-crew]]
  - [[core-sandbox]]
  - [[spec-driven-generative-engine]]
