from agent_workspace.core.engine import AgentEngine
from agent_workspace.core.router import AgentRouter


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
