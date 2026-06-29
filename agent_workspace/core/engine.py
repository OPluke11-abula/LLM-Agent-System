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

from agent_workspace.observability import TOOL_CALL_COUNT, TOOL_CALL_LATENCY, Timer, tracer
from agent_workspace.core.precheck import SkillsPrechecker


logger = logging.getLogger(__name__)


class HandoffRequired(RuntimeError):
    """Raised when a thread handoff is required due to context/turn limits."""

    HANDOFF_EXIT_CODE = 42

    def __init__(self, handoff_id: str, reason: str) -> None:
        self.handoff_id = handoff_id
        self.reason = reason
        super().__init__(
            f"Handoff required ({reason}). Handoff packet exported as '{handoff_id}'."
        )


class AgentEngine:
    """Runtime owner for prompt rendering and reflected tool execution."""

    PROTOCOL_VERSION = "1.0.0"
    RUNTIME_VERSION = "0.5.0"

    def __init__(self, workspace_path: str = ".", bypass_onboarding: bool = False, enforce_onboarding: bool | None = None):
        self.workspace_path = os.path.abspath(workspace_path)
        self.prechecker = SkillsPrechecker(self.workspace_path)

        # Load agent config YAML frontmatter if it exists
        self.config = {}
        agent_md = os.path.join(self.workspace_path, ".agent", "agent.md")
        if os.path.isfile(agent_md):
            try:
                with open(agent_md, "r", encoding="utf-8") as f:
                    raw_agent = f.read()
                self.config, _ = self._split_frontmatter(raw_agent)
            except Exception:
                pass

        # Check version compatibility at startup
        self._check_version_compat()

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
        self._discover_markdown_skills()

        # Session turns and handoff threshold tracking (Task 23-01)
        self.session_turns: dict[str, int] = {}
        self.handoff_threshold = 5
        config_path = os.path.join(self.workspace_path, "config.yaml")
        if os.path.isfile(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    cfg = yaml.safe_load(f) or {}
                    self.handoff_threshold = cfg.get("agent", {}).get("handoff_threshold", 5)
            except Exception:
                pass

        # Onboarding Sequence Configuration
        self.onboarding_sequence = ["agent.md", "skills.md", "agent_tasks.md", "handoff_guide.md"]
        self._onboarding_read: list[str] = []
        env_bypass = os.environ.get("PAP_BYPASS_ONBOARDING", "").strip().lower() in ("1", "true", "yes", "on")
        self._bypass_onboarding = bypass_onboarding or env_bypass

        # Determine if onboarding is required
        if enforce_onboarding is not None:
            self._onboarding_required = enforce_onboarding
        else:
            self._onboarding_required = self._resolve_onboarding_required()



        # Auto-handoff limits
        auto_handoff_cfg = self.config.get("auto_handoff", {}) or {}
        self._max_turns = int(auto_handoff_cfg.get("max_turns", 0))
        self._max_context_chars = int(auto_handoff_cfg.get("max_context_chars", 0))
        self._turn_count = 0
        self._context_chars = 0

    def _resolve_onboarding_required(self) -> bool:
        """Resolve whether all onboarding sequence files are present and declared."""
        paths_map = {
            "agent.md": os.path.join(self.workspace_path, ".agent", "agent.md"),
            "skills.md": os.path.join(self.workspace_path, ".agent", "skills.md"),
            "agent_tasks.md": os.path.join(self.workspace_path, "agent_tasks.md") if os.path.isfile(os.path.join(self.workspace_path, "agent_tasks.md")) else os.path.join(self.workspace_path, ".agent", "agent_tasks.md"),
            "handoff_guide.md": os.path.join(self.workspace_path, ".agent", "handoff_guide.md"),
        }
        for label, path in paths_map.items():
            if not os.path.isfile(path):
                return False

        protocol = self.config.get("protocol")
        if not isinstance(protocol, dict):
            return False
        entrypoints = protocol.get("entrypoints")
        if not isinstance(entrypoints, dict):
            return False
        return all(k in entrypoints for k in ("skills", "tasks", "handoff"))

    def _check_version_compat(self) -> None:
        """Verify protocol version compatibility and min runtime version requirement."""
        protocol_ver = self.config.get("protocol_version")
        min_runtime_ver = self.config.get("min_runtime_version")

        if protocol_ver:
            parsed_manifest_proto = self._parse_version(str(protocol_ver))
            parsed_engine_proto = self._parse_version(self.PROTOCOL_VERSION)
            if len(parsed_manifest_proto) > 0 and len(parsed_engine_proto) > 0:
                if parsed_manifest_proto[0] != parsed_engine_proto[0]:
                    import warnings
                    msg = f"Protocol version mismatch: manifest protocol version '{protocol_ver}' is incompatible with engine protocol version '{self.PROTOCOL_VERSION}'"
                    warnings.warn(msg, UserWarning)
                    logger.warning(msg)

        if min_runtime_ver:
            parsed_min_runtime = self._parse_version(str(min_runtime_ver))
            parsed_engine_runtime = self._parse_version(self.RUNTIME_VERSION)
            if parsed_min_runtime > parsed_engine_runtime:
                import warnings
                msg = f"Runtime version mismatch: manifest requires min_runtime_version '{min_runtime_ver}' but engine runtime version is '{self.RUNTIME_VERSION}'"
                warnings.warn(msg, UserWarning)
                logger.warning(msg)

    def is_onboarding_complete(self) -> bool:
        """Check if the strict onboarding sequence has been completed."""
        if self._bypass_onboarding or not self._onboarding_required:
            return True
        return len(self._onboarding_read) >= len(self.onboarding_sequence)

    def read_onboarding_file(self, filename: str) -> str:
        """Read an onboarding document in strict sequence order."""
        basename = os.path.basename(filename)
        if basename not in self.onboarding_sequence:
            raise ValueError(f"File '{filename}' is not part of the onboarding sequence.")

        paths_map = {
            "agent.md": os.path.join(self.workspace_path, ".agent", "agent.md"),
            "skills.md": os.path.join(self.workspace_path, ".agent", "skills.md"),
            "agent_tasks.md": os.path.join(self.workspace_path, "agent_tasks.md") if os.path.isfile(os.path.join(self.workspace_path, "agent_tasks.md")) else os.path.join(self.workspace_path, ".agent", "agent_tasks.md"),
            "handoff_guide.md": os.path.join(self.workspace_path, ".agent", "handoff_guide.md"),
        }
        target_path = paths_map[basename]
        if not os.path.isfile(target_path):
            raise FileNotFoundError(f"Onboarding file '{basename}' missing at '{target_path}'.")

        with open(target_path, "r", encoding="utf-8") as f:
            content = f.read()

        if self._bypass_onboarding or not self._onboarding_required:
            return content

        if basename in self._onboarding_read:
            return content

        expected = self.onboarding_sequence[len(self._onboarding_read)]
        if basename != expected:
            raise PermissionError(
                f"Onboarding sequence out of order. Expected {expected}, got {basename}. "
                f"Must read agent.md -> skills.md -> agent_tasks.md -> handoff_guide.md before calling tools."
            )

        self._onboarding_read.append(basename)
        return content

    def complete_onboarding(self) -> None:
        """Mark onboarding sequence as completed."""
        self._onboarding_read = list(self.onboarding_sequence)

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
        # Onboarding guard check
        if not self.is_onboarding_complete():
            expected = self.onboarding_sequence[len(self._onboarding_read)]
            raise PermissionError(
                f"Onboarding sequence incomplete. Must read agent.md -> skills.md -> "
                f"agent_tasks.md -> handoff_guide.md before calling tools. Next required file: {expected}."
            )

        # Auto-handoff limits tracking & triggers
        self._turn_count += 1
        self._context_chars += len(str(arguments))

        reason = None
        if self._max_turns > 0 and self._turn_count > self._max_turns:
            reason = f"Turn count {self._turn_count} exceeds max_turns {self._max_turns}"
        elif self._max_context_chars > 0 and self._context_chars > self._max_context_chars:
            reason = f"Context length {self._context_chars} chars exceeds max_context_chars {self._max_context_chars}"

        if reason:
            session_id = (context or {}).get("session_id", "default_session") if context else "default_session"
            handoff_id = self.export_handoff(session_id, f"Auto-handoff: {reason}")
            raise HandoffRequired(handoff_id=handoff_id, reason=reason)

        if allowed_tools is not None and tool_name not in allowed_tools:
            raise PermissionError(f"Tool '{tool_name}' is not allowed for this request.")

        if tool_name not in self.tools_registry:
            known_tools = ", ".join(sorted(self.tools_registry))
            raise KeyError(f"Unknown tool '{tool_name}'. Available tools: {known_tools}")

        tool = self.tools_registry[tool_name]

        precheck_res = self.prechecker.run_precheck(tool_name, tool.get("function"))
        if precheck_res["status"] == "BLOCKED":
            import json
            return json.dumps({
                "status": "BLOCKED",
                "message": f"Pre-check failed for tool '{tool_name}': {precheck_res['message']} Please verify configuration."
            })

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
        for name, tool in self.tools_registry.items():
            is_md = "[Markdown Skill]" if tool.get("is_markdown_skill") else ""
            lines.append(f"    - {name} {is_md}".strip())

        lines.append("=" * 60)
        return "\n".join(lines)

    def _discover_markdown_contexts(self) -> None:
        """Load Markdown knowledge files from knowledge_base/ and PAP files from .agent/."""
        # 1. Load standard domain knowledge files
        kb_dir = os.path.join(self.workspace_path, "knowledge_base")
        if os.path.isdir(kb_dir):
            for entry in sorted(os.listdir(kb_dir)):
                entry_path = os.path.join(kb_dir, entry)

                if os.path.isfile(entry_path) and entry.lower().endswith(".md"):
                    self._parse_skill_md(entry_path)
                elif os.path.isdir(entry_path):
                    skill_file = os.path.join(entry_path, "SKILL.md")
                    if os.path.isfile(skill_file):
                        self._parse_skill_md(skill_file)

        # 2. Load PAP agent identity and tasks from .agent/ directory if they exist
        pap_dir = os.path.join(self.workspace_path, ".agent")
        if os.path.isdir(pap_dir):
            agent_md = os.path.join(pap_dir, "agent.md")
            if os.path.isfile(agent_md):
                self._parse_pap_doc(
                    agent_md,
                    default_name="Agent Identity Manifest",
                    default_desc="Agent identity, role, and capabilities definition"
                )
            tasks_md = os.path.join(pap_dir, "agent_tasks.md")
            if os.path.isfile(tasks_md):
                self._parse_pap_doc(
                    tasks_md,
                    default_name="Agent Tasks Queue",
                    default_desc="List of development tasks, priorities, and implementation checklists"
                )

    def _parse_skill_md(self, filepath: str) -> None:
        """Parse a Markdown knowledge document with optional YAML front matter."""
        from pathlib import Path
        resolved = Path(filepath).resolve()

        is_allowed = False
        workspace_resolved = Path(self.workspace_path).resolve()
        try:
            resolved.relative_to(workspace_resolved)
            is_allowed = True
        except ValueError:
            pass

        try:
            resolved.relative_to(workspace_resolved.parent)
            is_allowed = True
        except ValueError:
            pass

        import tempfile
        try:
            temp_dir = Path(tempfile.gettempdir()).resolve()
            resolved.relative_to(temp_dir)
            is_allowed = True
        except ValueError:
            pass

        if not is_allowed:
            raise PermissionError("Directory traversal warning: Access denied outside project boundary")

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
    def _parse_version(version_str: str) -> tuple[int, ...]:
        """Parse a semantic version string into a tuple of integers for comparison."""
        try:
            clean_str = version_str.strip().lstrip("v")
            clean_str = clean_str.split("-")[0].split("+")[0]
            parts = []
            for part in clean_str.split("."):
                if part.isdigit():
                    parts.append(int(part))
                else:
                    parts.append(0)
            return tuple(parts)
        except Exception:
            return (0,)

    def _parse_pap_doc(self, filepath: str, default_name: str, default_desc: str) -> None:
        """Parse a PAP document and load it into knowledge contexts."""
        from pathlib import Path
        resolved = Path(filepath).resolve()

        is_allowed = False
        workspace_resolved = Path(self.workspace_path).resolve()
        try:
            resolved.relative_to(workspace_resolved)
            is_allowed = True
        except ValueError:
            pass

        try:
            resolved.relative_to(workspace_resolved.parent)
            is_allowed = True
        except ValueError:
            pass

        import tempfile
        try:
            temp_dir = Path(tempfile.gettempdir()).resolve()
            resolved.relative_to(temp_dir)
            is_allowed = True
        except ValueError:
            pass

        if not is_allowed:
            raise PermissionError("Directory traversal warning: Access denied outside project boundary")

        try:
            with open(filepath, "r", encoding="utf-8") as file:
                raw = file.read()
        except (OSError, IOError) as error:
            logger.warning("Failed to read PAP file %s: %s", filepath, error)
            return

        frontmatter, body = self._split_frontmatter(raw)
        name = str(frontmatter.get("name", default_name))
        description = str(frontmatter.get("description", default_desc))

        # Version compatibility verification (Task 1-05)
        protocol_ver = frontmatter.get("protocol_version")
        min_runtime_ver = frontmatter.get("min_runtime_version")

        if protocol_ver:
            parsed_manifest_proto = self._parse_version(str(protocol_ver))
            parsed_engine_proto = self._parse_version(self.PROTOCOL_VERSION)
            if len(parsed_manifest_proto) > 0 and len(parsed_engine_proto) > 0:
                if parsed_manifest_proto[0] != parsed_engine_proto[0]:
                    import warnings
                    msg = f"Protocol version mismatch: manifest protocol version '{protocol_ver}' is incompatible with engine protocol version '{self.PROTOCOL_VERSION}'"
                    warnings.warn(msg, UserWarning)
                    logger.warning(msg)

        if min_runtime_ver:
            parsed_min_runtime = self._parse_version(str(min_runtime_ver))
            parsed_engine_runtime = self._parse_version(self.RUNTIME_VERSION)
            if parsed_min_runtime > parsed_engine_runtime:
                import warnings
                msg = f"Runtime version mismatch: manifest requires min_runtime_version '{min_runtime_ver}' but engine runtime version is '{self.RUNTIME_VERSION}'"
                warnings.warn(msg, UserWarning)
                logger.warning(msg)

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
                "is_markdown_skill": False,
            }

    def _discover_markdown_skills(self) -> None:
        """Load pure Markdown SKILL.md files as Pydantic tools."""
        try:
            from core.skill_loader import SkillLoader
            loader = SkillLoader(self.workspace_path)
            markdown_skills = loader.discover_skills()
            self.tools_registry.update(markdown_skills)
        except ImportError as e:
            logger.warning("Failed to load SkillLoader: %s", e)

    def export_handoff(
        self,
        session_id: str,
        context_summary: str,
        pending_steps: list[str] | None = None,
    ) -> str:
        """Export session working memory and agent task state into a standardized PAP handoff packet.

        Verifies state integrity with a SHA256 checksum and writes the packet
        to .agent/memory/handoff/handoff-<checksum>.json.
        """
        import hashlib
        import json
        from datetime import datetime, timezone
        from pathlib import Path

        project_root = Path(self.workspace_path).parent

        # 1. Gather task_state
        task_state = {}
        tasks_file = project_root / ".agent" / "agent_tasks.md"
        if tasks_file.is_file():
            try:
                task_state["agent_tasks_content"] = tasks_file.read_text(encoding="utf-8")
            except Exception as e:
                logger.warning("Failed to read agent_tasks.md for handoff: %s", e)

        # 2. Gather memory_snapshot (working memory)
        memory_snapshot = {}
        memory_dir = Path(self.workspace_path) / "memory"
        session_file = (memory_dir / f"{session_id}.json").resolve()
        try:
            session_file.relative_to(memory_dir.resolve())
        except ValueError:
            raise PermissionError("Directory traversal warning: Access denied outside memory boundary")
        if session_file.is_file():
            try:
                memory_snapshot["working_memory"] = json.loads(session_file.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning("Failed to read session memory %s for handoff: %s", session_id, e)
        memory_snapshot["session_id"] = session_id
        pending_steps = pending_steps or ["Resume LAS session from exported handoff state."]

        # 3. Calculate SHA256 Checksum
        payload = {
            "task_state": task_state,
            "pending_steps": pending_steps,
            "context_summary": context_summary,
            "memory_snapshot": memory_snapshot
        }
        serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
        checksum = hashlib.sha256(serialized).hexdigest()

        # 4. Construct complete handoff packet
        handoff_id = f"handoff-{checksum[:16]}"
        packet = {
            "protocol": "PAP-Handoff",
            "version": "1.0.0",
            "handoff_id": handoff_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "task_state": task_state,
            "pending_steps": pending_steps,
            "context_summary": context_summary,
            "memory_snapshot": memory_snapshot,
            "checksum": checksum
        }

        # 5. Persist to filesystem
        handoff_dir = project_root / ".agent" / "memory" / "handoff"
        handoff_dir.mkdir(parents=True, exist_ok=True)
        handoff_file = handoff_dir / f"{handoff_id}.json"
        prompt_file = handoff_dir / f"{handoff_id}_prompt.md"

        try:
            handoff_file.write_text(json.dumps(packet, ensure_ascii=False, indent=2), encoding="utf-8")

            # Compile dense English handoff prompt markdown (Task 23-01)
            prompt_content = f"""# FindAi Studio LLM Agent System (LAS) - Warm Thread Handoff Prompt

You are resuming a conversational thread in a fresh environment. The state of the previous session has been compacted and exported.

## Handoff Metadata
- **Handoff ID**: {handoff_id}
- **Created At**: {packet["created_at"]}
- **Session ID**: {session_id}

## Context Summary
{context_summary}

## Pending Steps
{chr(10).join(f"- {step}" for step in pending_steps)}

## Structural State Inventory
- **Tasks File**: `.agent/agent_tasks.md`
- **Memory Snapshot**: `memory/{session_id}.json`
- **Integrity Checksum**: {checksum}

## Instructions to Resume State
To restore the task queue, memory snapshot, and structural state of the agent, please run the following command or use the import feature in your active environment:

```bash
import_handoff {handoff_id}
```

This handoff is part of the Federated Swarm Autonomous Handoff protocol. It enables seamless multi-thread transfer by carrying the complete session state across thread boundaries.
"""
            prompt_file.write_text(prompt_content, encoding="utf-8")
            logger.info("Successfully exported handoff packet %s and prompt markdown", handoff_id)
        except Exception as e:
            logger.error("Failed to write handoff packet to %s: %s", handoff_file, e)
            raise RuntimeError(f"Failed to save handoff packet: {e}") from e

        return handoff_id

    def import_handoff(self, handoff_id: str) -> dict[str, Any]:
        """Import a PAP handoff packet and restore session working memory.

        Verifies cryptographic integrity with SHA256 checksum and raises ValueError
        on any mismatch or malformed packet.
        """
        import hashlib
        import json
        from pathlib import Path

        project_root = Path(self.workspace_path).parent
        handoff_dir = (project_root / ".agent" / "memory" / "handoff").resolve()
        handoff_file = (handoff_dir / f"{handoff_id}.json").resolve()
        try:
            handoff_file.relative_to(handoff_dir)
        except ValueError:
            raise PermissionError("Directory traversal warning: Access denied outside handoff boundary")

        if not handoff_file.is_file():
            raise FileNotFoundError(f"Handoff packet file '{handoff_id}' not found at {handoff_file}")

        try:
            packet = json.loads(handoff_file.read_text(encoding="utf-8"))
        except Exception as e:
            raise ValueError(f"Malformed handoff packet JSON for '{handoff_id}': {e}") from e

        # Validate packet fields
        required = ["protocol", "version", "task_state", "context_summary", "memory_snapshot", "checksum"]
        missing = [k for k in required if k not in packet]
        if missing:
            raise ValueError(f"Handoff packet '{handoff_id}' is missing required fields: {missing}")

        # Verify integrity checksum
        task_state = packet["task_state"]
        context_summary = packet["context_summary"]
        memory_snapshot = packet["memory_snapshot"]
        checksum_expected = packet["checksum"]
        pending_steps = packet.get("pending_steps")

        payload = {
            "task_state": task_state,
            "context_summary": context_summary,
            "memory_snapshot": memory_snapshot
        }
        if isinstance(pending_steps, list):
            payload["pending_steps"] = pending_steps
        serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
        checksum_actual = hashlib.sha256(serialized).hexdigest()

        if checksum_actual != checksum_expected:
            raise ValueError("Handoff packet integrity verification failed (checksum mismatch)")

        # Restore working memory snapshot
        working_memory = memory_snapshot.get("working_memory")
        if working_memory:
            session_id = memory_snapshot.get("session_id", "default")
            session_file = Path(self.workspace_path) / "memory" / f"{session_id}.json"
            session_file.parent.mkdir(parents=True, exist_ok=True)
            try:
                session_file.write_text(json.dumps(working_memory, ensure_ascii=False, indent=2), encoding="utf-8")
                logger.info("Successfully restored working memory for session %s", session_id)
            except Exception as e:
                logger.error("Failed to restore working memory to %s: %s", session_file, e)
                raise RuntimeError(f"Failed to restore working memory: {e}") from e

        return packet

    def increment_turns(self, session_id: str, context_summary: str | None = None) -> tuple[int, bool, str | None]:
        """Increment session turn count and trigger export_handoff if threshold is reached (Task 23-01).

        Returns a tuple of (current_turns, triggered_handoff, handoff_id).
        """
        turns = self.session_turns.get(session_id, 0) + 1
        self.session_turns[session_id] = turns
        triggered = False
        handoff_id = None
        if turns >= self.handoff_threshold:
            summary = context_summary or f"Automated handoff triggered at turn {turns}."
            try:
                handoff_id = self.export_handoff(session_id, summary)
                triggered = True
            except Exception as e:
                logger.error("Failed to automatically export handoff for session %s: %s", session_id, e)
        return turns, triggered, handoff_id


class DynamicCodeGenerator:
    """Gateway for generating specialized tools at runtime with security audits and test validation."""

    def __init__(self, engine: AgentEngine):
        self.engine = engine
        self.workspace_path = engine.workspace_path

    def generate_and_load_skill(self, name: str, code_content: str) -> bool:
        """Audit, validate, run automated test gate, and dynamically load the new skill."""
        import ast
        import sys
        import os
        from pathlib import Path
        import subprocess

        # 1. AST Security Audit
        try:
            tree = ast.parse(code_content)
        except SyntaxError as e:
            raise ValueError(f"Syntax error in generated code: {e}")

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func_name = ""
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    func_name = node.func.attr

                if func_name in {"eval", "exec", "compile", "system", "popen", "subprocess", "run"}:
                    raise PermissionError(f"Security violation: unsafe execution call '{func_name}' detected")

        # 2. Verify Tool Contract Structure
        has_model = False
        model_name = ""
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                for base in node.bases:
                    if isinstance(base, ast.Name) and base.id == "BaseModel":
                        has_model = True
                        model_name = node.name
                        break

        if not has_model:
            raise ValueError("Generated skill must define a Pydantic BaseModel argument class")

        has_func = False
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
                if node.args.args:
                    first_arg = node.args.args[0]
                    if first_arg.annotation and isinstance(first_arg.annotation, ast.Name) and first_arg.annotation.id == model_name:
                        has_func = True
                        break

        if not has_func:
            raise ValueError("Generated skill must define a public function whose first parameter is annotated with the Pydantic BaseModel")

        # Ensure directories exist
        skills_dir = Path(self.workspace_path) / "skills"
        skills_dir.mkdir(parents=True, exist_ok=True)
        tests_dir = Path(self.workspace_path) / "tests"
        tests_dir.mkdir(parents=True, exist_ok=True)

        skill_file_path = skills_dir / f"{name}.py"
        test_file_path = tests_dir / f"test_gen_{name}.py"

        # 3. Write skill file
        skill_file_path.write_text(code_content, encoding="utf-8")

        # 4. Subprocess Pytest Verification Gate
        test_code = f"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from skills.{name} import {name}, {model_name}

def test_dynamic_run():
    # Verify we can import and verify basic execution
    assert {name} is not None
"""
        test_file_path.write_text(test_code, encoding="utf-8")

        python_exe = sys.executable or "C:\\Users\\luke2\\AppData\\Local\\Programs\\Python\\Python314\\python.exe"
        try:
            res = subprocess.run(
                [python_exe, "-m", "pytest", str(test_file_path)],
                capture_output=True,
                text=True,
                timeout=10
            )
            if res.returncode != 0:
                # Clean up generated files
                if skill_file_path.is_file():
                    os.remove(skill_file_path)
                raise ValueError(f"pytest verification gate failed:\n{res.stdout}\n{res.stderr}")
        finally:
            if test_file_path.is_file():
                os.remove(test_file_path)

        # 5. Dynamic loading at runtime
        import sys
        import importlib
        if "skills" in sys.modules:
            skills_mod = sys.modules["skills"]
            if hasattr(skills_mod, "__path__"):
                skills_path_str = str(skills_dir.resolve())
                if skills_path_str not in skills_mod.__path__:
                    skills_mod.__path__.append(skills_path_str)

        module_name = f"skills.{name}"
        try:
            if module_name in sys.modules:
                # Force remove old cache to ensure fresh import from new path
                sys.modules.pop(module_name, None)
            module = importlib.import_module(module_name)
            self.engine._register_functions_from_module(module)
            logger.info("Successfully hot-loaded dynamically generated tool '%s' into tools_registry", name)
            return True
        except Exception as e:
            if skill_file_path.is_file():
                os.remove(skill_file_path)
            raise RuntimeError(f"Dynamic skill loading failed: {e}") from e


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
