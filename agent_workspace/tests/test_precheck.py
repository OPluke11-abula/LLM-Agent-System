import os
import sys
import pytest
import shutil
import yaml
import json
import asyncio
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

from agent_workspace.core.precheck import SkillsPrechecker
from agent_workspace.core.engine import AgentEngine
from agent_workspace.core.router import AgentRouter
from agent_workspace.tool_manifest import scan_secrets, generate_matrix


@pytest.fixture
def temp_workspace(tmp_path):
    """Set up a temporary workspace directory structure."""
    os.makedirs(tmp_path / ".agent" / "skills", exist_ok=True)
    os.makedirs(tmp_path / "agent_workspace", exist_ok=True)
    return tmp_path


def test_prechecker_cli_check(temp_workspace):
    prechecker = SkillsPrechecker(temp_workspace)

    # Test checking for git (which should exist on any dev machine)
    missing = prechecker.check_cli_dependencies(["git"])
    assert len(missing) == 0 or not shutil.which("git")

    # Test checking for non-existent tool
    missing = prechecker.check_cli_dependencies(["nonexistent-tool-xyz-123"])
    assert missing == ["nonexistent-tool-xyz-123"]


def test_prechecker_credentials(temp_workspace):
    prechecker = SkillsPrechecker(temp_workspace)

    # Set mock variables in os.environ
    os.environ["MOCK_TEST_CRED"] = "secret123"
    try:
        status = prechecker.check_credentials(["MOCK_TEST_CRED", "MISSING_TEST_CRED"])
        assert status["MOCK_TEST_CRED"] is True
        assert status["MISSING_TEST_CRED"] is False
    finally:
        os.environ.pop("MOCK_TEST_CRED", None)


def test_prechecker_run_precheck_with_contract(temp_workspace):
    prechecker = SkillsPrechecker(temp_workspace)

    # Create a mock contract md file
    contract_content = """---
id: test_tool
name: test_tool
description: A mock tool description.
version: 1.0.0
cli_dependencies:
  - nonexistent-tool-xyz-123
required_env_vars:
  - REQUIRED_MOCK_ENV_VAR
safety_notes:
  - This is a test note.
---
# test_tool
    """
    contract_path = temp_workspace / ".agent" / "skills" / "test_tool.md"
    contract_path.write_text(contract_content, encoding="utf-8")

    # 1. Test when credentials and dependencies are missing
    res = prechecker.run_precheck("test_tool")
    assert res["status"] == "BLOCKED"
    assert "Missing external CLI dependency: nonexistent-tool-xyz-123" in res["message"]
    assert "Missing environment credentials: REQUIRED_MOCK_ENV_VAR" in res["message"]

    # 2. Test fallback function attributes
    def dummy_func():
        pass
    dummy_func.cli_dependencies = ["git"]
    dummy_func.required_env_vars = ["MOCK_TEST_CRED_ATTR"]

    os.environ["MOCK_TEST_CRED_ATTR"] = "somevalue"
    try:
        res = prechecker.run_precheck("another_tool", dummy_func)
        # Assuming git is available, res should only block on nonexistent tools or pass if none are missing
        if shutil.which("git"):
            assert res["status"] == "PASS"
    finally:
        os.environ.pop("MOCK_TEST_CRED_ATTR", None)


def test_engine_executes_tool_precheck_interception(temp_workspace):
    # Setup configuration yaml file
    config_path = temp_workspace / "config.yaml"
    config_path.write_text("memory:\n  backend: sqlite\n  long_term_enabled: false\n", encoding="utf-8")

    engine = AgentEngine(workspace_path=str(temp_workspace), bypass_onboarding=True)

    # Mock prechecker response to be BLOCKED
    engine.prechecker.run_precheck = MagicMock(return_value={
        "status": "BLOCKED",
        "message": "Blocked by test mockup precheck."
    })

    # Register mock tool in registry
    from pydantic import BaseModel, Field
    class MockArgs(BaseModel):
        input_val: str

    def mock_tool_func(args: MockArgs) -> str:
        return "Executed successfully"

    engine.tools_registry["mock_tool"] = {
        "function": mock_tool_func,
        "args_model": MockArgs,
        "description": "Mock tool.",
        "schema": MockArgs.model_json_schema(),
        "wants_context": False,
        "is_markdown_skill": False
    }

    # Execute tool should be intercepted and return BLOCKED payload
    res = engine.execute_tool("mock_tool", {"input_val": "hello"})
    parsed = json.loads(res)
    assert parsed["status"] == "BLOCKED"
    assert "Blocked by test mockup precheck." in parsed["message"]


