"""Target repository onboarding wizard and TaskEnvironment synthesizer for LAS (Phase 84 / P5).

Provides automated ecosystem analysis, verification command discovery, protected path
detection, and scaffolding of Protocol v3.8.0 configuration (.agent/) for any target repository.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field

from agent_workspace.core.repository import RepositoryInspector, RepositoryProfile, DEFAULT_PROTECTED_PATTERNS

logger = logging.getLogger(__name__)


class OnboardingRecommendation(BaseModel):
    """Recommended execution parameters synthesized for a target repository."""

    model_config = ConfigDict(extra="forbid")

    primary_ecosystem: str = Field("unknown", description="Primary detected language/ecosystem")
    detected_ecosystems: list[str] = Field(default_factory=list, description="All detected ecosystems")
    recommended_test_command: str = Field("python -m unittest discover", description="Primary test command for verification ladders")
    all_test_commands: list[str] = Field(default_factory=list, description="All discovered test commands")
    recommended_linter_command: Optional[str] = Field(None, description="Primary lint/format check command")
    default_mutable_scopes: list[str] = Field(default_factory=list, description="Recommended writable directory scopes")
    protected_scopes: list[str] = Field(default_factory=list, description="Files and paths strictly blocked from mutation")
    recommended_role: str = Field("DOMAIN_LOGIC_AGENT", description="Default assigned Grounded Role")
    max_turns: int = Field(3, description="Hard turn limit under Bounded Autonomy")


class OnboardingResult(BaseModel):
    """Complete result of repository onboarding and scaffolding."""

    model_config = ConfigDict(extra="forbid")

    target_path: str = Field(..., description="Absolute path to target repository")
    is_git_repository: bool = Field(..., description="Whether target directory is a valid git repo")
    current_branch: str = Field(..., description="Active branch name")
    head_commit: str = Field(..., description="Active commit hash")
    is_clean: bool = Field(..., description="Whether working tree is clean")
    recommendation: OnboardingRecommendation = Field(..., description="Synthesized onboarding recommendations")
    scaffolded_files: list[str] = Field(default_factory=list, description="Files created during scaffolding")
    onboarded_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class TargetRepoOnboarder:
    """Automated scanner and scaffolder connecting LAS to target repositories."""

    def __init__(self, target_path: str | Path) -> None:
        self.target_path = Path(target_path).resolve()
        self.inspector = RepositoryInspector()

    def analyze(self) -> OnboardingRecommendation:
        """Inspect target repository and infer recommended TaskEnvironment configuration."""
        profile: RepositoryProfile = self.inspector.inspect(str(self.target_path))

        detected = profile.detected_ecosystems
        primary = detected[0] if detected else "unknown"

        # Determine recommended test command
        all_tests: list[str] = []
        for cmd_dict in profile.test_commands:
            for _, cmd in cmd_dict.items():
                if cmd not in all_tests:
                    all_tests.append(cmd)

        primary_test = all_tests[0] if all_tests else (
            "pytest" if primary == "python" else (
                "npm test" if primary == "node" else (
                    "cargo test" if primary == "rust" else (
                        "go test ./..." if primary == "go" else "echo 'No test command configured'"
                    )
                )
            )
        )

        # Determine recommended linter command
        primary_linter: Optional[str] = None
        if profile.linter_commands:
            for _, cmd in profile.linter_commands[0].items():
                primary_linter = cmd
                break

        # Determine default mutable scopes based on repository structure
        mutable_scopes: list[str] = []
        candidates = ["src", "lib", "app", "pkg", "core", "tests", "test"]
        for c in candidates:
            if (self.target_path / c).is_dir():
                mutable_scopes.append(f"{c}/**")

        if not mutable_scopes:
            mutable_scopes = ["src/**", "tests/**"]

        # Protected scopes
        protected = list(profile.protected_paths)
        additional_protected = [".agent/state.md", ".agent/ownership.md", ".github/**"]
        for p in additional_protected:
            if p not in protected:
                protected.append(p)

        return OnboardingRecommendation(
            primary_ecosystem=primary,
            detected_ecosystems=detected,
            recommended_test_command=primary_test,
            all_test_commands=all_tests,
            recommended_linter_command=primary_linter,
            default_mutable_scopes=mutable_scopes,
            protected_scopes=protected,
            recommended_role="DOMAIN_LOGIC_AGENT",
            max_turns=3,
        )

    def onboard(self, scaffold: bool = True, force: bool = False) -> OnboardingResult:
        """Perform full repository analysis and optionally scaffold Protocol v3.8.0 configuration."""
        profile = self.inspector.inspect(str(self.target_path))
        rec = self.analyze()

        scaffolded: list[str] = []
        if scaffold:
            scaffolded = self._scaffold_protocol_files(rec, force=force)

        return OnboardingResult(
            target_path=str(self.target_path),
            is_git_repository=profile.head_commit != "0" * 40,
            current_branch=profile.current_branch,
            head_commit=profile.head_commit,
            is_clean=profile.is_clean,
            recommendation=rec,
            scaffolded_files=scaffolded,
        )

    def _scaffold_protocol_files(self, rec: OnboardingRecommendation, force: bool = False) -> list[str]:
        """Generate standard Protocol v3.8.0 directory and configuration files."""
        agent_dir = self.target_path / ".agent"
        created_files: list[str] = []

        agent_dir.mkdir(parents=True, exist_ok=True)
        (agent_dir / "evidence").mkdir(parents=True, exist_ok=True)
        (agent_dir / "patches").mkdir(parents=True, exist_ok=True)

        files_to_create: dict[Path, str] = {
            self.target_path / "AGENTS.md": """# Project Agent Entry Point (AGENTS.md)

