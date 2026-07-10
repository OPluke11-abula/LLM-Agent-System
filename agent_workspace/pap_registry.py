from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import jsonschema


class RegistryHubAuditError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class RegistryHubAuditResult:
    registry_version: str
    skill_count: int
    packaged_path_count: int


DEFAULT_REGISTRY_PATH = "registry/index.json"
SCHEMA_NAME = "registry-schema.json"
EXCLUDED_DIR_NAMES = frozenset({".git", "memory", "logs"})
EXCLUDED_FILE_NAMES = frozenset({".env"})
EXCLUDED_FILE_PREFIXES = (".env.",)
EXCLUDED_SUFFIXES = (
    ".db",
    ".db-shm",
    ".db-wal",
    ".log",
    ".sqlite",
    ".sqlite-shm",
    ".sqlite-wal",
    ".sqlite3",
    ".sqlite3-shm",
    ".sqlite3-wal",
)


def validate_registry_hub(
    root: str | Path,
    registry_path: str | Path = DEFAULT_REGISTRY_PATH,
    package_root: str | Path | None = None,
) -> RegistryHubAuditResult:
    root_path = Path(root).resolve()
    resolved_registry = _resolve_existing_file(root_path, registry_path, "registry")
    registry = _read_json_mapping(resolved_registry)
    _validate_registry_schema(root_path, registry)
    _validate_registry_entries(root_path, registry)

    packaged_path_count = 0
    if package_root is not None:
        resolved_package_root = _resolve_existing_dir(root_path, package_root, "package root")
        packaged_path_count = _audit_package_tree(root_path, resolved_package_root)

    return RegistryHubAuditResult(
        registry_version=str(registry["registry_version"]),
        skill_count=len(registry.get("skills", {})),
        packaged_path_count=packaged_path_count,
    )


def _read_json_mapping(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise RegistryHubAuditError(f"{path} could not be parsed as JSON: {error}") from error
    except OSError as error:
        raise RegistryHubAuditError(f"{path} could not be read: {error}") from error
    if not isinstance(data, dict):
        raise RegistryHubAuditError(f"{path} must contain a JSON object")
    return data


def _validate_registry_schema(root: Path, registry: dict[str, Any]) -> None:
    schema_path = root / "spec" / SCHEMA_NAME
    if not schema_path.is_file():
        schema_path = Path(__file__).resolve().parents[1] / "spec" / SCHEMA_NAME
    if not schema_path.is_file():
        raise RegistryHubAuditError(f"schema not found: {SCHEMA_NAME}")

    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = jsonschema.Draft7Validator(schema)
    errors = sorted(validator.iter_errors(registry), key=lambda item: list(item.path))
    if errors:
        first = errors[0]
        location = ".".join(str(part) for part in first.path) or "<root>"
        raise RegistryHubAuditError(f"schema validation failed at {location}: {first.message}")


def _validate_registry_entries(root: Path, registry: dict[str, Any]) -> None:
    skills = registry.get("skills", {})
    if not isinstance(skills, dict):
        raise RegistryHubAuditError("registry.skills must be an object")

    for skill_key, descriptor in skills.items():
        if not isinstance(descriptor, dict):
            raise RegistryHubAuditError(f"registry.skills.{skill_key} must be an object")
        descriptor_id = descriptor["id"]
        if descriptor_id != skill_key:
            raise RegistryHubAuditError(
                f"registry skill key {skill_key} must match descriptor id {descriptor_id}"
            )
        relative_path = _resolve_workspace_path(root, descriptor["path"], f"registry.skills.{skill_key}.path")
        _reject_public_package_exclusion(relative_path, f"registry.skills.{skill_key}.path")


def _audit_package_tree(root: Path, package_root: Path) -> int:
    checked = 0
    for path in package_root.rglob("*"):
        relative_to_root = path.resolve().relative_to(root)
        _reject_public_package_exclusion(relative_to_root, f"package path {relative_to_root.as_posix()}")
        checked += 1
    return checked


def _reject_public_package_exclusion(relative_path: Path, label: str) -> None:
    lower_parts = tuple(part.lower() for part in relative_path.parts)
    for part in lower_parts:
        if part in EXCLUDED_DIR_NAMES:
            raise RegistryHubAuditError(f"{label} uses excluded public package directory: {part}")

    file_name = relative_path.name.lower()
    if file_name in EXCLUDED_FILE_NAMES or file_name.startswith(EXCLUDED_FILE_PREFIXES):
        raise RegistryHubAuditError(f"{label} uses excluded public package file: {relative_path.name}")
    if file_name.endswith(EXCLUDED_SUFFIXES):
        raise RegistryHubAuditError(f"{label} uses excluded public package artifact: {relative_path.name}")


def _resolve_existing_file(root: Path, path_value: str | Path, label: str) -> Path:
    path = _resolve_input_path(root, path_value, label)
    if not path.is_file():
        raise RegistryHubAuditError(f"{label} file does not exist: {path_value}")
    return path


def _resolve_existing_dir(root: Path, path_value: str | Path, label: str) -> Path:
    path = _resolve_input_path(root, path_value, label)
    if not path.is_dir():
        raise RegistryHubAuditError(f"{label} directory does not exist: {path_value}")
    return path


def _resolve_input_path(root: Path, path_value: str | Path, label: str) -> Path:
    path = Path(path_value)
    if not path.is_absolute():
        path = root / path
    resolved = path.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as error:
        raise RegistryHubAuditError(f"{label} escapes workspace: {path_value}") from error
    return resolved


def _resolve_workspace_path(root: Path, path_value: str | Path, label: str) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        raise RegistryHubAuditError(f"{label} escapes workspace: {path_value}")
    resolved = (root / path).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as error:
        raise RegistryHubAuditError(f"{label} escapes workspace: {path_value}") from error
    return resolved


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate PAP registry indexes and staged Hub packages.")
    parser.add_argument("--root", default=".", help="Workspace root. Defaults to current directory.")
    parser.add_argument(
        "--registry",
        default=DEFAULT_REGISTRY_PATH,
        help=f"Registry index path. Defaults to {DEFAULT_REGISTRY_PATH}.",
    )
    parser.add_argument(
        "--package-root",
        help="Optional staged public package directory to audit for Hub exclusion rules.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        result = validate_registry_hub(args.root, args.registry, args.package_root)
    except RegistryHubAuditError as error:
        parser.exit(1, f"PAP registry/hub validation failed: {error}\n")

    print(
        f"PAP registry/hub valid: {result.registry_version} "
        f"({result.skill_count} skill(s), {result.packaged_path_count} package path(s) audited)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
