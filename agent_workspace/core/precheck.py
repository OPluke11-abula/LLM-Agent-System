import os
import shutil
from pathlib import Path
from typing import Any
import yaml
import logging

logger = logging.getLogger("core.precheck")

class SkillsPrechecker:
    def __init__(self, workspace_path: str | Path) -> None:
        self.workspace_path = Path(workspace_path)

    def check_cli_dependencies(self, dependencies: list[str]) -> list[str]:
        """Check if CLI binaries are available in PATH."""
        missing = []
        for dep in dependencies:
            if not shutil.which(dep):
                missing.append(dep)
        return missing

    def check_credentials(self, env_vars: list[str]) -> dict[str, bool]:
        """Verify presence of required environment variables without exposing values."""
        status = {}
        for var in env_vars:
            status[var] = var in os.environ
        return status

    def run_precheck(self, tool_name: str, tool_func: Any = None) -> dict[str, Any]:
        """Run pre-checks for a tool based on its contract frontmatter and function attributes."""
        cli_deps = []
        required_env = []

        # 1. Check function attributes if provided
        if tool_func is not None:
            cli_deps.extend(getattr(tool_func, "cli_dependencies", []))
            required_env.extend(getattr(tool_func, "required_env_vars", []))

        # 2. Check YAML contract frontmatter
        # We need to support finding .agent/skills/ relative to project_root (parent of agent_workspace) or workspace_path
        # Let's try both paths
        paths_to_try = [
            self.workspace_path / ".agent" / "skills" / f"{tool_name}.md",
            self.workspace_path.parent / ".agent" / "skills" / f"{tool_name}.md",
        ]

        contract_path = None
        for p in paths_to_try:
            if p.is_file():
                contract_path = p
                break

        if contract_path:
            try:
                content = contract_path.read_text(encoding="utf-8")
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    fm = yaml.safe_load(parts[1]) or {}
                    if isinstance(fm, dict):
                        # Merge dependencies (de-duplicate)
                        for d in fm.get("cli_dependencies", []):
                            if isinstance(d, str) and d not in cli_deps:
                                cli_deps.append(d)
                        for e in fm.get("required_env_vars", []):
                            if isinstance(e, str) and e not in required_env:
                                required_env.append(e)
            except Exception as e:
                logger.warning("Failed to parse YAML frontmatter for tool %s: %s", tool_name, e)

        # 3. Perform the checks
        missing_cli = self.check_cli_dependencies(cli_deps)
        cred_status = self.check_credentials(required_env)
        missing_creds = [k for k, v in cred_status.items() if not v]

        if missing_cli or missing_creds:
            errors = []
            if missing_cli:
                errors.append(f"Missing external CLI dependency: {', '.join(missing_cli)}")
            if missing_creds:
                errors.append(f"Missing environment credentials: {', '.join(missing_creds)} (Please verify active OAuth/Connector)")

            return {
                "status": "BLOCKED",
                "message": "; ".join(errors)
            }

        return {
            "status": "PASS",
            "message": "Pre-check passed."
        }
