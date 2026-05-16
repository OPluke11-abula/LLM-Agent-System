# INSTRUCTIONS FOR AI AGENTS

Hello AI Assistant!

You are looking at a **Universal LLM Agent Template**. Your user has cloned this repository and wants YOU to transform it into a specialized Agent for a specific domain.

---

## 🔒 Universal Hard Rules (DO NOT MODIFY)

These rules apply to ALL projects derived from this template. You MUST follow them regardless of domain.

### Version Baseline Rules

- Always use the latest stable version that is appropriate for this repository when adding or upgrading dependencies.
- Always verify the matching syntax and current official usage before writing new code.
- Do not introduce code copied from outdated blog posts, deprecated examples, or older major-version APIs.
- If the repository is intentionally pinned to an older version, document the reason before extending that dependency.
- Prefer official documentation and package registries (PyPI, pub.dev, npm) as the source of truth for version and syntax decisions.
- Do not assume bare `python` on PATH is the intended project interpreter; confirm the actual interpreter path before using Python-version-specific syntax.
- If package versions are upgraded, also upgrade the code syntax and migration patterns in the same change.
- Do not write Pydantic v1 syntax, legacy `typing` patterns, or outdated SDK usage into this repository.

### Editing Rules

- Prefer editing existing files over creating new files when reasonable.
- Do not create a new file or document unless it is clearly necessary; write into the best existing document whenever possible.
- Keep changes small, verifiable, and production-oriented.
- Do not silently change architecture decisions.
- Use full type hints, Pydantic validation, and explicit error handling.
- Keep secrets and API keys in environment variables or `config.yaml`, never hard-coded in source.
- When introducing or updating a package, check the current latest stable version first and avoid using outdated syntax or deprecated usage patterns.
- Avoid introducing new architecture assumptions without documenting them.
- Keep service boundaries clear between engine, router, skills, and memory modules.

### Security Rules

- Do not execute destructive operations without explicit user confirmation.
- Sanitize all external inputs before injecting into Jinja2 templates (SSTI prevention).
- Validate all file paths in skills to prevent directory traversal attacks.
- Enforce `max_iterations` in the agent loop to prevent infinite loops and token cost runaway.
- Do not hard-code secrets in source code.

### Dual-Track Skill System

This project uses a hybrid "Brain & Hands" architecture:

- **Brain (knowledge_base/)**: `SKILL.md` files with YAML Frontmatter define the Agent's persona, expertise, and thinking framework. These are injected into the system prompt as context.
- **Hands (skills/)**: Python files with Pydantic BaseModel arguments define callable tools. The engine auto-discovers these via reflection.

Rules:

- Do not write tool schemas manually in `agent.jinja2`; let `core/engine.py` handle auto-discovery.
- Every Python skill MUST have a Pydantic BaseModel for arguments and a descriptive Docstring with `[觸發時機]` and `[限制條件]`.
- Every SKILL.md MUST have YAML Frontmatter with `name` and `description` fields.
- When tasks match one of the loaded knowledge skills, inspect the relevant `SKILL.md` first and follow the skill's workflow before writing code.

### Core Architecture

Preserve and improve these modules:

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

---

## ✏️ Customization Guide (EDIT WHEN ADAPTING TO A NEW DOMAIN)

When the user gives you a new domain (e.g., "Make a Customer Support Agent"), follow these steps:

### 1. Update the parent `AGENTS.md`
- Update the `✏️ PROJECT-SPECIFIC` sections with new product naming, tech stack, and version pinning.

### 2. Update Configuration (`config.yaml`)
- Add any required API keys or environment variables needed for the new domain.

### 3. Rewrite the System Prompt (`agent.jinja2`)
- Modify `agent.jinja2` to define the Agent's Persona, Role, and SOP (Standard Operating Procedure).
- Use `{{ variables }}` for context that `core/engine.py` will inject at runtime.

### 4. Add Domain Knowledge (`knowledge_base/`)
- Create subdirectories with `SKILL.md` files for the Agent's expertise areas.
- Follow YAML Frontmatter format: `name` and `description` fields.

### 5. Create Domain-Specific Skills (`skills/*.py`)
- Delete `skills/example_skill_template.py`.
- Create new Python files in `skills/` for the tools the Agent needs.
- **CRITICAL**: Every skill MUST follow this pattern:
  1. Define a `pydantic.BaseModel` for arguments.
  2. Write a clear Docstring containing `[觸發時機]` (Trigger condition) and `[限制條件]` (Constraints).
  3. The `core/engine.py` will automatically parse this into a JSON Schema for the LLM.

### 6. Update the Core Engine (Optional)
- Modify `core/engine.py` only if you need to inject new dynamic variables into the Jinja2 template (e.g., fetching DB status before rendering).

---

**Begin your work by analyzing the user's domain request and generating an Implementation Plan!**
