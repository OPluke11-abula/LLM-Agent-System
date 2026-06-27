from agent_workspace.core.engine import AgentEngine
from agent_workspace.core.router import AgentRouter
from unittest.mock import MagicMock, patch

import pytest


def test_router_builds_conductor_plan_without_changing_tool_allowlist(tmp_path):
    agent_dir = tmp_path / ".agent"
    agent_dir.mkdir(parents=True)
    (agent_dir / "agent.md").write_text(
        "---\nauthorization_level: standard\ntools:\n  - calculate\n  - run_tests\n---\n",
        encoding="utf-8",
    )
    (tmp_path / "config.yaml").write_text("agent:\n  max_iterations: 5\n  max_tool_calls: 15\n", encoding="utf-8")

    engine = AgentEngine(workspace_path=str(tmp_path), bypass_onboarding=True)
    router = AgentRouter(engine, session_id="s1", agent_name="tester")

    resolved_tools = router._resolve_allowed_tools(["calculate", "unknown"])
    plan = router._build_conductor_plan(
        user_input="Please run tests after changing router telemetry.",
        task_type="compilation",
        intent="TASK",
        resolved_tools=resolved_tools,
        selected_account={
            "id": "primary",
            "provider": "google-genai",
            "model": "gemini-2.5-flash",
        },
    )

    assert resolved_tools == ["calculate"]
    assert plan.tool_allowlist == ["calculate"]
    assert plan.task_type == "compilation"
    assert plan.execution_mode == "pro"
    assert router.last_conductor_plan is plan


@pytest.mark.asyncio
async def test_router_persists_route_outcome_after_agent_loop(tmp_path):
    agent_dir = tmp_path / ".agent"
    agent_dir.mkdir(parents=True)
    (agent_dir / "agent.md").write_text(
        "---\nauthorization_level: standard\ntools:\n  - calculate\n  - run_tests\n---\n",
        encoding="utf-8",
    )
    (tmp_path / "config.yaml").write_text(
        "agent:\n  max_iterations: 5\n  max_tool_calls: 15\nmemory:\n  long_term_enabled: true\n  backend: sqlite\n",
        encoding="utf-8",
    )

    engine = AgentEngine(workspace_path=str(tmp_path), bypass_onboarding=True)
    mock_provider = MagicMock()

    with patch("agent_workspace.core.router.ProviderFactory.get_provider", return_value=mock_provider):
        router = AgentRouter(engine, session_id="s-outcome", agent_name="tester")

        async def fake_internal(user_input, allowed_tools=None, output_schema=None, account_id=None):
            router.last_conductor_plan = router._build_conductor_plan(
                user_input=user_input,
                task_type="compilation",
                intent="TASK",
                resolved_tools=["run_tests"],
                selected_account={
                    "id": "primary",
                    "provider": "google-genai",
                    "model": "gemini-2.5-flash",
                },
            )
            router.total_tokens = 321
            return "completed"

        router._run_agent_loop_internal = fake_internal
        try:
            result = await router.run_agent_loop("Run a focused router test")
            records = router.long_term_memory.all_records()
        finally:
            router.close()

    assert result == "completed"
    outcome_records = [record for record in records if record.get("source") == "routing_outcome"]
    assert len(outcome_records) == 1
    outcome = outcome_records[0]
    assert outcome["payload"]["success"] is True
    assert outcome["payload"]["token_count"] == 321
    assert outcome["payload"]["task_type"] == "compilation"
    assert outcome["payload"]["human_intervention_count"] == 0
