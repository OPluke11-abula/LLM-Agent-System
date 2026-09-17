"""Swarm Engine & Policy Gate Integration Test Suite (Phase 92 / GAP-01).

Validates that:
1. AgentEngine.execute_tool evaluates UnifiedPolicyGate before executing tools.
2. Role boundary restrictions (ROLE_SCOPE_RESTRICTIONS) block unauthorized cross-boundary mutations.
3. Reviewer roles (QA_TEST_AGENT, etc.) are strictly prohibited from write actions.
4. Resources escaping workspace scope are rejected.
5. Authorized tool invocations succeed and synchronously log policy decisions to AuditLedger.
"""

from pathlib import Path
import tempfile
import unittest
from pydantic import BaseModel, Field

from agent_workspace.core.audit_ledger import AuditLedger
from agent_workspace.core.engine import AgentEngine


class FileWriteArgs(BaseModel):
    target_file: str = Field(description="Target file path")
    content: str = Field(description="Content to write")


class CalculatorArgs(BaseModel):
    x: int
    y: int


class TestEnginePolicyIntegration(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace_path = Path(self.temp_dir.name).resolve()

        # Create basic directory structure
        (self.workspace_path / "src").mkdir(parents=True)
        (self.workspace_path / "agent_workspace").mkdir(parents=True)
        (self.workspace_path / "viewer").mkdir(parents=True)

        # Initialize AgentEngine
        self.engine = AgentEngine(workspace_path=str(self.workspace_path), bypass_onboarding=True)

        # Register custom test tools in the engine
        def mock_file_writer(args: FileWriteArgs) -> str:
            target = (self.workspace_path / args.target_file).resolve()
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(args.content, encoding="utf-8")
            return f"WROTE:{args.target_file}"

        def mock_calc(args: CalculatorArgs) -> str:
            return str(args.x + args.y)

        self.engine.tools_registry["filesystem_write"] = {
            "function": mock_file_writer,
            "args_model": FileWriteArgs,
            "description": "Writes file content to workspace",
            "schema": FileWriteArgs.model_json_schema(),
            "wants_context": False,
            "is_markdown_skill": False,
        }

        self.engine.tools_registry["calculate"] = {
            "function": mock_calc,
            "args_model": CalculatorArgs,
            "description": "Calculates sum of two numbers",
            "schema": CalculatorArgs.model_json_schema(),
            "wants_context": False,
            "is_markdown_skill": False,
        }

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_engine_blocks_ui_agent_from_backend_boundary(self):
        """UI_UX_AGENT attempting to write to agent_workspace/ must be denied by PolicyGate."""
        context = {
            "session_id": "session-swarm-1",
            "agent_role": "UI_UX_AGENT",
        }
        with self.assertRaises(PermissionError) as ctx:
            self.engine.execute_tool(
                tool_name="filesystem_write",
                arguments={"target_file": "agent_workspace/backend.py", "content": "# forbidden"},
                context=context,
            )
        self.assertIn("Boundary violation", str(ctx.exception))
        self.assertIn("UI_UX_AGENT", str(ctx.exception))

    def test_engine_blocks_reviewer_role_from_writing(self):
        """Reviewer roles (QA_TEST_AGENT) must be rejected on file write operations."""
        context = {
            "session_id": "session-swarm-2",
            "agent_role": "QA_TEST_AGENT",
        }
        with self.assertRaises(PermissionError) as ctx:
            self.engine.execute_tool(
                tool_name="filesystem_write",
                arguments={"target_file": "src/feature.py", "content": "# qa edit"},
                context=context,
            )
        self.assertIn("read-only", str(ctx.exception).lower())

    def test_engine_blocks_path_traversal_outside_workspace(self):
        """Path attempting traversal outside workspace must be blocked."""
        context = {
            "session_id": "session-swarm-3",
            "agent_role": "DOMAIN_LOGIC_AGENT",
        }
        with self.assertRaises(PermissionError) as ctx:
            self.engine.execute_tool(
                tool_name="filesystem_write",
                arguments={"target_file": "../../../escaped.py", "content": "# escape"},
                context=context,
            )
        self.assertIn("outside workspace", str(ctx.exception).lower())

    def test_engine_allows_authorized_role_modification(self):
        """Authorized developer role modifying allowed path succeeds and persists."""
        context = {
            "session_id": "session-swarm-4",
            "agent_role": "DOMAIN_LOGIC_AGENT",
        }
        res = self.engine.execute_tool(
            tool_name="filesystem_write",
            arguments={"target_file": "src/logic.py", "content": "def run(): pass\n"},
            context=context,
        )
        self.assertEqual(res, "WROTE:src/logic.py")
        self.assertTrue((self.workspace_path / "src" / "logic.py").exists())

    def test_engine_records_policy_decision_in_audit_ledger(self):
        """Every tool execution evaluated by PolicyGate must be recorded in AuditLedger."""
        context = {
            "session_id": "session-swarm-5",
            "agent_role": "DOMAIN_LOGIC_AGENT",
        }
        self.engine.execute_tool(
            tool_name="calculate",
            arguments={"x": 10, "y": 20},
            context=context,
        )

        ledger = AuditLedger(workspace_path=str(self.workspace_path))
        events = ledger.get_logs()
        self.assertGreater(len(events), 0)
        policy_event = next((e for e in events if e.get("event_type") == "policy_gate_decision"), None)
        self.assertIsNotNone(policy_event)
        self.assertEqual(policy_event["payload"]["actor"], "DOMAIN_LOGIC_AGENT")
        self.assertTrue(policy_event["payload"]["allowed"])


if __name__ == "__main__":
    unittest.main()
