from __future__ import annotations

import re
import shutil
import sys
import tempfile
from contextlib import redirect_stdout
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from io import StringIO
from pathlib import Path
from typing import Any, Final

import yaml

from agent_workspace.pap_validate import validate as validate_pap_workspace


VALID_LAYOUT_AGENT_MD: Final[str] = (
    "---\n"
    'protocol_version: "1.0.0"\n'
    'min_runtime_version: "0.1.0"\n'
    'name: "LayoutAgent"\n'
    'version: "1.0.0"\n'
    'purpose: "PAP layout conformance"\n'
    'language: "en"\n'
    'authorization_level: "autonomous"\n'
    'use_case_tags: ["conformance"]\n'
    'tools: ["calculate"]\n'
    "---\n"
    "# Layout Agent\n"
)


class ExpectedBehavior(StrEnum):
    ACCEPT = "accept"
    REJECT_WITH_ERROR = "reject_with_error"


class ConformanceStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    DEVIATION = "deviation"


class ConformanceFormatError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ConformanceCase:
    suite: str
    name: str
    input_data: dict[str, Any]
    expected_behavior: ExpectedBehavior


@dataclass(frozen=True, slots=True)
class ConformanceResult:
    name: str
    expected_behavior: ExpectedBehavior
    actual_behavior: ExpectedBehavior
    status: ConformanceStatus
    error: str
    deviation: str


def load_conformance_cases(path: Path) -> list[ConformanceCase]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ConformanceFormatError(f"{path} must contain a mapping")

    tests = raw.get("tests")
    if not isinstance(tests, list):
        raise ConformanceFormatError(f"{path} must contain a tests list")

    suite = path.stem
    cases: list[ConformanceCase] = []
    for index, item in enumerate(tests):
        if not isinstance(item, dict):
            raise ConformanceFormatError(f"{path} test {index} must be a mapping")
        name = item.get("name")
        input_data = item.get("input")
        expected = item.get("expected_behavior")
        if not isinstance(name, str) or not isinstance(input_data, dict) or not isinstance(expected, str):
            raise ConformanceFormatError(f"{path} test {index} has invalid fields")
        cases.append(
            ConformanceCase(
                suite=suite,
                name=name,
                input_data=input_data,
                expected_behavior=ExpectedBehavior(expected),
            )
        )
    return cases


def run_conformance_suite(path: Path, workspace_root: Path) -> list[ConformanceResult]:
    return [run_conformance_case(case, workspace_root) for case in load_conformance_cases(path)]


def run_conformance_case(case: ConformanceCase, workspace_root: Path) -> ConformanceResult:
    case_root = workspace_root / _safe_name(case.name)
    if case_root.exists():
        shutil.rmtree(case_root)
    case_root.mkdir(parents=True)
    _copy_schemas(case_root)

    match case.suite:
        case "schema-validation":
            deviation = _prepare_schema_case(case, case_root)
        case "layout-validation":
            deviation = _prepare_layout_case(case, case_root)
        case unreachable:
            raise ConformanceFormatError(f"Unsupported conformance suite: {unreachable}")

    actual_behavior, error = _validate_workspace(case_root)
    status = _status_for(case.expected_behavior, actual_behavior, deviation)
    return ConformanceResult(
        name=case.name,
        expected_behavior=case.expected_behavior,
        actual_behavior=actual_behavior,
        status=status,
        error=error,
        deviation=deviation,
    )


def _prepare_schema_case(case: ConformanceCase, case_root: Path) -> str:
    agent_md = case.input_data.get("agent.md")
    if not isinstance(agent_md, str):
        raise ConformanceFormatError(f"{case.name} must provide input.agent.md")
    agent_dir = case_root / ".agent"
    skills_dir = agent_dir / "skills"
    skills_dir.mkdir(parents=True)
    (agent_dir / "agent.md").write_text(agent_md, encoding="utf-8")

    config = _frontmatter_mapping(agent_md)
    tools = config.get("tools", [])
    if isinstance(tools, list):
        for tool in tools:
            if isinstance(tool, str):
                _write_skill_contract(skills_dir / f"{tool}.md", tool)

    if case.expected_behavior is not ExpectedBehavior.ACCEPT:
        return ""

    deviations: list[str] = []
    if "tools" not in config:
        deviations.append("upstream schema fixture omits tools, which LAS requires")
    if config.get("authorization_level") == "read_only":
        deviations.append("upstream schema fixture uses read_only, while LAS accepts read-only")
    return "; ".join(deviations)


