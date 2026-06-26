from pathlib import Path

from scripts.eval_agents import run_eval


def test_agent_eval_smoke_report_contains_required_fields(tmp_path):
    report = run_eval(Path("scripts/agent_eval_fixtures.json"), tmp_path)

    assert report["suite"] == "agent_golden_smoke"
    assert report["failed"] == 0
    assert report["fixtures"] >= 2

    first = report["results"][0]
    assert first["completed"] is True
    assert "cost_usd" in first
    assert "latency_ms" in first
    assert "tool_use" in first
    assert "verifier_outcome" in first
    assert "unresolved_risk" in first
