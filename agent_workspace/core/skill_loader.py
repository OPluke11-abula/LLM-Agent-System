import os
import yaml
from typing import Any, Callable
from pydantic import BaseModel, create_model, Field

class SkillLoader:
    """
    SkillLoader bridges pure Markdown SKILL.md files (anthropics format) 
    into executable Pydantic tool schemas for the AgentEngine.
    """

    def __init__(self, workspace_path: str):
        self.workspace_path = os.path.abspath(workspace_path)
        self.markdown_skills: dict[str, dict[str, Any]] = {}

    def discover_skills(self) -> dict[str, dict[str, Any]]:
        """
        Scan both global skills directory and local workspace skills/ directory,
        extract frontmatter, and generate Pydantic tools.
        Returns a registry dictionary compatible with AgentEngine.tools_registry.
        """
        import sys
        is_testing = "pytest" in sys.modules

        # 1. Load global skills first (so local skills can override them)
        if not is_testing:
            global_skills_dir = os.path.join(os.path.expanduser("~"), ".gemini", "antigravity", "skills")
            if os.path.isdir(global_skills_dir):
                for entry in sorted(os.listdir(global_skills_dir)):
                    entry_path = os.path.join(global_skills_dir, entry)
                    if os.path.isdir(entry_path):
                        skill_file = os.path.join(entry_path, "SKILL.md")
                        if os.path.isfile(skill_file):
                            self._parse_and_register_skill(skill_file, is_global=True)

        # 2. Load local skills (overriding global if naming collides)
        skills_dir = os.path.join(self.workspace_path, "skills")
        if os.path.isdir(skills_dir):
            for entry in sorted(os.listdir(skills_dir)):
                entry_path = os.path.join(skills_dir, entry)
                if os.path.isdir(entry_path):
                    skill_file = os.path.join(entry_path, "SKILL.md")
                    if os.path.isfile(skill_file):
                        self._parse_and_register_skill(skill_file, is_global=False)

        return self.markdown_skills

    def _parse_and_register_skill(self, filepath: str, is_global: bool = False) -> None:
        """Parse SKILL.md and register it as a Pydantic tool."""
        from pathlib import Path
        resolved_path = Path(filepath).resolve()

        local_skills_dir = Path(self.workspace_path) / "skills"
        global_skills_dir = Path(os.path.expanduser("~")) / ".gemini" / "antigravity" / "skills"

        is_allowed = False
        try:
            resolved_path.relative_to(local_skills_dir.resolve())
            is_allowed = True
        except ValueError:
            pass

        try:
            resolved_path.relative_to(global_skills_dir.resolve())
            is_allowed = True
        except ValueError:
            pass

        import tempfile
        try:
            temp_dir = Path(tempfile.gettempdir()).resolve()
            resolved_path.relative_to(temp_dir)
            is_allowed = True
        except ValueError:
            pass

        if not is_allowed:
            raise PermissionError("Directory traversal warning: Access denied outside skill directories")

        try:
            with open(filepath, "r", encoding="utf-8") as file:
                raw = file.read()
        except (OSError, IOError):
            return

        frontmatter, body = self._split_frontmatter(raw)
        
        # Extract metadata
        name = str(frontmatter.get("name", os.path.basename(os.path.dirname(filepath)))).replace("-", "_")
        description = str(frontmatter.get("description", f"Markdown skill for {name}")).strip()
        triggers = frontmatter.get("triggers", [])
        
        if triggers:
            description += f"\n\nTriggers: {', '.join(triggers)}"

        # Generate dynamic Pydantic model for arguments
        # Since this is a markdown skill, it might not need structured arguments, 
        # but we give it a simple intent parameter to fulfill the function signature.
        ArgsModel = create_model(
            f"{name.capitalize()}Args",
            intent=(str, Field(default="", description="The specific intent or question when invoking this skill."))
        )

        # Generate dynamic Python function
        def dynamic_skill_func(args: ArgsModel) -> str:
            response = [
                f"=== Loaded Skill Instructions: {name} ===",
                f"Intent: {args.intent}",
                "",
                "Please read the following instructions and execute the task accordingly:",
                "---",
                body.strip(),
                "---",
            ]
            return "\n".join(response)

        # Set docstring for inspection
        dynamic_skill_func.__doc__ = description
        dynamic_skill_func.__name__ = name

        self.markdown_skills[name] = {
            "function": dynamic_skill_func,
            "args_model": ArgsModel,
            "description": description,
            "schema": ArgsModel.model_json_schema(),
            "wants_context": False,
            "is_markdown_skill": True, # Flag to distinguish from Python skills
            "is_global_skill": is_global, # Track global skills
        }

    @staticmethod
    def _split_frontmatter(raw_text: str) -> tuple[dict[str, Any], str]:
        """Split YAML front matter from a Markdown body."""
        if not raw_text.startswith("---"):
            return {}, raw_text

        parts = raw_text.split("---", 2)
        if len(parts) < 3:
            return {}, raw_text

        try:
            parsed = yaml.safe_load(parts[1]) or {}
            frontmatter = parsed if isinstance(parsed, dict) else {}
        except yaml.YAMLError:
            # Fallback to simple parse if yaml fails
            frontmatter = SkillLoader._parse_simple_frontmatter(parts[1])

        return frontmatter, parts[2]

    @staticmethod
    def _parse_simple_frontmatter(raw_frontmatter: str) -> dict[str, Any]:
        """Parse simple key/value front matter when PyYAML fails."""
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
