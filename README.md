# FindAi-Studio-LLM-Agent-System

A universal boilerplate template for LLM Agents. Designed to be cloned and automatically customized by AI for any specific domain, featuring dynamic Jinja2 prompting and Pydantic tool registration.

## Quick Start

```powershell
pip install -r requirements.txt
```

## Project Structure

```
agent_workspace/
├── config.yaml              # Static environment parameters
├── agent.jinja2             # Dynamic system prompt template
├── core/
│   ├── engine.py            # Dual-parser engine (Markdown + Python)
│   └── router.py            # Agent execution loop
├── skills/                  # Pydantic-based callable tools
├── knowledge_base/          # SKILL.md domain knowledge
└── memory/                  # Cross-turn state persistence
```

## Architecture: Dual-Track "Brain & Hands"

- **Brain** (`knowledge_base/`): SKILL.md files define the Agent's persona and expertise → injected into system prompt
- **Hands** (`skills/`): Python functions with Pydantic models → auto-discovered as callable tools via reflection

See `AGENTS.md` for full development rules. See `agent_workspace/INSTRUCTIONS_FOR_AI.md` for universal rules and AI customization guide.
