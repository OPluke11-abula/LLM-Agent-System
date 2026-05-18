"""Dual-parser runtime engine for LAS.

The engine keeps two runtime surfaces separate:

1. Persona and project knowledge are loaded from Markdown files under
   ``knowledge_base/`` and injected into Jinja2 prompts.
2. Executable tools are loaded from Python modules under ``skills/`` through
   Pydantic argument models and function docstrings.

HTTP, UI, topology, and PAP synchronization stay outside this module.
"""

from __future__ import annotations

import importlib
import inspect
import logging
import os
import sys
from typing import Any

from pydantic import BaseModel

try:
    from jinja2 import Environment, FileSystemLoader, TemplateNotFound, UndefinedError
except ImportError:
    Environment = None
    FileSystemLoader = None

    class TemplateNotFound(Exception):
        """Fallback exception used when Jinja2 is unavailable."""

    class UndefinedError(Exception):
        """Fallback exception used when Jinja2 is unavailable."""

try:
    import yaml
except ImportError:
    yaml = None

try:
    from observability import TOOL_CALL_COUNT, TOOL_CALL_LATENCY, Timer, tracer
except ImportError:
    from agent_workspace.observability import TOOL_CALL_COUNT, TOOL_CALL_LATENCY, Timer, tracer


logger = logging.getLogger(__name__)


