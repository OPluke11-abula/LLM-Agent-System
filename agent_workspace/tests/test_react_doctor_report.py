import json
from pathlib import Path

from agent_workspace.react_doctor_report import (
    ReactDoctorReportError,
    parse_react_doctor_report,
    write_react_doctor_summary,
)


def test_parse_react_doctor_report_redacts_secret_like_values() -> None:
    source = {
        "tool": {"name": "react-doctor", "version": "0.5.8"},
        "findings": [
            {
                "ruleId": "artifact-secret-leak",
                "severity": "error",
                "category": "security",
                "file": "viewer/dist/assets/AdminDashboardView.js",
                "line": 42,
                "message": "Found apiKey=sk_live_1234567890abcdef in browser bundle",
            },
            {
                "rule": "control-has-associated-label",
                "severity": "warning",
                "category": "accessibility",
                "file": "viewer/src/components/TaskFlowView.tsx",
                "message": "Button has no label",
            },
        ],
    }

    summary = parse_react_doctor_report(source)

    assert summary["totals"]["by_severity"] == {"error": 1, "warning": 1}
    assert summary["totals"]["by_category"] == {"accessibility": 1, "security": 1}
    assert summary["top_files"][0]["path"] == "viewer/dist/assets/AdminDashboardView.js"
    assert summary["error_findings"][0]["message"] == "Found apiKey=[REDACTED] in browser bundle"
    assert summary["affected_phase67_surfaces"] == ["Admin Console", "Task Flow"]


def test_write_react_doctor_summary_uses_bounded_las_output(tmp_path: Path) -> None:
    report_path = tmp_path / "react-doctor.json"
    report_path.write_text(
        json.dumps(
            {
                "issues": [
                    {
                        "rule": "giant-component",
                        "severity": "warning",
                        "category": "architecture",
                        "file": "viewer/src/components/TopologyView.tsx",
                        "message": "Large component",
                    },
                    {
                        "rule": "effect-state-sync",
                        "severity": "error",
                        "category": "state",
                        "file": "viewer/src/components/AdminDashboardView.tsx",
                        "message": "Cascading state sync",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    output_path = write_react_doctor_summary(report_path, tmp_path / "reports")

    summary = json.loads(output_path.read_text(encoding="utf-8"))
    assert output_path.name == "react-doctor-summary.json"
    assert summary["schema_version"] == "1.0.0"
    assert summary["source_report"] == str(report_path)
    assert summary["totals"]["total_findings"] == 2
    assert summary["changed_file_regressions"] == []
    assert [item["rule"] for item in summary["next_fix_queue"]] == [
        "effect-state-sync",
        "giant-component",
    ]
    assert summary["verification_commands"] == [
        "npm.cmd --prefix viewer run doctor:json",
        "python -m agent_workspace.react_doctor_report <react-doctor-json>",
    ]


def test_write_react_doctor_summary_includes_changed_scope_and_snapshot(tmp_path: Path) -> None:
    report_path = tmp_path / "react-doctor.json"
    changed_report_path = tmp_path / "react-doctor-changed.json"
    snapshot_path = tmp_path / "viewer" / "react-doctor-summary.json"
    report_path.write_text(
        json.dumps(
            {
                "projects": [
                    {
                        "diagnostics": [
                            {
                                "rule": "prefer-html-dialog",
                                "severity": "warning",
                                "category": "Accessibility",
                                "filePath": "viewer/src/components/CommandPalette.tsx",
                                "line": 206,
                                "message": "Custom modal instead of dialog",
                            }
                        ]
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    changed_report_path.write_text(
        json.dumps(
            {
                "projects": [
                    {
                        "diagnostics": [
                            {
                                "rule": "no-array-index-as-key",
                                "severity": "warning",
                                "category": "Bugs",
                                "filePath": "viewer/src/components/TopologyView.tsx",
                                "line": 1158,
                                "message": "Array index used as a key",
                            }
                        ]
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    output_path = write_react_doctor_summary(
        report_path,
        tmp_path / "reports",
        changed_report_path=changed_report_path,
        snapshot_path=snapshot_path,
    )

    summary = json.loads(output_path.read_text(encoding="utf-8"))
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    assert summary == snapshot
    assert summary["changed_source_report"] == str(changed_report_path)
    assert summary["changed_file_regressions"] == [
        {
            "category": "Bugs",
            "line": 1158,
            "message": "Array index used as a key",
            "path": "viewer/src/components/TopologyView.tsx",
            "rule": "no-array-index-as-key",
            "severity": "warning",
        }
    ]
    assert summary["next_fix_queue"][0]["rule"] == "prefer-html-dialog"


def test_write_react_doctor_summary_rejects_non_object_json(tmp_path: Path) -> None:
    report_path = tmp_path / "react-doctor.json"
    report_path.write_text("[]", encoding="utf-8")

    try:
        write_react_doctor_summary(report_path, tmp_path / "reports")
    except ReactDoctorReportError as error:
        assert str(error) == "React Doctor report root must be a JSON object"
    else:
        raise AssertionError("Expected ReactDoctorReportError")


def test_write_react_doctor_summary_accepts_npm_wrapped_json(tmp_path: Path) -> None:
    report_path = tmp_path / "react-doctor.json"
    report_path.write_text(
        '\n> tauri-app@0.1.0 doctor:json\n\n{"projects":[{"diagnostics":[{"rule":"no-fetch","severity":"warning","filePath":"viewer/src/App.tsx"}]}]}\n',
        encoding="utf-8",
    )

    output_path = write_react_doctor_summary(report_path, tmp_path / "reports")

    summary = json.loads(output_path.read_text(encoding="utf-8"))
    assert summary["totals"]["total_findings"] == 1
    assert summary["totals"]["by_severity"] == {"warning": 1}
    assert summary["top_files"] == [{"path": "viewer/src/App.tsx", "findings": 1}]
