"""Unit and integration tests for LAS Phase 84 (P5 Developer Beta & Packaging).

Validates CLI subcommands (status, onboard, init, benchmark, pipeline), TargetRepoOnboarder,
packaging configuration in pyproject.toml, and backward compatibility with legacy flags.
"""

from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from agent_workspace.cli import (
    handle_benchmark,
    handle_init,
    handle_onboard,
    handle_status,
    main,
)
from agent_workspace.core.onboarding import OnboardingRecommendation, TargetRepoOnboarder


class TestDeveloperBetaP5(unittest.TestCase):
    """Test suite for Developer Beta CLI toolbelt, onboarding wizard, and packaging."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp(prefix="las_test_p5_")
        self.addCleanup(lambda: shutil.rmtree(self.temp_dir, ignore_errors=True))

    def _init_git_repo(self, path: Path) -> None:
        """Helper to initialize a bare-bones git repository for testing."""
        subprocess.run(["git", "init"], cwd=str(path), capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=str(path), capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "test@las.local"], cwd=str(path), capture_output=True, check=True)
        (path / "README.md").write_text("# Test Repo\n", encoding="utf-8")
        subprocess.run(["git", "add", "README.md"], cwd=str(path), capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=str(path), capture_output=True, check=True)

    def test_packaging_pyproject_toml_structure(self) -> None:
        """Verifies pyproject.toml contains standard PEP 517/621 entrypoints and dependencies."""
        pyproject_path = Path(__file__).resolve().parent.parent.parent / "pyproject.toml"
        self.assertTrue(pyproject_path.exists(), "pyproject.toml must exist at repo root")

        content = pyproject_path.read_text(encoding="utf-8")
        self.assertIn("[build-system]", content)
        self.assertIn("[project]", content)
        self.assertIn('name = "llm-agent-system"', content)
        self.assertIn("[project.scripts]", content)
        self.assertIn('las = "agent_workspace.cli:main"', content)
        self.assertIn('las-server = "agent_workspace.server:main"', content)
        self.assertIn('las-benchmark = "scripts.run_golden_benchmark:main"', content)

    def test_cli_help_output(self) -> None:
        """Verifies las --help outputs core subcommands."""
        stdout_capture = io.StringIO()
        with patch.object(sys, "argv", ["las", "--help"]), patch("sys.stdout", stdout_capture):
            main()

        output = stdout_capture.getvalue()
        self.assertIn("Core Subcommands:", output)
        self.assertIn("init [path]", output)
        self.assertIn("onboard [path]", output)
        self.assertIn("pipeline run", output)
        self.assertIn("benchmark", output)
        self.assertIn("serve", output)
        self.assertIn("status [path]", output)

    def test_cli_status_command(self) -> None:
        """Verifies las status command inspects current workspace and prints status."""
        stdout_capture = io.StringIO()
        args = MagicMock()
        args.path = str(Path(__file__).resolve().parent.parent.parent)

        with patch("sys.stdout", stdout_capture):
            handle_status(args)

        output = stdout_capture.getvalue()
        self.assertIn("LAS Developer Control Plane Status", output)
        self.assertIn("Workspace Path", output)
        self.assertIn("Protocol Baseline", output)
        self.assertIn("Git Branch", output)

    def test_cli_init_protocol_v380_scaffolding(self) -> None:
        """Verifies las init scaffolds Protocol v3.8.0 configuration files in target directory."""
        target_path = Path(self.temp_dir) / "test_init_repo"
        target_path.mkdir(parents=True, exist_ok=True)
        self._init_git_repo(target_path)

        args = MagicMock()
        args.path = str(target_path)
        args.dry_run = False
        args.force = False

        stdout_capture = io.StringIO()
        with patch("sys.stdout", stdout_capture):
            handle_init(args)

        output = stdout_capture.getvalue()
        self.assertIn("Initialized Protocol v3.8.0 workspace", output)

        # Verify scaffolded files
        self.assertTrue((target_path / "AGENTS.md").exists())
        self.assertTrue((target_path / ".agent" / "state.md").exists())
        self.assertTrue((target_path / ".agent" / "ownership.md").exists())
        self.assertTrue((target_path / ".agent" / "test_policy.md").exists())
        self.assertTrue((target_path / ".agent" / "task_environment.json").exists())

        # Verify Protocol baseline version
        state_content = (target_path / ".agent" / "state.md").read_text(encoding="utf-8")
        self.assertIn("Protocol Baseline: 3.8.0", state_content)

    def test_target_repo_onboarder_analysis_python(self) -> None:
        """Verifies TargetRepoOnboarder detects Python pytest ecosystem."""
        repo_path = Path(self.temp_dir) / "python_project"
        repo_path.mkdir(parents=True, exist_ok=True)
        self._init_git_repo(repo_path)

        # Add python indicators
        (repo_path / "pyproject.toml").write_text('[project]\nname = "demo"\n', encoding="utf-8")
        (repo_path / "tests").mkdir()
        (repo_path / "tests" / "test_demo.py").write_text("def test_ok(): pass\n", encoding="utf-8")
        (repo_path / ".env").write_text("SECRET=123\n", encoding="utf-8")

        onboarder = TargetRepoOnboarder(repo_path)
        rec: OnboardingRecommendation = onboarder.analyze()

        self.assertEqual(rec.primary_ecosystem, "python")
        self.assertIn("python", rec.detected_ecosystems)
        self.assertIn("pytest", rec.recommended_test_command)
        self.assertIn(".env*", rec.protected_scopes)
        self.assertEqual(rec.recommended_role, "DOMAIN_LOGIC_AGENT")

    def test_cli_onboard_json_format(self) -> None:
        """Verifies las onboard --format json outputs well-formed JSON specification."""
        repo_path = Path(self.temp_dir) / "json_project"
        repo_path.mkdir(parents=True, exist_ok=True)
        self._init_git_repo(repo_path)

        args = MagicMock()
        args.path = str(repo_path)
        args.no_scaffold = True
        args.force = False
        args.format = "json"

        stdout_capture = io.StringIO()
        with patch("sys.stdout", stdout_capture):
            handle_onboard(args)

        output = stdout_capture.getvalue()
        data = json.loads(output)
        self.assertEqual(data["target_path"], str(repo_path))
        self.assertTrue(data["is_git_repository"])
        self.assertIn("recommendation", data)
        self.assertIn("primary_ecosystem", data["recommendation"])

    def test_cli_benchmark_dispatcher(self) -> None:
        """Verifies handle_benchmark dispatches GoldenFlowBenchmarkEngine and outputs table."""
        from agent_workspace.core.pipeline.benchmark import (
            GoldenBenchmarkScorecard,
            ScenarioExecutionReceipt,
        )

        mock_scorecard = GoldenBenchmarkScorecard(
            suite_id="SUITE-P5-TEST",
            timestamp="2026-09-13T00:00:00Z",
            total_scenarios=1,
            successful_scenarios=1,
            mission_completion_rate=1.0,
            avg_time_to_verified_completion_ms=123.45,
            total_scope_violations_blocked=0,
            scope_containment_rate=1.0,
            review_freshness_verified=True,
            canonical_host_preservation_pass=True,
            context_token_efficiency_kb=15.2,
            scenario_receipts=[
                ScenarioExecutionReceipt(
                    scenario_id="HAPPY_PATH_FEATURE",
                    name="Happy Path Feature",
                    success=True,
                    stage_reached="COMPLETED",
                    duration_ms=123.45,
                    merkle_root="abc12345",
                    canonical_preserved=True,
                    scope_violations_blocked=0,
                    test_ladder_passed=True,
                    test_ladder_receipts_count=1,
                    draft_pr_generated=True,
                )
            ],
            advisory_verdict="GOLDEN_FLOW_VERIFIED",
        )

        args = MagicMock()
        args.scenarios = "HAPPY_PATH_FEATURE"
        args.output_json = None
        args.verbose = False

        stdout_capture = io.StringIO()
        with patch("agent_workspace.core.pipeline.benchmark.GoldenFlowBenchmarkEngine.run_benchmark", return_value=mock_scorecard):
            with patch("sys.stdout", stdout_capture):
                handle_benchmark(args)

        output = stdout_capture.getvalue()
        self.assertIn("LAS Golden Flow Benchmark Scorecard", output)
        self.assertIn("100.0%", output)
        self.assertIn("HAPPY_PATH_FEATURE", output)

    def test_cli_legacy_flag_backward_compatibility(self) -> None:
        """Verifies legacy flag routing (--list-skills) executes without crashing."""
        stdout_capture = io.StringIO()
        with patch.object(sys, "argv", ["las", "--list-skills"]), patch("sys.stdout", stdout_capture):
            main()

        output = stdout_capture.getvalue()
        self.assertIn("Skill ID", output)
        self.assertIn("Version", output)


if __name__ == "__main__":
    unittest.main()
