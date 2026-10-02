from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from json import JSONDecodeError
from pathlib import Path
from typing import Final, Sequence, TypeAlias

JsonValue: TypeAlias = (
    None | bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"]
)
JsonObject: TypeAlias = dict[str, JsonValue]

DEFAULT_OUTPUT_DIR: Final = Path(".agent/reports/react-doctor")
SUMMARY_FILENAME: Final = "react-doctor-summary.json"
MAX_TOP_FILES: Final = 10
MAX_ERROR_FINDINGS: Final = 20
MAX_MESSAGE_CHARS: Final = 240
MAX_CHANGED_REGRESSIONS: Final = 12
MAX_NEXT_FIX_QUEUE: Final = 10

FINDING_KEYS: Final = ("findings", "issues", "results", "diagnostics", "violations")
SECRET_PATTERNS: Final = (
    re.compile(r"(?i)(api[_-]?key\s*[:=]\s*)[^\s,\"']+"),
    re.compile(r"(?i)(token\s*[:=]\s*)[^\s,\"']+"),
    re.compile(r"(?i)(password\s*[:=]\s*)[^\s,\"']+"),
    re.compile(r"\bsk_(?:live|test)_[A-Za-z0-9_-]+"),
)

SURFACE_BY_FILE_TOKEN: Final = {
    "MissionControlView": "Mission Control",
    "TaskFlowView": "Task Flow",
    "IntelligenceMapView": "Intelligence Map",
    "SwarmGovernanceConsole": "Governance Cockpit",
    "LongTermMemoryView": "Memory Manager",
    "SettingsView": "Settings",
    "AdminDashboardView": "Admin Console",
    "TopologyView": "Topology",
}


@dataclass(frozen=True, slots=True)
class Finding:
    rule: str
    severity: str
    category: str
    path: str
    message: str
    line: int | None = None

    def to_summary(self) -> JsonObject:
        payload: JsonObject = {
            "rule": self.rule,
            "severity": self.severity,
            "category": self.category,
            "path": self.path,
            "message": self.message,
        }
        if self.line is not None:
            payload["line"] = self.line
        return payload


@dataclass(frozen=True, slots=True)
class ReactDoctorReportError(Exception):
    reason: str

    def __str__(self) -> str:
        return self.reason


def parse_react_doctor_report(
    source: JsonObject,
    changed_source: JsonObject | None = None,
) -> JsonObject:
    findings = [_parse_finding(item) for item in _finding_objects(source)]
    changed_findings = (
        [_parse_finding(item) for item in _finding_objects(changed_source)]
        if changed_source is not None
        else []
    )
    severity_counts = Counter(finding.severity for finding in findings)
    category_counts = Counter(finding.category for finding in findings)
    file_counts = Counter(finding.path for finding in findings if finding.path)
    error_findings = [finding.to_summary() for finding in findings if finding.severity == "error"][
        :MAX_ERROR_FINDINGS
    ]

    return {
        "schema_version": "1.0.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "totals": {
            "total_findings": len(findings),
            "by_severity": dict(sorted(severity_counts.items())),
            "by_category": dict(sorted(category_counts.items())),
        },
        "top_files": [
            {"path": path, "findings": count}
            for path, count in file_counts.most_common(MAX_TOP_FILES)
        ],
        "error_findings": error_findings,
        "changed_file_regressions": [
            finding.to_summary() for finding in changed_findings
        ][:MAX_CHANGED_REGRESSIONS],
        "next_fix_queue": [finding.to_summary() for finding in _next_fix_queue(findings)],
        "affected_phase67_surfaces": _affected_surfaces(findings),
        "verification_commands": [
            "npm.cmd --prefix viewer run doctor:json",
            "python -m agent_workspace.react_doctor_report <react-doctor-json>",
        ],
    }


