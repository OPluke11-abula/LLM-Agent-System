from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, assert_never

import jsonschema


class ReviewFindingsError(ValueError):
    pass


class ReviewFindingsShape(StrEnum):
    LAS = "las"
    PAP = "pap"


@dataclass(frozen=True)
class ReviewFindingsResult:
    review_id: str
    finding_count: int
    security_trigger_count: int


LAS_SCHEMA_NAME = "review-findings.schema.json"
PAP_SCHEMA_NAME = "pap-review-findings.schema.json"
HIGH_SEVERITIES = {"high", "critical"}
PLACEHOLDER_IMPACTS = {"", "n/a", "na", "none", "tbd", "todo", "unknown"}
HIGH_RISK_PATH_PATTERNS: tuple[tuple[str, str], ...] = (
    ("auth_or_authorization", "auth"),
    ("auth_or_authorization", "jwt"),
    ("auth_or_authorization", "rbac"),
    ("auth_or_authorization", "permission"),
    ("secret_or_token_handling", "secret"),
    ("secret_or_token_handling", "token"),
    ("secret_or_token_handling", ".env"),
    ("database_query_or_migration", "migration"),
    ("database_query_or_migration", "sql"),
    ("database_query_or_migration", "database"),
    ("external_api_or_webhook", "webhook"),
    ("external_api_or_webhook", "external"),
    ("file_parsing_or_upload", "upload"),
    ("file_parsing_or_upload", "parser"),
    ("file_parsing_or_upload", "parse"),
    ("command_execution_or_sandbox", "sandbox"),
    ("command_execution_or_sandbox", "subprocess"),
    ("command_execution_or_sandbox", "exec"),
    ("high_impact_policy_gate", "policy_gate"),
    ("high_impact_policy_gate", "consensus"),
)


def validate_review_findings(root: str | Path, input_path: str | Path) -> ReviewFindingsResult:
    root_path = Path(root).resolve()
    report_path = _resolve_existing_file(root_path, input_path, "review findings")
    report = _read_json_mapping(report_path)
    shape = _detect_report_shape(report)

    match shape:
        case ReviewFindingsShape.LAS:
            _validate_schema(root_path, LAS_SCHEMA_NAME, report)
            _validate_las_workspace_paths(root_path, report)
            _validate_las_high_risk_rules(report)
            report_id = str(report["review_id"])
        case ReviewFindingsShape.PAP:
            _validate_schema(root_path, PAP_SCHEMA_NAME, report)
            _validate_pap_workspace_paths(root_path, report)
            _validate_pap_high_risk_rules(report)
            report_id = str(report["report_id"])
        case unreachable:
            assert_never(unreachable)

    return ReviewFindingsResult(
        review_id=report_id,
        finding_count=len(report.get("findings", [])),
        security_trigger_count=len(report.get("security_triggers", [])),
    )


