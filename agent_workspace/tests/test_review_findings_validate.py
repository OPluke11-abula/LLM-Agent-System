import json
from pathlib import Path

import pytest

from agent_workspace.review_findings_validate import ReviewFindingsError, validate_review_findings


def _write_json(path: Path, data: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def _touch_workspace_files(root: Path) -> None:
    for relative in (
        "agent_workspace/core/router.py",
        "agent_workspace/core/auth.py",
        "agent_workspace/core/policy_gate.py",
        "agent_workspace/tests/test_router.py",
    ):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# test file\n", encoding="utf-8")


def _valid_report() -> dict:
    trace = {
        "path": "agent_workspace/core/router.py",
        "line": 12,
        "symbol": "AgentRouter",
        "description": "Router entrypoint validates the caller request.",
    }
    return {
        "schema_version": "1.0",
        "review_id": "TASK-0001-security",
        "target": "TASK-0001",
        "review_type": "security_review",
        "generated_at": "2026-06-29T00:00:00Z",
        "verdict": "needs_changes",
        "risk_level": "medium",
        "changed_paths": ["agent_workspace/core/router.py"],
        "security_triggers": [],
        "findings": [
            {
                "verdict": "valid",
                "severity": "medium",
                "category": "OWASP A01 Broken Access Control",
                "title": "Router path requires explicit authorization evidence",
                "entrypoint_trace": [trace],
                "propagation_trace": [],
                "sink_trace": [trace],
                "impact": "A missing authorization check could expose another session's routing state.",
                "evidence": [trace],
                "remediation": "Keep route authorization explicit and add focused regression tests.",
                "validation_status": "reasoned",
            }
        ],
    }


def test_validate_review_findings_accepts_traceable_report(tmp_path):
    _touch_workspace_files(tmp_path)
    report = _write_json(tmp_path / "docs" / "reviews" / "TASK-0001-SECURITY.json", _valid_report())

    result = validate_review_findings(tmp_path, report)

    assert result.review_id == "TASK-0001-security"
    assert result.finding_count == 1
    assert result.security_trigger_count == 0


def test_validate_review_findings_rejects_missing_evidence_trace(tmp_path):
    _touch_workspace_files(tmp_path)
    data = _valid_report()
    data["findings"][0]["evidence"] = []
    report = _write_json(tmp_path / "docs" / "reviews" / "TASK-0001-SECURITY.json", data)

    with pytest.raises(ReviewFindingsError, match="schema validation failed"):
        validate_review_findings(tmp_path, report)


def test_validate_review_findings_rejects_high_finding_without_concrete_impact(tmp_path):
    _touch_workspace_files(tmp_path)
    data = _valid_report()
    data["security_triggers"] = ["auth_or_authorization"]
    data["findings"][0]["severity"] = "high"
    data["findings"][0]["impact"] = "TBD"
    report = _write_json(tmp_path / "docs" / "reviews" / "TASK-0001-SECURITY.json", data)

    with pytest.raises(ReviewFindingsError, match="concrete impact"):
        validate_review_findings(tmp_path, report)


def test_validate_review_findings_requires_security_review_for_triggered_paths(tmp_path):
    _touch_workspace_files(tmp_path)
    data = _valid_report()
    data["review_type"] = "code_review"
    data["changed_paths"] = ["agent_workspace/core/auth.py"]
    data["security_triggers"] = []
    report = _write_json(tmp_path / "docs" / "reviews" / "TASK-0001-SECURITY.json", data)

    with pytest.raises(ReviewFindingsError, match="review_type=security_review"):
        validate_review_findings(tmp_path, report)


def test_validate_review_findings_rejects_missing_declared_trigger(tmp_path):
    _touch_workspace_files(tmp_path)
    data = _valid_report()
    data["changed_paths"] = ["agent_workspace/core/policy_gate.py"]
    data["security_triggers"] = []
    report = _write_json(tmp_path / "docs" / "reviews" / "TASK-0001-SECURITY.json", data)

    with pytest.raises(ReviewFindingsError, match="missing security_triggers"):
        validate_review_findings(tmp_path, report)


def test_validate_review_findings_rejects_trace_path_workspace_escape(tmp_path):
    _touch_workspace_files(tmp_path)
    data = _valid_report()
    data["findings"][0]["evidence"][0]["path"] = "../outside.py"
    report = _write_json(tmp_path / "docs" / "reviews" / "TASK-0001-SECURITY.json", data)

    with pytest.raises(ReviewFindingsError, match="escapes workspace"):
        validate_review_findings(tmp_path, report)
