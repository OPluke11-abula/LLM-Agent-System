"""
Unit and Integration Tests for Autonomous Coding Pipeline Phase 83 (P4)
Official Golden Flow Benchmark & E2E Verification Harness
"""

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from agent_workspace.api import app
from agent_workspace.core.pipeline.benchmark import (
    BenchmarkScenarioId,
    GoldenBenchmarkScorecard,
    GoldenFlowBenchmarkEngine,
    ScenarioExecutionReceipt,
    create_golden_fixture_repo,
)


class TestPipelineBenchmarkP4(unittest.TestCase):
    """Verifies the Golden Flow Benchmark Engine, repository fixture, and ADR-006 KPI calculations."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="las_p4_test_")
        self.repo_path = create_golden_fixture_repo(os.path.join(self.temp_dir, "golden_repo"))
        self.engine = GoldenFlowBenchmarkEngine(
            base_worktrees_dir=os.path.join(self.temp_dir, "worktrees")
        )

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_golden_fixture_repo_scaffolding(self):
        """Verifies that the golden fixture repo is properly initialized with git and testable modules."""
        repo_p = Path(self.repo_path)
        self.assertTrue((repo_p / ".git").exists())
        self.assertTrue((repo_p / "src" / "math_service.py").exists())
        self.assertTrue((repo_p / "tests" / "test_math.py").exists())
        self.assertTrue((repo_p / ".gitignore").exists())

    def test_scenario_happy_path_feature(self):
        """Scenario 1: Verifies happy path feature addition with passing verification ladder and Draft PR."""
        scenarios = self.engine.build_default_scenarios(self.repo_path)
        s1 = next(s for s in scenarios if s.scenario_id == BenchmarkScenarioId.HAPPY_PATH_FEATURE)

        receipt = self.engine.run_scenario(s1, self.repo_path)
        self.assertTrue(receipt.success)
        self.assertEqual(receipt.stage_reached, "COMPLETED")
        self.assertTrue(receipt.test_ladder_passed)
        self.assertTrue(receipt.draft_pr_generated)
        self.assertTrue(receipt.canonical_preserved)
        self.assertIsNotNone(receipt.merkle_root)
        self.assertGreater(receipt.duration_ms, 0)

    def test_scenario_security_containment(self):
        """Scenario 2: Verifies physical ScopeGuard containment of unauthorized agent file mutations."""
        scenarios = self.engine.build_default_scenarios(self.repo_path)
        s2 = next(s for s in scenarios if s.scenario_id == BenchmarkScenarioId.SECURITY_CONTAINMENT)

        receipt = self.engine.run_scenario(s2, self.repo_path)
        self.assertTrue(receipt.success)  # Expected violation successfully caught
        self.assertEqual(receipt.scope_violations_blocked, 1)
        self.assertFalse(receipt.draft_pr_generated)
        self.assertTrue(receipt.canonical_preserved)

    def test_scenario_fail_fast_diagnostic(self):
        """Scenario 3: Verifies fail-fast ladder halting on regression and preventing false Draft PRs."""
        scenarios = self.engine.build_default_scenarios(self.repo_path)
        s3 = next(s for s in scenarios if s.scenario_id == BenchmarkScenarioId.FAIL_FAST_DIAGNOSTIC)

        receipt = self.engine.run_scenario(s3, self.repo_path)
        self.assertTrue(receipt.success)  # Successfully failed fast without false positive PR
        self.assertEqual(receipt.stage_reached, "FAILED")
        self.assertFalse(receipt.test_ladder_passed)
        self.assertFalse(receipt.draft_pr_generated)
        self.assertTrue(receipt.canonical_preserved)

    def test_benchmark_suite_scorecard_and_export(self):
        """Verifies full benchmark suite execution, 6 KPI calculations, and receipt export."""
        scorecard = self.engine.run_benchmark_suite(self.repo_path)

        self.assertEqual(scorecard.total_scenarios, 3)
        self.assertEqual(scorecard.successful_scenarios, 3)
        self.assertEqual(scorecard.mission_completion_rate, 1.0)
        self.assertEqual(scorecard.advisory_verdict, "GOLDEN_FLOW_VERIFIED")
        self.assertTrue(scorecard.canonical_host_preservation_pass)
        self.assertTrue(scorecard.review_freshness_verified)
        self.assertGreaterEqual(scorecard.total_scope_violations_blocked, 1)
        self.assertGreater(scorecard.avg_time_to_verified_completion_ms, 0)

        # Export test
        out_file = os.path.join(self.temp_dir, "receipt.json")
        saved_path = self.engine.export_receipt(scorecard, out_file)
        self.assertTrue(os.path.exists(saved_path))

        with open(saved_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["advisory_verdict"], "GOLDEN_FLOW_VERIFIED")
        self.assertEqual(len(data["scenario_receipts"]), 3)

    def test_benchmark_rest_api_endpoints(self):
        """Verifies POST /v1/pipeline/benchmark/run and GET /v1/pipeline/benchmark/latest endpoints."""
        client = TestClient(app)

        # 1. Trigger benchmark run
        res = client.post(f"/v1/pipeline/benchmark/run?repo_path={self.repo_path}")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["scorecard"]["mission_completion_rate"], 1.0)
        self.assertEqual(data["scorecard"]["advisory_verdict"], "GOLDEN_FLOW_VERIFIED")

        # 2. Query latest benchmark scorecard
        res_latest = client.get("/v1/pipeline/benchmark/latest")
        self.assertEqual(res_latest.status_code, 200)
        data_latest = res_latest.json()
        self.assertEqual(data_latest["status"], "success")
        self.assertEqual(data_latest["scorecard"]["mission_completion_rate"], 1.0)


if __name__ == "__main__":
    unittest.main()
