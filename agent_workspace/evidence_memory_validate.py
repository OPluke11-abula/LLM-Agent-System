from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

import jsonschema


class EvidenceMemoryValidationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class EvidenceMemoryValidationResult:
    schema_version: str
    record_count: int


@dataclass(frozen=True, slots=True)
class EvidenceMemoryBuildInput:
    task_id: str
    atom_id: str
    result_ref: str
    canvas_ref: str
    source_path: str
    source_hash: str
    fact: str
    scenario: str
    persona: str | None


SCHEMA_NAME: Final = "evidence-memory.schema.json"
WORKFLOW_MEMORY_RECORD_TYPES: Final[frozenset[str]] = frozenset(
    {
        "evidence_ref",
        "workflow_atom",
        "workflow_scenario",
        "workflow_persona",
        "canonical_artifact",
        "mermaid_canvas_ref",
    }
)
TRACE_LINK_KEYS: Final[frozenset[str]] = frozenset(
    {
        "result_ref",
        "raw_evidence_ref",
        "raw_evidence_refs",
        "evidence_ref",
        "evidence_refs",
        "canonical_artifact_ref",
        "canonical_artifact_refs",
        "source_ref",
        "source_refs",
        "atom_ref",
        "atom_refs",
        "trace_ref",
        "trace_refs",
    }
)


def build_evidence_memory_document(source: EvidenceMemoryBuildInput) -> dict[str, Any]:
    raw_id = f"raw-{source.task_id}"
    artifact_id = f"artifact-{source.task_id}"
    scenario_id = f"scenario-{source.task_id}"
    canvas_id = f"canvas-{source.task_id}"
    profile_claims = []
    if source.persona:
        profile_claims.append(
            {
                "id": f"profile-{source.task_id}",
                "claim": source.persona,
                "evidence_refs": [raw_id],
                "atom_refs": [source.atom_id],
            }
        )
    return {
        "schema_version": "1.0",
        "l0_raw_evidence_refs": [
            {
                "id": raw_id,
                "path": source.result_ref,
                "source_path": source.source_path,
                "sha256": source.source_hash,
            }
        ],
        "canonical_artifacts": [
            {
                "id": artifact_id,
                "path": source.result_ref,
                "artifact_type": "raw_evidence",
                "evidence_refs": [raw_id],
            }
        ],
        "l1_atoms": [
            {
                "id": source.atom_id,
                "fact": source.fact,
                "evidence_refs": [raw_id],
                "canonical_artifact_refs": [artifact_id],
            }
        ],
        "l2_scenarios": [
            {
                "id": scenario_id,
                "summary": source.scenario,
                "atom_refs": [source.atom_id],
                "evidence_refs": [raw_id],
            }
        ],
        "l3_profile_claims": profile_claims,
        "mermaid_canvas_refs": [
            {
                "id": canvas_id,
                "path": source.canvas_ref,
                "atom_refs": [source.atom_id],
                "evidence_refs": [raw_id],
            }
        ],
    }


def validate_evidence_memory_document(root: str | Path, input_path: str | Path) -> EvidenceMemoryValidationResult:
    root_path = Path(root).resolve()
    document_path = _resolve_existing_file(root_path, input_path, "evidence memory")
    document = _read_json_mapping(document_path)
    _validate_schema(root_path, document)
    _validate_document_paths(root_path, document)
    record_count = sum(len(document.get(field_name, [])) for field_name in _record_array_fields())
    return EvidenceMemoryValidationResult(
        schema_version=str(document["schema_version"]),
        record_count=record_count,
    )


def validate_workflow_memory_record(
    *,
    record_type: str,
    payload: dict[str, Any],
    citations: list[str] | None,
) -> None:
    if record_type not in WORKFLOW_MEMORY_RECORD_TYPES:
        raise EvidenceMemoryValidationError(f"Unsupported workflow memory record_type: {record_type}")
    if not _has_trace_link(payload, citations or []):
        raise EvidenceMemoryValidationError(
            "workflow memory payload must include a raw evidence, canonical artifact, or lower-level trace ref"
        )


def _read_json_mapping(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise EvidenceMemoryValidationError(f"{path} could not be parsed as JSON: {error}") from error
    except OSError as error:
        raise EvidenceMemoryValidationError(f"{path} could not be read: {error}") from error
    if not isinstance(data, dict):
        raise EvidenceMemoryValidationError(f"{path} must contain a JSON object")
    return data


def _validate_schema(root: Path, document: dict[str, Any]) -> None:
    schema_path = root / "spec" / SCHEMA_NAME
    if not schema_path.is_file():
        schema_path = Path(__file__).resolve().parents[1] / "spec" / SCHEMA_NAME
    if not schema_path.is_file():
        raise EvidenceMemoryValidationError(f"schema not found: {SCHEMA_NAME}")

    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = jsonschema.Draft7Validator(schema)
    errors = sorted(validator.iter_errors(document), key=lambda item: list(item.path))
    if errors:
        first = errors[0]
        location = ".".join(str(part) for part in first.path) or "<root>"
        raise EvidenceMemoryValidationError(f"schema validation failed at {location}: {first.message}")


def _validate_document_paths(root: Path, document: dict[str, Any]) -> None:
    for field_name in ("l0_raw_evidence_refs", "canonical_artifacts", "mermaid_canvas_refs"):
        for index, item in enumerate(document.get(field_name, [])):
            _resolve_workspace_path(root, item["path"], f"{field_name}[{index}].path")


def _has_trace_link(payload: dict[str, Any], citations: list[str]) -> bool:
    if citations:
        return True
    for key, value in payload.items():
        if key not in TRACE_LINK_KEYS:
            continue
        if isinstance(value, str) and value.strip():
            return True
        if isinstance(value, list) and value:
            return True
    return False


def _record_array_fields() -> tuple[str, ...]:
    return (
        "l0_raw_evidence_refs",
        "canonical_artifacts",
        "l1_atoms",
        "l2_scenarios",
        "l3_profile_claims",
        "mermaid_canvas_refs",
    )


def _resolve_existing_file(root: Path, path_value: str | Path, label: str) -> Path:
    path = Path(path_value)
    if not path.is_absolute():
        path = root / path
    resolved = path.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as error:
        raise EvidenceMemoryValidationError(f"{label} path escapes workspace: {path_value}") from error
    if not resolved.is_file():
        raise EvidenceMemoryValidationError(f"{label} file does not exist: {path_value}")
    return resolved


def _resolve_workspace_path(root: Path, path_value: str, label: str) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        raise EvidenceMemoryValidationError(f"{label} escapes workspace: {path_value}")
    resolved = (root / path).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as error:
        raise EvidenceMemoryValidationError(f"{label} escapes workspace: {path_value}") from error
    return resolved
