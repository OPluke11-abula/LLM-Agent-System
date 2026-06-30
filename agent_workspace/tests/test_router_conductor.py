from agent_workspace.core.engine import AgentEngine
from agent_workspace.core.router import AgentRouter
from unittest.mock import MagicMock, patch

import pytest


class RecordingSpan:
    def __init__(self):
        self.attributes = {}

    def set_attribute(self, key, value):
        self.attributes[key] = value


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


def test_router_builds_conductor_trace_event(tmp_path):
    (tmp_path / "config.yaml").write_text("agent:\n  max_iterations: 5\n  max_tool_calls: 15\n", encoding="utf-8")

    engine = AgentEngine(workspace_path=str(tmp_path), bypass_onboarding=True)
    router = AgentRouter(engine, session_id="s-trace", agent_name="tester")
    plan = router._build_conductor_plan(
        user_input="Please refine the UI trace panel.",
        task_type="ui_layout",
        intent="TASK",
        resolved_tools=["run_tests"],
        selected_account={
            "id": "primary",
            "provider": "google-genai",
            "model": "gemini-2.5-flash",
        },
    )

    event = router._conductor_trace_event(plan)

    assert event["type"] == "conductor_trace"
    assert event["session_id"] == "s-trace"
    assert event["trace"]["task_type"] == "ui_layout"
    assert event["trace"]["selected_models"][0]["selection_reason"]
    assert event["trace"]["verification_strategy"]["kind"] == "verifier"


def test_router_conductor_trace_and_span_include_workflow_metadata_when_present(tmp_path):
    (tmp_path / "config.yaml").write_text("agent:\n  max_iterations: 5\n  max_tool_calls: 15\n", encoding="utf-8")

    engine = AgentEngine(workspace_path=str(tmp_path), bypass_onboarding=True)
    router = AgentRouter(engine, session_id="s-workflow", agent_name="tester")
    plan = router._build_conductor_plan(
        user_input="Run an atomic workflow task.",
        task_type="compilation",
        intent="TASK",
        resolved_tools=["run_tests"],
        selected_account={"id": "primary", "provider": "google-genai", "model": "gemini-2.5-flash"},
        workflow_stage_id="atomic_task",
        workflow_checkpoint_ref=".agent/checkpoints/TASK-0001.json",
        evidence_refs=[".agent/memory/refs/TASK-0001.md"],
        code_graph_refs=[
            {
                "path": "agent_workspace/core/router.py",
                "symbol": "AgentRouter._build_conductor_plan",
                "ref_type": "entrypoint",
                "description": "Router builds conductor telemetry.",
            }
        ],
        impact_summary={
            "changed_file_count": 1,
            "impacted_symbol_count": 2,
            "linked_test_count": 1,
            "security_relevant_paths": ["agent_workspace/core/router.py"],
            "summary": "Router telemetry metadata changed.",
        },
    )
    span = RecordingSpan()

    router._record_conductor_plan(span, plan)
    event = router._conductor_trace_event(plan)

    assert event["trace"]["workflow_stage_id"] == "atomic_task"
    assert event["trace"]["workflow_checkpoint_ref"] == ".agent/checkpoints/TASK-0001.json"
    assert event["trace"]["evidence_refs"] == [".agent/memory/refs/TASK-0001.md"]
    assert event["trace"]["code_graph_refs"][0]["symbol"] == "AgentRouter._build_conductor_plan"
    assert event["trace"]["impact_summary"]["impacted_symbol_count"] == 2
    assert span.attributes["conductor.workflow_stage_id"] == "atomic_task"
    assert span.attributes["conductor.workflow_checkpoint_ref"] == ".agent/checkpoints/TASK-0001.json"
    assert span.attributes["conductor.evidence_ref_count"] == 1
    assert span.attributes["conductor.code_graph_ref_count"] == 1
    assert span.attributes["conductor.impact.changed_file_count"] == 1
    assert span.attributes["conductor.impact.impacted_symbol_count"] == 2
    assert span.attributes["conductor.impact.linked_test_count"] == 1
    assert span.attributes["conductor.impact.security_relevant_path_count"] == 1
    assert plan.selected_models[0].model == "gemini-2.5-flash"


def test_router_adds_route_outcome_hints_without_changing_selected_model(tmp_path):
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
    router = AgentRouter(engine, session_id="s-hints", agent_name="tester")
    try:
        seed_plan = router._build_conductor_plan(
            user_input="Seed a previous compilation outcome.",
            task_type="compilation",
            intent="TASK",
            resolved_tools=["run_tests"],
            selected_account={"id": "primary", "provider": "google-genai", "model": "gemini-2.5-pro"},
        )
        router.long_term_memory.add_route_outcome(
            session_id="s-hints",
            conductor_plan=seed_plan.model_dump(mode="json"),
            success=True,
            latency_ms=500,
            token_count=1200,
        )

        plan = router._build_conductor_plan(
            user_input="Please run tests after changing router telemetry.",
            task_type="compilation",
            intent="TASK",
            resolved_tools=["run_tests"],
            selected_account={"id": "primary", "provider": "google-genai", "model": "gemini-2.5-flash"},
        )
    finally:
        router.close()

    assert plan.selected_models[0].model == "gemini-2.5-flash"
    assert len(plan.routing_memory_hints) == 1
    assert plan.routing_memory_hints[0].task_type == "compilation"
    assert plan.routing_memory_hints[0].success is True


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
