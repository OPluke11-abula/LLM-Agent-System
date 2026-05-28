"""Executable Prompt Registry for LAS.

Loads prompt snippets with YAML frontmatter from .agent/prompts/<id>.md,
validates variable inputs, and implements automatic Jinja2 delimiters escaping
to protect against Server-Side Template Injection (SSTI) and prompt injection.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import yaml
from jinja2 import Template

logger = logging.getLogger(__name__)


def jinja2_escape(value: Any) -> str:
    """Safely escapes Jinja2 delimiters in variable values to prevent SSTI.

    Replaces delimiters like {{, }}, {%, %}, {#, #} with literal Jinja2
    representations using raw blocks so they are rendered as plain text.
    """
    if value is None:
        return ""
    val_str = str(value)
    # Neutralize control characters using safe placeholders to prevent double replacements
    val_str = val_str.replace("{{", "__JINJA_L2__")
    val_str = val_str.replace("}}", "__JINJA_R2__")
    val_str = val_str.replace("{%", "__JINJA_LP__")
    val_str = val_str.replace("%}", "__JINJA_RP__")
    val_str = val_str.replace("{#", "__JINJA_LC__")
    val_str = val_str.replace("#}", "__JINJA_RC__")

    # Expand to clean raw blocks
    val_str = val_str.replace("__JINJA_L2__", "{% raw %}{{{% endraw %}")
    val_str = val_str.replace("__JINJA_R2__", "{% raw %}}}{% endraw %}")
    val_str = val_str.replace("__JINJA_LP__", "{% raw %}{%{% endraw %}")
    val_str = val_str.replace("__JINJA_RP__", "{% raw %}%}{% endraw %}")
    val_str = val_str.replace("__JINJA_LC__", "{% raw %}{#{% endraw %}")
    val_str = val_str.replace("__JINJA_RC__", "{% raw %}#}{% endraw %}")
    return val_str


class PromptComposer:
    """Manager and executor for the PAP prompt registry."""

    def __init__(self, workspace_path: str = "."):
        self.workspace_path = os.path.abspath(workspace_path)
        self.project_root = Path(self.workspace_path).parent
        self.prompts_dir = self.project_root / ".agent" / "prompts"
        self.prompts_dir.mkdir(parents=True, exist_ok=True)

    def _get_prompt_file(self, prompt_id: str) -> Path:
        """Get the absolute path to a prompt markdown definition."""
        return self.prompts_dir / f"{prompt_id}.md"

    def load_prompt(self, prompt_id: str) -> dict[str, Any]:
        """Load and parse a prompt definition from .agent/prompts/<id>.md."""
        prompt_file = self._get_prompt_file(prompt_id)
        if not prompt_file.is_file():
            raise FileNotFoundError(f"Prompt '{prompt_id}' not found at {prompt_file}")

        content = prompt_file.read_text(encoding="utf-8")
        if not content.startswith("---"):
            raise ValueError(f"Prompt file '{prompt_id}' is missing frontmatter start delimiter '---'")

        parts = content.split("---", 2)
        if len(parts) < 3:
            raise ValueError(f"Prompt file '{prompt_id}' is missing frontmatter end delimiter '---'")

        try:
            prompt_def = yaml.safe_load(parts[1])
        except yaml.YAMLError as err:
            raise ValueError(f"Failed to parse prompt '{prompt_id}' frontmatter YAML: {err}") from err

        if not isinstance(prompt_def, dict):
            raise ValueError(f"Prompt '{prompt_id}' frontmatter is not a dictionary")

        # Basic validation
        required = ["id", "template", "variables", "version"]
        missing = [k for k in required if k not in prompt_def]
        if missing:
            raise ValueError(f"Prompt '{prompt_id}' is missing required fields: {missing}")

        return prompt_def

    def _load_lessons_learned(self) -> str:
        """Loads and formats lessons learned from lessons_learned.md as prompt directives."""
        lessons_file = self.project_root / ".agent" / "knowledge_base" / "lessons_learned.md"
        if not lessons_file.is_file():
            return ""
            
        try:
            content = lessons_file.read_text(encoding="utf-8")
            policies = []
            for line in content.splitlines():
                stripped = line.strip()
                if stripped.startswith("- **Best Practice Policy**:") or stripped.startswith("- **最佳實踐**:") or stripped.startswith("- **Best Practice**:"):
                    policy = stripped.split(":", 1)[1].strip()
                    policies.append(policy)
            
            if policies:
                guidelines = "\n\n## 🎓 SYSTEM SELF-LEARNING DIRECTIVES (Auto-Learned Best Practices):\n"
                for idx, policy in enumerate(policies, 1):
                    guidelines += f"{idx}. {policy}\n"
                return guidelines
        except Exception as e:
            logger.error(f"Failed to load lessons learned: {e}")
            
        return ""

    def build(self, prompt_id: str, variables: dict[str, Any]) -> str:
        """Load a prompt template, validate variables, escape values, and render it."""
        prompt_def = self.load_prompt(prompt_id)
        
        expected_vars = prompt_def.get("variables", [])
        if not isinstance(expected_vars, list):
            expected_vars = [expected_vars]

        # Validate that all required variables are supplied
        missing_vars = [var for var in expected_vars if var not in variables]
        if missing_vars:
            raise ValueError(f"Missing required variables for prompt '{prompt_id}': {missing_vars}")

        # Escape variables to prevent SSTI
        escaped_vars = {}
        for k, v in variables.items():
            if k in expected_vars:
                escaped_vars[k] = jinja2_escape(v)
            else:
                escaped_vars[k] = v

        # Render template
        template_str = prompt_def["template"]
        template = Template(template_str)
        rendered = template.render(**escaped_vars)
        
        # Append dynamic lessons learned directives
        lessons = self._load_lessons_learned()
        return rendered + lessons