def write_react_doctor_summary(
    report_path: Path,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    changed_report_path: Path | None = None,
    snapshot_path: Path | None = None,
) -> Path:
    raw = _load_report_json(report_path)
    if not isinstance(raw, dict):
        raise ReactDoctorReportError(reason="React Doctor report root must be a JSON object")
    changed_raw = None
    if changed_report_path is not None:
        changed_raw = _load_report_json(changed_report_path)
        if not isinstance(changed_raw, dict):
            raise ReactDoctorReportError(reason="Changed React Doctor report root must be a JSON object")

    summary = parse_react_doctor_report(raw, changed_raw)
    summary["source_report"] = str(report_path)
    if changed_report_path is not None:
        summary["changed_source_report"] = str(changed_report_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / SUMMARY_FILENAME
    _write_summary_json(output_path, summary)
    if snapshot_path is not None:
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        _write_summary_json(snapshot_path, summary)
    return output_path


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Summarize React Doctor JSON for LAS")
    parser.add_argument("report", type=Path, help="Path to React Doctor JSON output")
    parser.add_argument(
        "--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR,
        help="Directory for react-doctor-summary.json"
    )
    parser.add_argument(
        "--changed-report", type=Path, default=None,
        help="Optional changed-scope React Doctor JSON output"
    )
    parser.add_argument(
        "--snapshot-output", type=Path, default=None,
        help="Optional second copy of the LAS summary for viewer imports"
    )
    args = parser.parse_args(argv)
    output_path = write_react_doctor_summary(
        args.report,
        args.output_dir,
        changed_report_path=args.changed_report,
        snapshot_path=args.snapshot_output,
    )
    print(output_path)
    return 0


def _finding_objects(source: JsonObject) -> list[JsonObject]:
    for key in FINDING_KEYS:
        value = source.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    projects = source.get("projects")
    if not isinstance(projects, list):
        return []
    findings: list[JsonObject] = []
    for project in projects:
        if isinstance(project, dict):
            for key in FINDING_KEYS:
                value = project.get(key)
                if isinstance(value, list):
                    findings.extend(item for item in value if isinstance(item, dict))
    return findings


def _load_report_json(report_path: Path) -> JsonValue:
    content = report_path.read_text(encoding="utf-8")
    try:
        return json.loads(content)
    except JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}")
        if start < 0 or end <= start:
            raise ReactDoctorReportError(reason="React Doctor output does not contain JSON") from None
        try:
            return json.loads(content[start : end + 1])
        except JSONDecodeError as error:
            raise ReactDoctorReportError(reason=f"React Doctor JSON parse failed: {error.msg}") from None


def _parse_finding(raw: JsonObject) -> Finding:
    return Finding(
        rule=_string_field(raw, ("ruleId", "rule", "id", "check"), "unknown"),
        severity=_normal_severity(_string_field(raw, ("severity", "level"), "warning")),
        category=_string_field(raw, ("category", "type", "group"), "uncategorized"),
        path=_string_field(raw, ("file", "filePath", "path", "filename", "source"), ""),
        line=_int_field(raw, ("line", "lineNumber")),
        message=_redact(_string_field(raw, ("message", "description", "title"), ""))[
            :MAX_MESSAGE_CHARS
        ],
    )


def _next_fix_queue(findings: Sequence[Finding]) -> list[Finding]:
    return sorted(findings, key=_fix_priority)[:MAX_NEXT_FIX_QUEUE]


def _fix_priority(finding: Finding) -> tuple[int, int, str, int]:
    severity_rank = {"error": 0, "warning": 1, "info": 2}.get(finding.severity, 3)
    category_rank = {
        "Bugs": 0,
        "bug": 0,
        "Accessibility": 1,
        "accessibility": 1,
        "Performance": 2,
        "performance": 2,
        "Maintainability": 3,
        "maintainability": 3,
    }.get(finding.category, 4)
    return (severity_rank, category_rank, finding.path, finding.line or 0)


def _write_summary_json(path: Path, summary: JsonObject) -> None:
    path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _string_field(raw: JsonObject, keys: Sequence[str], fallback: str) -> str:
    for key in keys:
        value = raw.get(key)
        if isinstance(value, str) and value:
            return _redact(value)
    return fallback


def _int_field(raw: JsonObject, keys: Sequence[str]) -> int | None:
    for key in keys:
        value = raw.get(key)
        if isinstance(value, int):
            return value
    return None


def _normal_severity(value: str) -> str:
    normalized = value.strip().lower()
    if normalized in {"error", "warning", "info"}:
        return normalized
    if normalized in {"warn", "medium"}:
        return "warning"
    if normalized in {"critical", "high"}:
        return "error"
    return "info"


def _redact(value: str) -> str:
    redacted = value
    for pattern in SECRET_PATTERNS:
        redacted = pattern.sub(_redaction_replacement, redacted)
    return redacted


def _redaction_replacement(match: re.Match[str]) -> str:
    prefix = match.group(1) if match.lastindex else ""
    return f"{prefix}[REDACTED]"


def _affected_surfaces(findings: Sequence[Finding]) -> list[str]:
    surfaces = {
        surface
        for finding in findings
        for token, surface in SURFACE_BY_FILE_TOKEN.items()
        if token in finding.path
    }
    return sorted(surfaces)


if __name__ == "__main__":
    raise SystemExit(main())