class AgentEngine:
    """Runtime owner for prompt rendering and reflected tool execution."""

    def __init__(self, workspace_path: str = "."):
        self.workspace_path = os.path.abspath(workspace_path)
        self.jinja_env = (
            Environment(loader=FileSystemLoader(self.workspace_path))
            if Environment is not None and FileSystemLoader is not None
            else None
        )

        self.knowledge_contexts: list[dict[str, str]] = []
        self._discover_markdown_contexts()

        self.tools_registry: dict[str, dict[str, Any]] = {}
        self._ensure_skills_importable()
        self._discover_tools()

    def render_prompt(self, runtime_context: dict, agent_name: str = "default") -> str:
        """Render the default or named-agent Jinja2 prompt."""
        if self.jinja_env is None:
            raise RuntimeError("Jinja2 is required to render prompts. Run pip install -r requirements.txt.")

        final_context = {
            "knowledge_contexts": self.knowledge_contexts,
            **runtime_context,
        }
        try:
            if agent_name != "default":
                try:
                    template = self.jinja_env.get_template(f"agents/{agent_name}.jinja2")
                except TemplateNotFound:
                    logger.warning(
                        "Agent template agents/%s.jinja2 not found. Falling back to agent.jinja2.",
                        agent_name,
                    )
                    template = self.jinja_env.get_template("agent.jinja2")
            else:
                template = self.jinja_env.get_template("agent.jinja2")
            return template.render(**final_context)
        except TemplateNotFound as error:
            raise FileNotFoundError(
                f"Required prompt template agent.jinja2 was not found under {self.workspace_path}"
            ) from error
        except UndefinedError as error:
            raise ValueError(
                "Prompt rendering failed because the template referenced an undefined variable. "
                f"Check agent.jinja2 and named-agent templates. Details: {error}"
            ) from error

    def get_tool_schemas(self, allowed_tools: list[str] | None = None) -> list[dict[str, Any]]:
        """Return provider-ready JSON schemas for reflected runtime tools."""
        schemas: list[dict[str, Any]] = []
        for name, tool in self.tools_registry.items():
            if allowed_tools is not None and name not in allowed_tools:
                continue

            schema = tool["schema"].copy()
            schema.pop("title", None)
            schemas.append(
                {
                    "name": name,
                    "description": (tool["description"] or "").strip(),
                    "input_schema": schema,
                }
            )
        return schemas

    def execute_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        allowed_tools: list[str] | None = None,
        context: dict[str, Any] | None = None,
    ) -> str:
        """Validate arguments and execute a reflected tool."""
        if allowed_tools is not None and tool_name not in allowed_tools:
            raise PermissionError(f"Tool '{tool_name}' is not allowed for this request.")

        if tool_name not in self.tools_registry:
            known_tools = ", ".join(sorted(self.tools_registry))
            raise KeyError(f"Unknown tool '{tool_name}'. Available tools: {known_tools}")

        tool = self.tools_registry[tool_name]
        validated_args = tool["args_model"](**arguments)

        with tracer.start_as_current_span("tool_call") as span:
            span.set_attribute("tool_name", tool_name)
            span.set_attribute("arguments", str(arguments))
            try:
                with Timer(TOOL_CALL_LATENCY, labels={"tool_name": tool_name}):
                    if tool["wants_context"]:
                        result = tool["function"](validated_args, context=context or {})
                    else:
                        result = tool["function"](validated_args)
                span.set_attribute("result", str(result)[:500])
                TOOL_CALL_COUNT.labels(tool_name=tool_name, status="success").inc()
                return str(result)
            except Exception as error:
                span.record_exception(error)
                TOOL_CALL_COUNT.labels(tool_name=tool_name, status="error").inc()
                raise

    def summary(self) -> str:
        """Return a human-readable engine inventory."""
        lines = [
            "=" * 60,
            "  AgentEngine Runtime Summary",
            "=" * 60,
            f"  Workspace: {self.workspace_path}",
            "",
            f"  Knowledge contexts ({len(self.knowledge_contexts)})",
        ]
        for ctx in self.knowledge_contexts:
            lines.append(f"    - {ctx['name']}: {ctx['description'][:60]}...")

        lines.append("")
        lines.append(f"  Runtime tools ({len(self.tools_registry)})")
        for name in self.tools_registry:
            lines.append(f"    - {name}")

        lines.append("=" * 60)
        return "\n".join(lines)

    def _discover_markdown_contexts(self) -> None:
        """Load Markdown knowledge files from knowledge_base/."""
        kb_dir = os.path.join(self.workspace_path, "knowledge_base")
        if not os.path.isdir(kb_dir):
            return

        for entry in sorted(os.listdir(kb_dir)):
            entry_path = os.path.join(kb_dir, entry)

            if os.path.isfile(entry_path) and entry.lower().endswith(".md"):
                self._parse_skill_md(entry_path)
            elif os.path.isdir(entry_path):
                skill_file = os.path.join(entry_path, "SKILL.md")
                if os.path.isfile(skill_file):
                    self._parse_skill_md(skill_file)

    def _parse_skill_md(self, filepath: str) -> None:
        """Parse a Markdown knowledge document with optional YAML front matter."""
        try:
            with open(filepath, "r", encoding="utf-8") as file:
                raw = file.read()
        except (OSError, IOError) as error:
            logger.warning("Failed to read knowledge file %s: %s", filepath, error)
            return

        frontmatter, body = self._split_frontmatter(raw)
        name = str(frontmatter.get("name", os.path.basename(os.path.dirname(filepath))))
        description = str(frontmatter.get("description", ""))

        self.knowledge_contexts.append(
            {
                "name": name,
                "description": description,
                "content": body.strip(),
                "source_file": filepath,
            }
        )

    @staticmethod
    def _split_frontmatter(raw_text: str) -> tuple[dict[str, Any], str]:
        """Split YAML front matter from a Markdown body."""
        if not raw_text.startswith("---"):
            return {}, raw_text

        parts = raw_text.split("---", 2)
        if len(parts) < 3:
            return {}, raw_text

        if yaml is not None:
            try:
                parsed = yaml.safe_load(parts[1]) or {}
                frontmatter = parsed if isinstance(parsed, dict) else {}
            except yaml.YAMLError:
                frontmatter = {}
        else:
            frontmatter = AgentEngine._parse_simple_frontmatter(parts[1])

        return frontmatter, parts[2]

    @staticmethod
    def _parse_simple_frontmatter(raw_frontmatter: str) -> dict[str, Any]:
        """Parse simple key/value front matter when PyYAML is unavailable."""
        parsed: dict[str, Any] = {}
        current_key: str | None = None
        for line in raw_frontmatter.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if stripped.startswith("- ") and current_key:
                parsed.setdefault(current_key, []).append(stripped[2:].strip().strip("\"'"))
                continue
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            current_key = key.strip()
            value = value.strip()
            if value:
                parsed[current_key] = value.strip("\"'")
            else:
                parsed[current_key] = []
        return parsed

    def _ensure_skills_importable(self) -> None:
        """Ensure skill modules can be imported as ``skills.<module>``."""
        if self.workspace_path not in sys.path:
            sys.path.insert(0, self.workspace_path)

    def _discover_tools(self) -> None:
        """Reflect Pydantic-based tool functions from skills/*.py."""
        skills_dir = os.path.join(self.workspace_path, "skills")
        if not os.path.isdir(skills_dir):
            return

        for filename in sorted(os.listdir(skills_dir)):
            if not filename.endswith(".py") or filename == "__init__.py":
                continue

            module_name = f"skills.{filename[:-3]}"
            try:
                module = importlib.import_module(module_name)
                self._register_functions_from_module(module)
            except Exception as error:
                logger.warning("Failed to import skill module %s: %s", module_name, error)

    def _register_functions_from_module(self, module: Any) -> None:
        """Register public functions whose first argument is a Pydantic model."""
        for name, func in inspect.getmembers(module, inspect.isfunction):
            if name.startswith("_"):
                continue

            sig = inspect.signature(func)
            params = list(sig.parameters.values())
            if not params:
                continue

            annotation = params[0].annotation
            if not (inspect.isclass(annotation) and issubclass(annotation, BaseModel)):
                continue

            self.tools_registry[name] = {
                "function": func,
                "args_model": annotation,
                "description": inspect.getdoc(func),
                "schema": annotation.model_json_schema(),
                "wants_context": "context" in sig.parameters,
            }


if __name__ == "__main__":
    import json

    engine = AgentEngine(workspace_path=os.path.dirname(os.path.dirname(__file__)))
    print(engine.summary())

    print("\n--- Rendered System Prompt Preview ---")
    prompt = engine.render_prompt(
        {
            "current_time": "2026-05-16T11:30:00+08:00",
            "context_status": "OK",
            "user_input": "Hello, calculate something for me.",
        }
    )
    print(prompt[:500])

    print("\n--- Tool Schemas ---")
    print(json.dumps(engine.get_tool_schemas(), indent=2, ensure_ascii=False))
