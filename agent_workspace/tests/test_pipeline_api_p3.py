"""Unit and API integration tests for Phase 82 (P3: REST & WebSocket Gateways)."""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from agent_workspace.api import app
from agent_workspace.core.pipeline.models import (
    CodingTaskRequest,
    PipelineStage,
    ScopedMutationPlan,
    VerificationStatus,
)


class TestPipelineApiP3(unittest.TestCase):
    """Verifies the REST API contracts and Stop-and-Wait Gate enforcement for the Autonomous Coding Pipeline."""

    def setUp(self):
        self.client = TestClient(app)
        self.temp_repo = tempfile.mkdtemp(prefix="las_test_api_repo_")

        # 1. Initialize git repo
        subprocess.run(["git", "init", "-b", "main"], cwd=self.temp_repo, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "API Test Agent"], cwd=self.temp_repo, check=True)
        subprocess.run(["git", "config", "user.email", "agent@api.test"], cwd=self.temp_repo, check=True)

        # 2. Add an initial source file and .gitignore
        core_dir = os.path.join(self.temp_repo, "agent_workspace", "core")
        os.makedirs(core_dir, exist_ok=True)
        self.calc_file = os.path.join(core_dir, "calc.py")
        with open(self.calc_file, "w", encoding="utf-8") as f:
            f.write("def add(a, b):\n    return a + b\n")

        with open(os.path.join(self.temp_repo, ".gitignore"), "w", encoding="utf-8") as f:
            f.write(".agent/patches/\nagent_worktrees/\n")

        subprocess.run(["git", "add", "."], cwd=self.temp_repo, check=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=self.temp_repo, check=True)

    def tearDown(self):
        if os.path.exists(self.temp_repo):
            shutil.rmtree(self.temp_repo, ignore_errors=True)

    def test_create_pipeline_task_success(self):
        req_payload = {
            "task_id": "TASK-API-001",
            "repository_path": self.temp_repo,
            "requirement_prompt": "Implement subtract(a, b)",
            "base_branch": "main",
            "target_branch": "feat/subtract",
            "inspected_files": ["agent_workspace/core/calc.py"],
            "target_files": ["agent_workspace/core/calc.py"],
            "allowed_roles": ["DOMAIN_LOGIC_AGENT"],
        }
        res = self.client.post("/v1/pipeline/tasks", json=req_payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["task_id"], "TASK-API-001")
        self.assertEqual(data["stage"], PipelineStage.PRECHECK.value)

    def test_create_pipeline_task_anti_summary_violation(self):
        req_payload = {
            "task_id": "TASK-API-VIOLATION",
            "repository_path": self.temp_repo,
            "requirement_prompt": "Refactor everything without inspecting",
            "base_branch": "main",
            "target_branch": "feat/refactor",
            "inspected_files": [],  # Violates Anti-Summary Invariant (調研先行)
            "target_files": ["agent_workspace/core/calc.py"],
        }
        res = self.client.post("/v1/pipeline/tasks", json=req_payload)
        self.assertEqual(res.status_code, 400)
        data = res.json()
        self.assertIn("detail", data)

    def test_stop_and_wait_gate_full_lifecycle(self):
        task_id = "TASK-API-LIFECYCLE"
        # 1. Intake
        req_payload = {
            "task_id": task_id,
            "repository_path": self.temp_repo,
            "requirement_prompt": "Add multiply function",
            "base_branch": "main",
            "target_branch": "feat/multiply",
            "inspected_files": ["agent_workspace/core/calc.py"],
            "target_files": ["agent_workspace/core/calc.py"],
            "allowed_roles": ["DOMAIN_LOGIC_AGENT"],
        }
        res = self.client.post("/v1/pipeline/tasks", json=req_payload)
        self.assertEqual(res.status_code, 200)

        # 2. Submit plan with role scope violation -> 403
        bad_plan = {
            "task_id": task_id,
            "plan_summary": "UI Agent touches backend domain code",
            "target_files": ["agent_workspace/core/calc.py"],
            "assigned_role": "UI_UX_AGENT",  # Forbidden for core/
            "human_approved": False,
        }
        res = self.client.post(f"/v1/pipeline/tasks/{task_id}/plan", json=bad_plan)
        self.assertEqual(res.status_code, 403)

        # 3. Submit valid plan awaiting approval
        good_plan = {
            "task_id": task_id,
            "plan_summary": "Domain Logic Agent implements multiply",
            "target_files": ["agent_workspace/core/calc.py"],
            "assigned_role": "DOMAIN_LOGIC_AGENT",
            "human_approved": False,
            "test_strategy": ['python -c "import sys; sys.exit(0)"'],
        }
        res = self.client.post(f"/v1/pipeline/tasks/{task_id}/plan", json=good_plan)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["gate_status"], "AWAITING_APPROVAL")

        # 4. Attempt to execute without approval -> 403 STOP_AND_WAIT_GATE_LOCKED
        res = self.client.post(f"/v1/pipeline/tasks/{task_id}/execute")
        self.assertEqual(res.status_code, 403)
        self.assertIn("STOP_AND_WAIT_GATE_LOCKED", res.json()["detail"])

        # 5. Human-in-the-loop (HITL) approval
        approve_payload = {
            "approval_token": "LUKE_TOKEN_999",
            "approver": "Luke (Domain Owner)",
            "notes": "Architecture plan verified.",
        }
        res = self.client.post(f"/v1/pipeline/tasks/{task_id}/approve", json=approve_payload)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["gate_status"], "APPROVED")

        # 6. Execute pipeline
        res = self.client.post(f"/v1/pipeline/tasks/{task_id}/execute")
        self.assertEqual(res.status_code, 200)
        exec_data = res.json()["result"]
        self.assertEqual(exec_data["status"], VerificationStatus.PASS.value)
        self.assertEqual(exec_data["current_stage"], PipelineStage.COMPLETED.value)
        self.assertIsNotNone(exec_data["pr_payload"])

        # 7. Check events ledger and Merkle root
        res = self.client.get(f"/v1/pipeline/tasks/{task_id}/events")
        self.assertEqual(res.status_code, 200)
        events_data = res.json()
        self.assertEqual(events_data["chain_integrity"], True)
        self.assertEqual(len(events_data["merkle_root"]), 64)
        self.assertGreaterEqual(events_data["event_count"], 3)

        # 8. Check Canonical Preservation Receipt
        res = self.client.get(f"/v1/pipeline/tasks/{task_id}/preservation")
        self.assertEqual(res.status_code, 200)
        pres_data = res.json()
        self.assertEqual(pres_data["is_preserved"], True)

    def test_run_full_pipeline_endpoint(self):
        task_id = "TASK-API-RUN-CONVENIENCE"
        req = {
            "task_id": task_id,
            "repository_path": self.temp_repo,
            "requirement_prompt": "Quick verified addition check",
            "base_branch": "main",
            "target_branch": "feat/quick-check",
            "inspected_files": ["agent_workspace/core/calc.py"],
            "target_files": ["agent_workspace/core/calc.py"],
            "allowed_roles": ["DOMAIN_LOGIC_AGENT"],
        }
        plan = {
            "task_id": task_id,
            "plan_summary": "Pre-approved unit test plan",
            "target_files": ["agent_workspace/core/calc.py"],
            "assigned_role": "DOMAIN_LOGIC_AGENT",
            "human_approved": True,
            "approval_token": "PRE_APPROVED_CLI",
            "test_strategy": ['python -c "exit(0)"'],
        }

        res = self.client.post("/v1/pipeline/tasks/run", json={"request": req, "plan": plan})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["is_preserved"])
        self.assertEqual(data["result"]["status"], VerificationStatus.PASS.value)

    def test_list_and_get_tasks_endpoints(self):
        # 1. List tasks
        res = self.client.get("/v1/pipeline/tasks")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertIsInstance(data["tasks"], list)

        # 2. Get non-existent task -> 404
        res_404 = self.client.get("/v1/pipeline/tasks/NON_EXISTENT_999")
        self.assertEqual(res_404.status_code, 404)

    def test_pipeline_websocket(self):
        with self.client.websocket_connect("/v1/pipeline/ws") as ws:
            ws.send_text("ping")
            resp = ws.receive_text()
            self.assertEqual(resp, "pong")


if __name__ == "__main__":
    unittest.main()