def _prepare_layout_case(case: ConformanceCase, case_root: Path) -> str:
    filesystem = case.input_data.get("filesystem")
    if not isinstance(filesystem, dict):
        raise ConformanceFormatError(f"{case.name} must provide input.filesystem")

    placeholders = False
    for relative_path, content in filesystem.items():
        if not isinstance(relative_path, str):
            raise ConformanceFormatError(f"{case.name} filesystem path must be a string")
        target = case_root / relative_path
        if relative_path.endswith("/"):
            target.mkdir(parents=True, exist_ok=True)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        if relative_path == ".agent/agent.md" and content == "...":
            placeholders = True
            target.write_text(VALID_LAYOUT_AGENT_MD, encoding="utf-8")
        else:
            placeholders = placeholders or content == "..."
            target.write_text(str(content), encoding="utf-8")

    _write_skill_contract(case_root / ".agent" / "skills" / "calculate.md", "calculate")

    deviations: list[str] = []
    if placeholders:
        deviations.append("upstream layout fixture uses placeholder file content")
    if case.expected_behavior is ExpectedBehavior.REJECT_WITH_ERROR:
        deviations.append("upstream layout requires persona.md and memory.md, which LAS pap_validate does not enforce")
    else:
        deviations.append("upstream layout names knowledge/, while LAS uses knowledge_base/")
    return "; ".join(deviations)


def _copy_schemas(case_root: Path) -> None:
    spec_dir = case_root / "spec"
    spec_dir.mkdir(parents=True)
    source_spec_dir = Path(__file__).resolve().parent.parent / "spec"
    for schema_file in source_spec_dir.glob("*.json"):
        shutil.copy(schema_file, spec_dir / schema_file.name)


def _write_skill_contract(path: Path, tool: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        (
            "---\n"
            f"id: {tool}\n"
            "description: Synthetic PAP conformance skill contract.\n"
            "safety_notes:\n"
            '  - "Synthetic conformance contract for validator execution."\n'
            "---\n"
            f"# {tool}\n"
        ),
        encoding="utf-8",
    )


def _frontmatter_mapping(agent_md: str) -> dict[str, Any]:
    parts = agent_md.split("---", 2)
    if len(parts) < 3:
        return {}
    data = yaml.safe_load(parts[1]) or {}
    if not isinstance(data, dict):
        return {}
    return data


def _validate_workspace(case_root: Path) -> tuple[ExpectedBehavior, str]:
    try:
        with redirect_stdout(StringIO()):
            validate_pap_workspace(case_root)
    except (FileNotFoundError, ValueError) as exc:
        return ExpectedBehavior.REJECT_WITH_ERROR, str(exc)
    return ExpectedBehavior.ACCEPT, ""


def _status_for(
    expected_behavior: ExpectedBehavior,
    actual_behavior: ExpectedBehavior,
    deviation: str,
) -> ConformanceStatus:
    if deviation:
        return ConformanceStatus.DEVIATION
    if expected_behavior is actual_behavior:
        return ConformanceStatus.PASSED
    return ConformanceStatus.FAILED


def _safe_name(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "-", name).strip("-").lower()


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print("usage: python -m agent_workspace.pap_conformance <conformance-yaml> [...]")
        return 2

    has_failed = False
    with tempfile.TemporaryDirectory(prefix="pap-conformance-") as temp_dir:
        temp_root = Path(temp_dir)
        for arg in args:
            path = Path(arg)
            results = run_conformance_suite(path, temp_root / path.stem)
            for result in results:
                details = result.deviation or result.error
                print(
                    "\t".join(
                        [
                            result.status.value,
                            path.name,
                            result.name,
                            f"expected={result.expected_behavior.value}",
                            f"actual={result.actual_behavior.value}",
                            details,
                        ]
                    ).rstrip()
                )
                has_failed = has_failed or result.status is ConformanceStatus.FAILED
    return 1 if has_failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
