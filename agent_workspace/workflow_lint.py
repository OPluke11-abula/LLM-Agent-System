"""Read-only validator for PAP workflow manifests and checkpoints."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Any

import jsonschema
import yaml


class WorkflowLintError(ValueError):
    """Raised when a workflow manifest or checkpoint is invalid."""


@dataclass(frozen=True)
class WorkflowLintResult:
    workflow_id: str
    stage_count: int
    checkpoint_count: int


def lint_workflow(
    root: str | Path,
    workflow_path: str | Path,
    checkpoint_paths: Iterable[str | Path] | None = None,
) -> WorkflowLintResult:
    """Validate a workflow manifest and optional checkpoint records without executing stages."""

    root_path = Path(root).resolve()
    manifest_path = _resolve_existing_file(root_path, workflow_path, "workflow")
    manifest = _read_yaml_mapping(manifest_path)
    _validate_schema(root_path, "workflow-stage.schema.json", manifest)

    stages = manifest.get("stages", [])
    stage_ids = _validate_stage_graph(stages)
    _validate_manifest_paths(root_path, stages)

    checkpoint_count = 0
    for checkpoint_path in checkpoint_paths or []:
        resolved_checkpoint = _resolve_existing_file(root_path, checkpoint_path, "checkpoint")
        checkpoint = _read_yaml_mapping(resolved_checkpoint)
        _validate_schema(root_path, "checkpoint.schema.json", checkpoint)
        _validate_checkpoint(root_path, manifest["id"], stage_ids, checkpoint)
        checkpoint_count += 1

    return WorkflowLintResult(
        workflow_id=str(manifest["id"]),
        stage_count=len(stages),
        checkpoint_count=checkpoint_count,
    )


def _read_yaml_mapping(path: Path) -> dict[str, Any]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as error:
        raise WorkflowLintError(f"{path} could not be parsed as YAML: {error}") from error
    if not isinstance(data, dict):
        raise WorkflowLintError(f"{path} must contain a YAML mapping")
    return data


def _validate_schema(root: Path, schema_name: str, data: dict[str, Any]) -> None:
    schema_path = root / "spec" / schema_name
    if not schema_path.is_file():
        schema_path = Path(__file__).resolve().parents[1] / "spec" / schema_name
    if not schema_path.is_file():
        raise WorkflowLintError(f"schema not found: {schema_name}")

    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    try:
        jsonschema.validate(instance=data, schema=schema)
    except jsonschema.exceptions.ValidationError as error:
        raise WorkflowLintError(f"schema validation failed: {error.message}") from error


def _validate_stage_graph(stages: list[dict[str, Any]]) -> set[str]:
    stage_ids: set[str] = set()
    for stage in stages:
        stage_id = stage["id"]
        if stage_id in stage_ids:
            raise WorkflowLintError(f"duplicate stage id: {stage_id}")
        stage_ids.add(stage_id)

    for stage in stages:
        for dependency in stage.get("requires", []):
            if dependency not in stage_ids:
                raise WorkflowLintError(f"stage {stage['id']} has unknown dependency: {dependency}")
            if dependency == stage["id"]:
                raise WorkflowLintError(f"stage {stage['id']} cannot depend on itself")

    dependencies = {stage["id"]: set(stage.get("requires", [])) for stage in stages}
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(stage_id: str) -> None:
        if stage_id in visiting:
            raise WorkflowLintError(f"stage dependency cycle detected at: {stage_id}")
        if stage_id in visited:
            return
        visiting.add(stage_id)
        for dependency in dependencies[stage_id]:
            visit(dependency)
        visiting.remove(stage_id)
        visited.add(stage_id)

    for stage_id in dependencies:
        visit(stage_id)
    return stage_ids


def _validate_manifest_paths(root: Path, stages: list[dict[str, Any]]) -> None:
    for stage in stages:
        _resolve_workspace_path(root, stage["produces"], f"stage {stage['id']} produces")
        director_doc = _resolve_workspace_path(root, stage["director_doc"], f"stage {stage['id']} director_doc")
        if not director_doc.is_file():
            raise WorkflowLintError(f"stage {stage['id']} director_doc does not exist: {stage['director_doc']}")


def _validate_checkpoint(
    root: Path,
    workflow_id: str,
    stage_ids: set[str],
    checkpoint: dict[str, Any],
) -> None:
    if checkpoint["workflow_id"] != workflow_id:
        raise WorkflowLintError(
            f"checkpoint workflow_id {checkpoint['workflow_id']} does not match manifest {workflow_id}"
        )
    if checkpoint["stage_id"] not in stage_ids:
        raise WorkflowLintError(f"checkpoint references unknown stage: {checkpoint['stage_id']}")

    _resolve_workspace_path(root, checkpoint["artifact_path"], "checkpoint artifact_path")
    for ref in checkpoint.get("evidence_refs", []):
        _resolve_workspace_path(root, ref, "checkpoint evidence_ref")


def _resolve_existing_file(root: Path, path_value: str | Path, label: str) -> Path:
    path = Path(path_value)
    if not path.is_absolute():
        path = root / path
    resolved = path.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as error:
        raise WorkflowLintError(f"{label} path escapes workspace: {path_value}") from error
    if not resolved.is_file():
        raise WorkflowLintError(f"{label} file does not exist: {path_value}")
    return resolved


def _resolve_workspace_path(root: Path, path_value: str, label: str) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        raise WorkflowLintError(f"{label} escapes workspace: {path_value}")
    resolved = (root / path).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as error:
        raise WorkflowLintError(f"{label} escapes workspace: {path_value}") from error
    return resolved


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate LAS/PAP workflow manifests and checkpoints.")
    parser.add_argument("--root", default=".", help="Workspace root. Defaults to current directory.")
    parser.add_argument("--workflow", required=True, help="Workflow manifest path.")
    parser.add_argument(
        "--checkpoint",
        action="append",
        default=[],
        help="Optional checkpoint YAML path. May be passed multiple times.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        result = lint_workflow(args.root, args.workflow, args.checkpoint)
    except WorkflowLintError as error:
        parser.exit(1, f"Workflow lint failed: {error}\n")

    print(
        f"Workflow valid: {result.workflow_id} "
        f"({result.stage_count} stage(s), {result.checkpoint_count} checkpoint(s))"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