**Canonical Coordination Workspace**: `.agent/`
**Required Protocol Version**: `3.8.0` (`Universal_Coding_Agent_Development_Protocol.md`)

Use this file as the thin, authoritative entry point for all collaborating coding agents.

## Core Operational Invariants
1. **Anti-Summary Invariant**: Always inspect concrete primary source files before modifying code.
2. **Stop-and-Wait Architecture Gate**: Propose diff plan, target files, and wait for human approval.
3. **Seven Universal Anti-Corruption Principles**: Zero dead code, single responsibility, concurrency elimination, typed failures only.
""",
            agent_dir / "state.md": f"""# Protocol State & Baseline
Protocol Baseline: 3.8.0
Coordination Mode: STATIC_DOMAIN_OWNERSHIP
Repository: {self.target_path.name}
Primary Ecosystem: {rec.primary_ecosystem}
Initialized At: {datetime.now(timezone.utc).isoformat()}
""",
            agent_dir / "ownership.md": f"""# Feature-Based Ownership & Mutable Boundary Matrix

| Grounded Role | Mutable Scope | Protected Scope |
|---|---|---|
| `DOMAIN_LOGIC_AGENT` | `{", ".join(rec.default_mutable_scopes)}` | `{", ".join(rec.protected_scopes[:3])}` |
| `UI_UX_AGENT` | `viewer/**`, `frontend/**`, `ui/**` | `src/**`, `core/**`, `backend/**` |
| `BACKEND_INFRA_AGENT` | `server/**`, `infra/**`, `api/**` | `viewer/**`, `frontend/**` |
| `QA_TEST_AGENT` | `tests/**`, `test/**` | `src/**`, `app/**` |
""",
            agent_dir / "test_policy.md": f"""# Verification Test Policy

## Verification Ladder
1. **Primary Test Suite**: `{rec.recommended_test_command}`
2. **Objective Status Requirements**: All verification commands must return exit code 0 (`PASS`).
""",
            agent_dir / "task_environment.json": json.dumps(
                {
                    "primary_ecosystem": rec.primary_ecosystem,
                    "recommended_test_command": rec.recommended_test_command,
                    "all_test_commands": rec.all_test_commands,
                    "default_mutable_scopes": rec.default_mutable_scopes,
                    "protected_scopes": rec.protected_scopes,
                    "recommended_role": rec.recommended_role,
                    "max_turns": rec.max_turns,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                },
                indent=2,
            ),
        }

        for path, content in files_to_create.items():
            if not path.exists() or force:
                path.write_text(content, encoding="utf-8")
                created_files.append(str(path.relative_to(self.target_path)))

        return created_files
