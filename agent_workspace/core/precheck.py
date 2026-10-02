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

    def check_anti_summary_preflight(self, inspected_files: list[str]) -> dict[str, Any]:
        """
        Anti-Summary Invariant (調研先行):
        Agents are strictly prohibited from generating architectural conclusions
        or code changes without inspecting primary source files.
        """
        if not inspected_files:
            return {
                "status": "BLOCKED",
                "message": "Anti-Summary violation: Primary source inspection required before planning or code changes. Citing concrete files is mandatory."
            }
        missing = []
        for f in inspected_files:
            fp = Path(f)
            if not fp.is_absolute():
                fp = self.workspace_path / fp
            if not fp.exists():
                missing.append(f)
        if missing:
            return {
                "status": "BLOCKED",
                "message": f"Anti-Summary violation: Specified primary source files do not exist: {', '.join(missing)}"
            }
        return {
            "status": "PASS",
            "message": f"Anti-Summary preflight verified across {len(inspected_files)} primary source files."
        }

    def check_stop_and_wait_gate(
        self, plan_approved: bool, approver_id: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Stop-and-Wait Architecture Gate:
        Enforces human approval before any file mutation tool or destructive change.
        Rejects agent self-approval.
        """
        if not plan_approved:
            return {
                "status": "BLOCKED",
                "message": "Stop-and-Wait Gate: Plan proposal requires explicit Human sign-off before modifying code.",
            }
        if approver_id:
            cleaned = approver_id.strip().lower()
            if cleaned.startswith("agent") or cleaned.startswith("bot"):
                return {
                    "status": "BLOCKED",
                    "message": f"Stop-and-Wait Gate: Self-approval rejected. Autonomous agent '{approver_id}' cannot approve execution plans.",
                }
        return {
            "status": "PASS",
            "message": "Stop-and-Wait Gate passed: Human sign-off confirmed.",
        }

    @staticmethod
    def check_seven_anti_corruption(code_text: str, filename: str = "") -> list[str]:
        """
        Seven Anti-Corruption static scanner:
        Checks for bare excepts, empty catch blocks, and swallowed exceptions.
        """
        issues = []
        if "except:" in code_text:
            issues.append("Anti-Corruption #4: Bare 'except:' detected. Typed failures only; catch specific exception classes.")
        if "catch (e) {}" in code_text or "catch (error) {}" in code_text:
            issues.append("Anti-Corruption #4: Empty catch block detected. Silently swallowing exceptions is prohibited.")
        if "except Exception:\n            pass" in code_text or "except Exception:\n        pass" in code_text:
            issues.append("Anti-Corruption #4: Swallowed Exception with 'pass' detected. Map to typed ErrorCode.")
        return issues
