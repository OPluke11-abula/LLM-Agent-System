from agent_workspace.core.context_budget_preflight import build_context_budget_preflight
from agent_workspace.core.token_efficient_profile import HandoffThresholds, TokenEfficientProfile


def test_preflight_reports_component_totals_and_advisory_reduction_without_trimming():
    report = build_context_budget_preflight(
        system_prompt="system " * 20,
        messages=[{"role": "user", "content": "request " * 20}],
        memory_context="memory " * 40,
        tool_schemas=[{"name": "run_tests", "description": "Run focused checks"}],
        task_context="task " * 20,
        memory_refs=["memory-ref-1", "memory-ref-2", "memory-ref-3"],
        code_graph_refs=["agent_workspace/core/conductor.py:ConductorPlan"],
        profile=TokenEfficientProfile(
            bounded_memory_retrieval_limit=1,
            max_tool_payload_tokens=1,
            verification_profile="focused",
            handoff_thresholds=HandoffThresholds(context_token_count=1),
        ),
    )

    assert report.estimated_total_tokens > 0
    assert report.component_tokens["task_context"] > 0
    assert report.component_tokens["memory_refs"] > 0
    assert report.component_tokens["code_graph_refs"] > 0
    assert report.estimated_reduction_tokens > 0
    assert report.estimated_reduction_ratio > 0
    assert report.handoff_recommended is True
    assert report.report_only is True
    assert report.trimming_applied is False


def test_preflight_recommends_handoff_for_history_change_and_evidence_thresholds():
    report = build_context_budget_preflight(
        system_prompt="system",
        messages=[{"role": "user", "content": "request"}],
        memory_context="memory",
        tool_schemas=[],
        task_context="task",
        memory_refs=[],
        code_graph_refs=[],
        changed_file_count=3,
        evidence_ref_count=2,
        profile=TokenEfficientProfile(
            handoff_thresholds=HandoffThresholds(
                history_message_count=1,
                changed_file_count=2,
                evidence_ref_count=2,
                context_token_count=10_000,
            ),
        ),
    )

    assert report.history_message_count == 1
    assert report.changed_file_count == 3
    assert report.evidence_ref_count == 2
    assert report.handoff_recommended is True
    assert report.handoff_reasons == [
        "history_message_count",
        "changed_file_count",
        "evidence_ref_count",
    ]