def _read_json_mapping(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as error:
        raise ReviewFindingsError(f"{path} could not be parsed as JSON: {error}") from error
    if not isinstance(data, dict):
        raise ReviewFindingsError(f"{path} must contain a JSON object")
    return data


def _detect_report_shape(report: dict[str, Any]) -> ReviewFindingsShape:
    has_las_id = "review_id" in report
    has_pap_id = "report_id" in report
    if has_las_id and has_pap_id:
        raise ReviewFindingsError("report must not mix review_id and report_id")
    if has_las_id:
        return ReviewFindingsShape.LAS
    if has_pap_id:
        return ReviewFindingsShape.PAP
    raise ReviewFindingsError("report must declare review_id or report_id")


def _validate_schema(root: Path, schema_name: str, report: dict[str, Any]) -> None:
    schema_path = root / "spec" / schema_name
    if not schema_path.is_file():
        schema_path = Path(__file__).resolve().parents[1] / "spec" / schema_name
    if not schema_path.is_file():
        raise ReviewFindingsError(f"schema not found: {schema_name}")

    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = jsonschema.Draft7Validator(schema)
    errors = sorted(validator.iter_errors(report), key=lambda item: list(item.path))
    if errors:
        first = errors[0]
        location = ".".join(str(part) for part in first.path) or "<root>"
        raise ReviewFindingsError(f"schema validation failed at {location}: {first.message}")


def _validate_las_workspace_paths(root: Path, report: dict[str, Any]) -> None:
    for path_value in report.get("changed_paths", []):
        _resolve_workspace_path(root, path_value, "changed_path")

    for finding_index, finding in enumerate(report.get("findings", [])):
        for field_name in ("entrypoint_trace", "propagation_trace", "sink_trace", "evidence"):
            traces = finding.get(field_name, [])
            for trace_index, trace in enumerate(traces):
                _resolve_workspace_path(
                    root,
                    trace["path"],
                    f"findings[{finding_index}].{field_name}[{trace_index}].path",
                )
        code_graph_evidence = finding.get("code_graph_evidence")
        if code_graph_evidence:
            _validate_code_graph_evidence_paths(root, finding_index, code_graph_evidence)


def _validate_pap_workspace_paths(root: Path, report: dict[str, Any]) -> None:
    for finding_index, finding in enumerate(report.get("findings", [])):
        for field_name in ("source_trace", "exploit_path"):
            traces = finding.get(field_name, [])
            for trace_index, trace in enumerate(traces):
                _resolve_workspace_path(
                    root,
                    trace["path"],
                    f"findings[{finding_index}].{field_name}[{trace_index}].path",
                )
        code_graph_evidence = finding.get("code_graph_evidence")
        if code_graph_evidence:
            _validate_code_graph_evidence_paths(root, finding_index, code_graph_evidence)


def _validate_las_high_risk_rules(report: dict[str, Any]) -> None:
    findings = report.get("findings", [])
    declared_triggers = set(report.get("security_triggers", []))
    inferred_triggers = _infer_path_triggers(report.get("changed_paths", []))

    if inferred_triggers and report.get("review_type") != "security_review":
        raise ReviewFindingsError(
            "high-risk changed paths require review_type=security_review "
            f"and declared security_triggers: {sorted(inferred_triggers)}"
        )
    missing_triggers = inferred_triggers - declared_triggers
    if missing_triggers:
        raise ReviewFindingsError(f"missing security_triggers for changed paths: {sorted(missing_triggers)}")

    for index, finding in enumerate(findings):
        severity = finding.get("severity")
        impact = str(finding.get("impact", "")).strip().lower()
        if severity in HIGH_SEVERITIES and impact in PLACEHOLDER_IMPACTS:
            raise ReviewFindingsError(f"findings[{index}] high/critical severity requires concrete impact")
        if severity in HIGH_SEVERITIES and not declared_triggers:
            raise ReviewFindingsError(f"findings[{index}] high/critical severity requires security_triggers")
        if severity in HIGH_SEVERITIES:
            _validate_high_risk_code_graph_evidence(index, finding)


def _validate_pap_high_risk_rules(report: dict[str, Any]) -> None:
    for index, finding in enumerate(report.get("findings", [])):
        severity = finding.get("severity")
        impact = str(finding.get("impact", "")).strip().lower()
        if severity in HIGH_SEVERITIES and impact in PLACEHOLDER_IMPACTS:
            raise ReviewFindingsError(f"findings[{index}] high/critical severity requires concrete impact")
        if severity in HIGH_SEVERITIES:
            exploit_path = finding.get("exploit_path", [])
            code_graph_evidence = finding.get("code_graph_evidence")
            if not exploit_path and not code_graph_evidence:
                raise ReviewFindingsError(
                    f"findings[{index}] high/critical severity requires exploit_path or code_graph_evidence"
                )
            if code_graph_evidence:
                _validate_high_risk_code_graph_evidence(index, finding)


def _validate_code_graph_evidence_paths(
    root: Path,
    finding_index: int,
    code_graph_evidence: dict[str, Any],
) -> None:
    symbol_fields = ("entrypoint_symbol", "sink_symbol")
    for field_name in symbol_fields:
        symbol_ref = code_graph_evidence.get(field_name)
        if symbol_ref:
            _resolve_workspace_path(
                root,
                symbol_ref["path"],
                f"findings[{finding_index}].code_graph_evidence.{field_name}.path",
            )

    list_fields = ("propagation_path", "impacted_symbols", "linked_tests")
    for field_name in list_fields:
        for item_index, item in enumerate(code_graph_evidence.get(field_name, [])):
            _resolve_workspace_path(
                root,
                item["path"],
                f"findings[{finding_index}].code_graph_evidence.{field_name}[{item_index}].path",
            )


def _validate_high_risk_code_graph_evidence(index: int, finding: dict[str, Any]) -> None:
    code_graph_evidence = finding.get("code_graph_evidence")
    if not code_graph_evidence:
        raise ReviewFindingsError(f"findings[{index}] high/critical severity requires code_graph_evidence")

    required_fields = (
        "entrypoint_symbol",
        "propagation_path",
        "sink_symbol",
        "impacted_symbols",
        "linked_tests",
    )
    for field_name in required_fields:
        value = code_graph_evidence.get(field_name)
        if not value:
            raise ReviewFindingsError(
                f"findings[{index}].code_graph_evidence requires non-empty {field_name}"
            )


def _infer_path_triggers(paths: list[str]) -> set[str]:
    triggers: set[str] = set()
    for raw_path in paths:
        lowered = raw_path.replace("\\", "/").lower()
        for trigger, pattern in HIGH_RISK_PATH_PATTERNS:
            if pattern in lowered:
                triggers.add(trigger)
    return triggers


def _resolve_existing_file(root: Path, path_value: str | Path, label: str) -> Path:
    path = Path(path_value)
    if not path.is_absolute():
        path = root / path
    resolved = path.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as error:
        raise ReviewFindingsError(f"{label} path escapes workspace: {path_value}") from error
    if not resolved.is_file():
        raise ReviewFindingsError(f"{label} file does not exist: {path_value}")
    return resolved


def _resolve_workspace_path(root: Path, path_value: str, label: str) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        raise ReviewFindingsError(f"{label} escapes workspace: {path_value}")
    resolved = (root / path).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as error:
        raise ReviewFindingsError(f"{label} escapes workspace: {path_value}") from error
    return resolved


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate LAS/PAP structured review findings.")
    parser.add_argument("--root", default=".", help="Workspace root. Defaults to current directory.")
    parser.add_argument("--input", required=True, help="Review findings JSON path.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        result = validate_review_findings(args.root, args.input)
    except ReviewFindingsError as error:
        parser.exit(1, f"Review findings validation failed: {error}\n")

    print(
        f"Review findings valid: {result.review_id} "
        f"({result.finding_count} finding(s), {result.security_trigger_count} trigger(s))"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