@pytest.mark.asyncio
async def test_router_loop_continuation_approval(temp_workspace):
    # Setup configuration yaml file
    config_path = temp_workspace / "config.yaml"
    config_path.write_text("agent:\n  max_iterations: 5\n", encoding="utf-8")

    # Create empty agent.md
    agent_md = temp_workspace / ".agent" / "agent.md"
    agent_md.write_text("---\nauthorization_level: standard\nmin_runtime_version: 0.1.0\ntools:\n  - mock_tool\n---\n", encoding="utf-8")

    # Create dummy agent.jinja2
    agent_jinja = temp_workspace / "agent.jinja2"
    agent_jinja.write_text("Mock prompt: {{ user_input }}", encoding="utf-8")

    engine = AgentEngine(workspace_path=str(temp_workspace), bypass_onboarding=True)
    router = AgentRouter(engine, session_id="test-loop-session", agent_name="loop_tester")

    # Mock generate_content to return tool calls so it cycles the loop
    mock_provider = AsyncMock()
    mock_provider.generate_content.side_effect = [
        ("tool_call", {"name": "mock_tool", "arguments": {"input_val": "hello"}}),  # Iteration 1
        ("tool_call", {"name": "mock_tool", "arguments": {"input_val": "hello"}}),  # Iteration 2
        ("tool_call", {"name": "mock_tool", "arguments": {"input_val": "hello"}}),  # Iteration 3
        ("text", "Done!"),  # If approved, finishes in iteration 4
    ]
    router._provider = mock_provider
    router._classify_intent = AsyncMock(return_value="TASK")

    # Mock tool registry
    from pydantic import BaseModel
    class MockArgs(BaseModel):
        input_val: str

    def mock_tool_func(args: MockArgs) -> str:
        return "Success"

    engine.tools_registry["mock_tool"] = {
        "function": mock_tool_func,
        "args_model": MockArgs,
        "description": "Mock.",
        "schema": MockArgs.model_json_schema(),
        "wants_context": False,
        "is_markdown_skill": False
    }

    # Setup test env variable to enforce loop approval check
    os.environ["TEST_LOOP_APPROVAL"] = "1"
    try:
        with patch("agent_workspace.core.providers.ProviderFactory.get_provider", return_value=mock_provider):
            # Scenario A: User denies approval at iteration 3
            with patch.object(router, "_wait_for_approval", new_callable=AsyncMock) as mock_wait:
                mock_wait.return_value = False

                res = await router.run_agent_loop("test loop gate", allowed_tools=["mock_tool"])
                assert "Error: Loop continuation denied by user after 3 iterations." in res
                assert mock_wait.call_count == 1

            # Scenario B: User grants approval at iteration 3
            mock_provider.generate_content.side_effect = [
                ("tool_call", {"name": "mock_tool", "arguments": {"input_val": "hello"}}),  # Iteration 1
                ("tool_call", {"name": "mock_tool", "arguments": {"input_val": "hello"}}),  # Iteration 2
                ("tool_call", {"name": "mock_tool", "arguments": {"input_val": "hello"}}),  # Iteration 3
                ("text", "Done!"),  # Approved, iteration 4 finishes
            ]
            with patch.object(router, "_wait_for_approval", new_callable=AsyncMock) as mock_wait:
                mock_wait.return_value = True
                res = await router.run_agent_loop("test loop gate", allowed_tools=["mock_tool"])
                assert "Done!" in res
                assert mock_wait.call_count == 2
    finally:
        os.environ.pop("TEST_LOOP_APPROVAL", None)


def test_secrets_scanning_and_matrix_generation(temp_workspace):
    # 1. Test secrets scanner detects hardcoded credentials
    secret_file = temp_workspace / "secret_file.py"
    # Hardcoded fake key
    secret_file.write_text("api_key = \"sk-123456789012345678901234567890123456789012345678\"\n", encoding="utf-8")

    # Mock files with test keywords should be skipped
    test_file = temp_workspace / "test_file.py"
    test_file.write_text("api_key = \"sk-mock-123456789012345678901234567890123456789012345678\"\n", encoding="utf-8")

    secrets = scan_secrets(temp_workspace)
    assert len(secrets) == 2
    assert any("FOUND_SECRET: Hardcoded OpenAI API Key" in s for s in secrets)

    # 2. Test matrix generation
    # Create configuration yaml file
    config_path = temp_workspace / "config.yaml"
    config_path.write_text("memory:\n  backend: sqlite\n  long_term_enabled: false\n", encoding="utf-8")

    # Create agent.md
    agent_md = temp_workspace / ".agent" / "agent.md"
    agent_md.write_text("---\nprotocol_version: 1.0.0\nmin_runtime_version: 0.1.0\ntools:\n  - mock_tool\n---\n", encoding="utf-8")

    engine = AgentEngine(workspace_path=str(temp_workspace), bypass_onboarding=True)
    from tool_manifest import ToolManifest
    manifest = ToolManifest.from_engine(engine)

    # Write empty contract doc
    contract_path = temp_workspace / ".agent" / "skills" / "mock_tool.md"
    contract_path.write_text("---\nid: mock_tool\nname: mock_tool\ndescription: Mock.\nversion: 1.0.0\ninputs: {}\noutputs: {}\nsafety_notes: []\n---\n", encoding="utf-8")

    # Add mock tool to manifest manually for testing
    from tool_manifest import ToolEntry
    manifest.tools = [ToolEntry(
        name="mock_tool",
        description="Mock.",
        module="mock_workspace",
        function="mock",
        input_schema={}
    )]

    report = generate_matrix(manifest, temp_workspace)
    assert "mock_tool" in report
    assert "PASS" in report or "BLOCKED" in report
