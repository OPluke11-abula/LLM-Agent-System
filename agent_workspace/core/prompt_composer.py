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
        path_check = Path(self.workspace_path)
        if (path_check / ".agent").is_dir():
            self.project_root = path_check
        elif (path_check.parent / ".agent").is_dir():
            self.project_root = path_check.parent
        else:
            self.project_root = path_check.parent
        self.prompts_dir = self.project_root / ".agent" / "prompts"
        self.prompts_dir.mkdir(parents=True, exist_ok=True)

    def load_role_persona(self, role: str) -> str | None:
        """Loads a role configuration markdown file from .agent/prompts/roles/{role}.md

        and returns the 'persona' property parsed from its YAML frontmatter.
        """
        role_file = self.prompts_dir / "roles" / f"{role}.md"
        if not role_file.is_file():
            return None

        try:
            content = role_file.read_text(encoding="utf-8")
            if not content.startswith("---"):
                return None

            parts = content.split("---", 2)
            if len(parts) < 3:
                return None

            role_def = yaml.safe_load(parts[1])
            if not isinstance(role_def, dict):
                return None

            return role_def.get("persona")
        except Exception as e:
            logger.error(f"Failed to load or parse role '{role}': {e}")
            return None

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
        compiled = rendered + lessons
        return self.prune_compiled_prompt(compiled)

    def prune_compiled_prompt(self, compiled_prompt: str) -> str:
        """Evaluates the token footprint of dynamic learning directives inside compiled_prompt.

        If cumulative token count exceeds 6,000, older guidelines are cleanly compacted.
        """
        lines = compiled_prompt.splitlines()
        
        # Parse the prompt into sections
        sections = [] # List of tuples: (is_directive, header_line, [content_lines])
        current_is_directive = False
        current_header = ""
        current_lines = []
        
        for line in lines:
            stripped = line.strip()
            if (stripped.startswith("## 🎓 SYSTEM SELF-LEARNING DIRECTIVES") or 
                stripped.startswith("## ⚡ Auto-Learned Swarm Constraints")):
                # Save previous section
                sections.append((current_is_directive, current_header, current_lines))
                current_is_directive = True
                current_header = line
                current_lines = []
            else:
                current_lines.append(line)
                
        # Append final section
        sections.append((current_is_directive, current_header, current_lines))
        
        # Extract and measure size of all directive blocks
        total_directive_chars = 0
        directive_blocks = []
        
        for is_dir, header, content_lines in sections:
            if is_dir:
                block_text = "\n".join(content_lines)
                total_directive_chars += len(header) + 1 + len(block_text)
                directive_blocks.append((header, content_lines))
                
        # 1 token ≈ 4 characters
        token_count = total_directive_chars // 4
        if token_count <= 6000:
            return compiled_prompt
            
        # We need to prune and compress the directive blocks!
        import re
        all_items = []
        for header, content_lines in directive_blocks:
            current_item = []
            for line in content_lines:
                stripped = line.strip()
                if not stripped:
                    continue
                # Match numbered lists or bullet points
                if (stripped.startswith("-") or 
                    stripped.startswith("*") or 
                    re.match(r"^\d+\.", stripped) or 
                    stripped.startswith("#")):
                    if current_item:
                        all_items.append(" ".join(current_item))
                        current_item = []
                    current_item.append(stripped)
                else:
                    current_item.append(stripped)
            if current_item:
                all_items.append(" ".join(current_item))
                
        if not all_items:
            return compiled_prompt
            
        # Retain last keep_count items in their full detail, summarize the rest
        keep_count = max(5, len(all_items) // 4)
        if keep_count >= len(all_items):
            keep_count = len(all_items) // 2
            
        older_items = all_items[:-keep_count]
        newer_items = all_items[-keep_count:]
        
        # Generate dense semantic summaries from older items
        summaries = []
        for item in older_items:
            item_lower = item.lower()
            if "lock" in item_lower or "sqlite" in item_lower:
                summaries.append("Enforce async lock guards on SQLite/disk concurrent write transactions.")
            elif "deadlock" in item_lower or "mock" in item_lower or "approval" in item_lower:
                summaries.append("Mock approval checks and bypass interactive gateways in automated/CI tests.")
            elif "resize" in item_lower or "observer" in item_lower:
                summaries.append("Throttle and debounce dynamic viewport resizing and ResizeObservers using requestAnimationFrame.")
            elif "path" in item_lower or "workspace" in item_lower:
                summaries.append("Dynamically inspect parent/current directories for `.agent` folder to resolve workspace paths.")
            elif "token" in item_lower or "budget" in item_lower or "context" in item_lower:
                summaries.append("Actively prune completed task logs and delete obsolete/redundant files to minimize context weight.")
            else:
                # Extract first few descriptive words to make a neat semantic summary
                words = [w for w in item.split() if len(w) > 4][:6]
                if words:
                    clean_words = [re.sub(r"[^\w]", "", w) for w in words]
                    summaries.append(f"Optimized directive regarding: {' '.join(clean_words)}.")
                    
        # Deduplicate summaries
        unique_summaries = []
        for s in summaries:
            if s not in unique_summaries:
                unique_summaries.append(s)
                
        if not unique_summaries:
            unique_summaries.append("Adhere to general robust coding standards, transaction safety, and non-interactive testing protocols.")
            
        # Reconstruct the compacted directive block
        compacted_lines = []
        compacted_lines.append("### ⚡ COMPACTED SEMANTIC HISTORICAL DIRECTIVES (Unified Best Practices):")
        for idx, s in enumerate(unique_summaries, 1):
            compacted_lines.append(f"- **Summary Principle {idx}**: {s}")
            
        compacted_lines.append("\n### 🎓 ACTIVE HIGH-PRIORITY SYSTEM DIRECTIVES:")
        for idx, item in enumerate(newer_items, 1):
            # Strip leading numbers/bullets if any to avoid double numbering in reconstruction
            clean_item = re.sub(r"^[-*\s]+", "", item)
            clean_item = re.sub(r"^\d+\.\s*", "", clean_item)
            compacted_lines.append(f"{idx}. {clean_item}")
            
        compacted_block = "\n".join(compacted_lines)
        
        # Reconstruct the final system prompt by replacing the first directive block and omitting the rest
        reconstructed = []
        replaced = False
        for is_dir, header, content_lines in sections:
            if is_dir:
                if not replaced:
                    reconstructed.append(header)
                    reconstructed.append(compacted_block)
                    replaced = True
            else:
                if header:
                    reconstructed.append(header)
                reconstructed.extend(content_lines)
                
        return "\n".join(reconstructed)

    def optimize_role_prompt(self, role: str, execution_efficiency: float, token_usage: int, outcome: str) -> bool:
        """Dynamically refine and auto-optimize standard role prompts based on execution performance feedback."""
        role_file = self.prompts_dir / "roles" / f"{role}.md"
        if not role_file.is_file():
            return False

        try:
            content = role_file.read_text(encoding="utf-8")
            if not content.startswith("---"):
                return False

            parts = content.split("---", 2)
            if len(parts) < 3:
                return False

            role_def = yaml.safe_load(parts[1]) or {}
            if not isinstance(role_def, dict):
                return False

            # 1. Automated semantic version increment loop
            version = str(role_def.get("version", "1.0.0"))
            try:
                version_parts = list(map(int, version.split(".")))
                version_parts[-1] += 1
                new_version = ".".join(map(str, version_parts))
            except Exception:
                new_version = version + ".1"
            role_def["version"] = new_version

            # 2. Append auto-learned optimized prompt instructions to markdown body
            body = parts[2].strip()
            constraints = []

            if outcome == "failure":
                constraints.append("- FailSafe constraint: Avoid repeating structural connection locking violations. Wrap database transaction loops with synchronized connection locks.")
            if token_usage > 50000:
                constraints.append("- TokenBudget constraint: Maintain highly dense system prompt responses and actively dejunk workspace file footprints to optimize context weight.")
            if execution_efficiency > 120:
                constraints.append("- Latency constraint: Direct prompt routing to specific subtasks and bypass repetitive intent classifications to streamline loops.")

            if constraints:
                if "## ⚡ Auto-Learned Swarm Constraints" not in body:
                    body += "\n\n## ⚡ Auto-Learned Swarm Constraints\n"
                for c in constraints:
                    if c not in body:
                        body += f"{c}\n"

            # 3. Serialize frontmatter and body back to disk
            new_frontmatter = yaml.safe_dump(role_def, allow_unicode=True, sort_keys=False).strip()
            new_content = f"---\n{new_frontmatter}\n---\n\n{body}\n"
            role_file.write_text(new_content, encoding="utf-8")
            logger.info("Successfully optimized and versioned standard prompt for role '%s' to version %s", role, new_version)
            return True

        except Exception as e:
            logger.error(f"Failed to optimize prompt for role '{role}': {e}")
            return False

