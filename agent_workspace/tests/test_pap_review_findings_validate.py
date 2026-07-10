import pytest

from agent_workspace.review_findings_validate import ReviewFindingsError, validate_review_findings
from agent_workspace.tests.test_review_findings_validate import (
    _code_graph_evidence,
    _touch_workspace_files,
    _write_json,
)


def _valid_pap_report() -> dict:
    source_trace = [
        {
            "path": "agent_workspace/core/auth.py",
            "line": 24,
            "symbol": "authorize_request",
            "description": "Authorization sink decides whether a caller may access the route.",
        }
    ]
    return {
        "schema_version": "1.0",
        "report_id": "PAP-0001-security",
        "target": "TASK-0001",
        "generated_at": "2026-06-29T00:00:00Z",
        "execution_policy": {
            "mode": "report_only",
            "parallel_audit_agents": False,
        },
        "security_triggers": ["auth_or_authorization"],
        "findings": [
            {
                "severity": "high",
                "category": "authorization",
                "title": "Route authorization can be bypassed",
                "source_trace": source_trace,
                "impact": "A caller could access another session's routing state.",
                "exploit_path": source_trace,
                "remediation": "Keep route authorization explicit and add focused regression tests.",
                "validation_status": "reasoned",
            }
        ],
    }


def test_validate_review_findings_accepts_pap_report_with_exploit_path(tmp_path):
    _touch_workspace_files(tmp_path)
    report = _write_json(tmp_path / "docs" / "reviews" / "PAP-0001-SECURITY.json", _valid_pap_report())

    result = validate_review_findings(tmp_path, report)

    assert result.review_id == "PAP-0001-security"
    assert result.finding_count == 1
    assert result.security_trigger_count == 1


def test_validate_review_findings_rejects_pap_report_without_report_only_policy(tmp_path):
    _touch_workspace_files(tmp_path)
    data = _valid_pap_report()
    data["execution_policy"]["mode"] = "apply_changes"
    report = _write_json(tmp_path / "docs" / "reviews" / "PAP-0001-SECURITY.json", data)

    with pytest.raises(ReviewFindingsError, match="schema validation failed"):
        validate_review_findings(tmp_path, report)


def test_validate_review_findings_rejects_pap_high_finding_without_exploit_or_graph(tmp_path):
    _touch_workspace_files(tmp_path)
    data = _valid_pap_report()
    data["findings"][0]["exploit_path"] = []
    report = _write_json(tmp_path / "docs" / "reviews" / "PAP-0001-SECURITY.json", data)

    with pytest.raises(ReviewFindingsError, match="requires exploit_path or code_graph_evidence"):
        validate_review_findings(tmp_path, report)


def test_validate_review_findings_accepts_pap_high_finding_with_code_graph_evidence(tmp_path):
    _touch_workspace_files(tmp_path)
    data = _valid_pap_report()
    data["findings"][0]["exploit_path"] = []
    data["findings"][0]["code_graph_evidence"] = _code_graph_evidence()
    report = _write_json(tmp_path / "docs" / "reviews" / "PAP-0001-SECURITY.json", data)

    result = validate_review_findings(tmp_path, report)

    assert result.review_id == "PAP-0001-security"


def test_validate_review_findings_rejects_pap_source_trace_workspace_escape(tmp_path):
    _touch_workspace_files(tmp_path)
    data = _valid_pap_report()
    data["findings"][0]["source_trace"][0]["path"] = "../outside.py"
    report = _write_json(tmp_path / "docs" / "reviews" / "PAP-0001-SECURITY.json", data)

    with pytest.raises(ReviewFindingsError, match="source_trace.*escapes workspace"):
        validate_review_findings(tmp_path, report)
