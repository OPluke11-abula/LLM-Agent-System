import pytest
from pydantic import ValidationError

from agent_workspace.core.conductor import (
    ConductorPlan,
    ExecutionBudget,
    FallbackRule,
    MemoryScope,
    ModelCandidate,
    SelectedModel,
    VerificationStrategy,
    build_default_conductor_plan,
)


def test_conductor_plan_serializes_stable_default_plan():
    plan = build_default_conductor_plan(
        task_id="session-1:compilation",
        task_summary="Fix the failing tests in the router.",
        session_id="session-1",
        task_type="compilation",
        intent="TASK",
        resolved_tools=["calculate", "run_tests"],
        selected_account={
            "id": "primary",
            "provider": "google-genai",
            "model": "gemini-2.5-pro",
            "token_budget": 100000,
        },
        max_iterations=5,
        max_tool_calls=15,
    )

    dumped = plan.model_dump(mode="json")

    assert dumped["execution_mode"] == "pro"
    assert dumped["topology"] == "planner_worker_verifier"
    assert dumped["selected_models"][0]["account_id"] == "primary"
    assert dumped["tool_allowlist"] == ["calculate", "run_tests"]
    assert dumped["verification_strategy"]["kind"] == "verifier"
    assert dumped["budget"]["max_iterations"] == 5
    assert dumped["budget"]["max_tool_calls"] == 15


def test_conductor_plan_rejects_unknown_mode_and_topology():
    with pytest.raises(ValidationError):
        ConductorPlan(
            task_id="bad",
            task_summary="bad",
            execution_mode="mega",
            risk_level="low",
            topology="single_worker",
            task_type="text_inference",
            intent="TASK",
            subtasks=[],
            roles=[],
            candidate_models=[],
            selected_models=[],
            tool_allowlist=[],
            memory_scope=MemoryScope(session_id="s1"),
            verification_strategy=VerificationStrategy(kind="none"),
            budget=ExecutionBudget(max_iterations=1, max_tool_calls=1),
            fallbacks=[],
            decision_rationale="bad mode",
        )

    with pytest.raises(ValidationError):
        ConductorPlan(
            task_id="bad",
            task_summary="bad",
            execution_mode="fast",
            risk_level="low",
            topology="unknown_topology",
            task_type="text_inference",
            intent="TASK",
            subtasks=[],
            roles=[],
            candidate_models=[],
            selected_models=[],
            tool_allowlist=[],
            memory_scope=MemoryScope(session_id="s1"),
            verification_strategy=VerificationStrategy(kind="none"),
            budget=ExecutionBudget(max_iterations=1, max_tool_calls=1),
            fallbacks=[],
            decision_rationale="bad topology",
        )


def test_high_risk_ultra_plan_requires_approval_gate():
    with pytest.raises(ValidationError, match="High-risk ultra plans require approval"):
        ConductorPlan(
            task_id="danger",
            task_summary="Rotate production credentials.",
            execution_mode="ultra",
            risk_level="high",
            topology="debate_consensus",
            task_type="security",
            intent="TASK",
            subtasks=[],
            roles=[],
            candidate_models=[ModelCandidate(provider="openai", model="gpt-5")],
            selected_models=[
                SelectedModel(
                    role_id="worker",
                    provider="openai",
                    model="gpt-5",
                    selection_reason="high reasoning capacity",
                )
            ],
            tool_allowlist=["run_tests"],
            memory_scope=MemoryScope(session_id="s1"),
            verification_strategy=VerificationStrategy(
                kind="proof_of_consensus",
                required=True,
                approval_required=False,
            ),
            budget=ExecutionBudget(max_iterations=5, max_tool_calls=10),
            fallbacks=[FallbackRule(trigger="provider_error", action="retry")],
            decision_rationale="high impact operation",
        )


def test_chat_plan_defaults_to_fast_single_worker():
    plan = build_default_conductor_plan(
        task_id="session-2:text_inference",
        task_summary="Hello",
        session_id="session-2",
        task_type="text_inference",
        intent="CHAT",
        resolved_tools=["calculate"],
        selected_account={"id": "primary", "provider": "google-genai", "model": "gemini-2.5-flash"},
        max_iterations=5,
        max_tool_calls=15,
    )

    assert plan.execution_mode == "fast"
    assert plan.topology == "single_worker"
    assert plan.tool_allowlist == []
    assert plan.verification_strategy.kind == "none"


def test_unlimited_negative_account_budget_is_not_a_schema_failure():
    plan = build_default_conductor_plan(
        task_id="session-3:text_inference",
        task_summary="Use the default unlimited account.",
        session_id="session-3",
        task_type="text_inference",
        intent="TASK",
        resolved_tools=[],
        selected_account={
            "id": "default-account",
            "provider": "google-genai",
            "model": "gemini-2.5-flash",
            "token_budget": -1,
        },
        max_iterations=5,
        max_tool_calls=15,
    )

    assert plan.budget.token_budget is None
