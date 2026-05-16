# AGENTS.md

Read this file first.

<!-- ================================================================== -->
<!-- 🔒 以下為「通用規則區」(UNIVERSAL RULES)                            -->
<!--    這些規則適用於所有由此模板衍生的專案，AI 不應修改此區塊。            -->
<!--    When customizing this template for a new domain, DO NOT edit     -->
<!--    sections marked 🔒 UNIVERSAL.                                   -->
<!-- ================================================================== -->

---

## 🔒 Version Baseline Rules (UNIVERSAL)

- Always use the latest stable version that is appropriate for this repository when adding or upgrading dependencies.
- Always verify the matching syntax and current official usage before writing new code.
- Do not introduce code copied from outdated blog posts, deprecated examples, or older major-version APIs.
- If the repository is intentionally pinned to an older version, document the reason before extending that dependency.
- Prefer official documentation and package registries (PyPI, pub.dev, npm) as the source of truth for version and syntax decisions.

Practical rules:

- do not assume bare `python` on PATH is the intended project interpreter; confirm the actual interpreter path before using Python-version-specific syntax
- if package versions are upgraded, also upgrade the code syntax and migration patterns in the same change
- do not write Pydantic v1 syntax, legacy `typing` patterns, or outdated SDK usage into this repository

## 🔒 Editing Rules (UNIVERSAL)

- Prefer editing existing files over creating new files when reasonable.
- Do not create a new file or document unless it is clearly necessary; write into the best existing document whenever possible.
- Keep changes small, verifiable, and production-oriented.
- Do not silently change architecture decisions.
- Use full type hints, Pydantic validation, and explicit error handling.
- Keep secrets and API keys in environment variables or `config.yaml`, never hard-coded in source.
- When introducing or updating a package, check the current latest stable version first and avoid using outdated syntax or deprecated usage patterns.
- Avoid introducing new architecture assumptions without documenting them.

## 🔒 Security Rules (UNIVERSAL)

- Do not execute destructive operations without explicit user confirmation.
- Sanitize all external inputs before injecting into Jinja2 templates (SSTI prevention).
- Validate all file paths in skills to prevent directory traversal attacks.
- Enforce `max_iterations` in the agent loop to prevent infinite loops and token cost runaway.
- Do not hard-code secrets in source code.

## 🔒 Dual-Track Skill System (UNIVERSAL)

This project uses a hybrid "Brain & Hands" architecture:

- **Brain (knowledge_base/)**: `SKILL.md` files with YAML Frontmatter define the Agent's persona, expertise, and thinking framework. These are injected into the system prompt as context.
- **Hands (skills/)**: Python files with Pydantic BaseModel arguments define callable tools. The engine auto-discovers these via reflection.

Rules:

- Do not write tool schemas manually in `agent.jinja2`; let `core/engine.py` handle auto-discovery.
- Every Python skill MUST have a Pydantic BaseModel for arguments and a descriptive Docstring with `[觸發時機]` and `[限制條件]`.
- Every SKILL.md MUST have YAML Frontmatter with `name` and `description` fields.

When tasks match one of the loaded knowledge skills:

- inspect the relevant `SKILL.md` first
- follow the skill's workflow before writing code
- treat the knowledge_base directory as project tooling, not product code

## 🔒 Core Architecture Areas (UNIVERSAL)

Preserve and improve these modules within `agent_workspace/`:

1. `core/engine.py` — Dual-parser engine (Markdown knowledge + Python tool discovery)
2. `core/router.py` — Agent execution loop (state machine)
3. `agent.jinja2` — Dynamic system prompt template
4. `config.yaml` — Static environment parameters
5. `skills/` — Pydantic-based callable tools (hands/actions)
6. `knowledge_base/` — SKILL.md domain knowledge (brain/persona)
7. `memory/` — Cross-turn state persistence

Do not silently convert the project into:

- a web frontend application
- a standalone chatbot without tool-calling capability
- a monolithic single-file script

Keep service boundaries clear between engine, router, skills, and memory modules.

## 🔒 If Unsure (UNIVERSAL)

- Read this `AGENTS.md` for project rules.
- Read `agent_workspace/INSTRUCTIONS_FOR_AI.md` for universal rules and customization guide.
- Read `README.md` for project context.
- Choose the simplest implementation that preserves the dual-track architecture and modular boundaries.

<!-- ================================================================== -->
<!-- ✏️ 以下為「專案特定區」(PROJECT-SPECIFIC)                           -->
<!--    AI 在為新領域客製化時，應修改此區塊的內容。                         -->
<!--    When customizing for a new domain, EDIT the sections below.      -->
<!-- ================================================================== -->

---

## ✏️ Product (PROJECT-SPECIFIC)

- Build `FindAi Studio LLM Agent System` as a universal boilerplate template for domain-specific LLM Agents.
- Chinese product name: `防呆工作室`
- English product name: `FindAi Studio`
- Technical workspace name: `FindAi-Studio-LLM-Agent-System`

Use `防呆工作室 / FindAi Studio` for user-facing copy and documentation.

## ✏️ Architecture Stack (PROJECT-SPECIFIC)

This project is a Python-based LLM Agent framework.

- runtime: `Python`
- template engine: `Jinja2`
- data validation: `Pydantic`
- file watching: `watchdog`
- HTTP client: `httpx`
- YAML parsing: `pyyaml`

The main application code lives under `agent_workspace/`.

## ✏️ Version Pinning (PROJECT-SPECIFIC)

Version baseline for this repository:

- project Python target baseline: `3.14.3`
- latest stable Pydantic on PyPI: `2.12.5`
- latest stable Jinja2 on PyPI: `3.1.6`
- latest stable pyyaml on PyPI: `6.0.3`

## ✏️ Validation (PROJECT-SPECIFIC)

Before closing substantial code changes, prefer running:

```powershell
& "C:\Users\luke2\AppData\Local\Programs\Python\Python314\python.exe" -c "import sys; sys.path.insert(0, 'agent_workspace'); from core.engine import AgentEngine; engine = AgentEngine(workspace_path='agent_workspace'); print(engine.summary())"
```
