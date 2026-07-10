import json
from pathlib import Path

import pytest

from agent_workspace.pap_registry import RegistryHubAuditError, main, validate_registry_hub


def _write_json(path: Path, data: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def _registry(skills: dict | None = None) -> dict:
    return {
        "registry_version": "1.0.0",
        "skills": skills or {},
    }


def _skill_descriptor(path: str = ".agent/skills/calculate.md") -> dict:
    return {
        "id": "calculate",
        "name": "Calculate",
        "version": "1.0.0",
        "description": "Evaluate a bounded arithmetic expression.",
        "author": "LAS",
        "path": path,
    }


def test_validate_registry_hub_accepts_empty_registry(tmp_path):
    registry = _write_json(tmp_path / "registry" / "index.json", _registry())

    result = validate_registry_hub(tmp_path, registry)

    assert result.registry_version == "1.0.0"
    assert result.skill_count == 0
    assert result.packaged_path_count == 0


def test_validate_registry_hub_accepts_skill_descriptor(tmp_path):
    skill_path = tmp_path / ".agent" / "skills" / "calculate.md"
    skill_path.parent.mkdir(parents=True, exist_ok=True)
    skill_path.write_text("# calculate\n", encoding="utf-8")
    registry = _write_json(
        tmp_path / "registry" / "index.json",
        _registry({"calculate": _skill_descriptor()}),
    )

    result = validate_registry_hub(tmp_path, registry)

    assert result.skill_count == 1


def test_validate_registry_hub_rejects_missing_required_descriptor_field(tmp_path):
    descriptor = _skill_descriptor()
    descriptor.pop("path")
    registry = _write_json(tmp_path / "registry" / "index.json", _registry({"calculate": descriptor}))

    with pytest.raises(RegistryHubAuditError, match="schema validation failed"):
        validate_registry_hub(tmp_path, registry)


def test_validate_registry_hub_rejects_descriptor_path_escape(tmp_path):
    descriptor = _skill_descriptor("../outside.md")
    registry = _write_json(tmp_path / "registry" / "index.json", _registry({"calculate": descriptor}))

    with pytest.raises(RegistryHubAuditError, match="escapes workspace"):
        validate_registry_hub(tmp_path, registry)


def test_validate_registry_hub_rejects_descriptor_memory_path(tmp_path):
    descriptor = _skill_descriptor(".agent/memory/private.md")
    registry = _write_json(tmp_path / "registry" / "index.json", _registry({"calculate": descriptor}))

    with pytest.raises(RegistryHubAuditError, match="excluded public package directory"):
        validate_registry_hub(tmp_path, registry)


def test_validate_registry_hub_rejects_staged_package_exclusions(tmp_path):
    registry = _write_json(tmp_path / "registry" / "index.json", _registry())
    package_root = tmp_path / "package"
    package_root.mkdir()
    (package_root / "agent.md").write_text("# public\n", encoding="utf-8")
    (package_root / ".env").write_text("TOKEN=fake\n", encoding="utf-8")

    with pytest.raises(RegistryHubAuditError, match="excluded public package file"):
        validate_registry_hub(tmp_path, registry, package_root)


def test_validate_registry_hub_rejects_staged_sqlite_artifact(tmp_path):
    registry = _write_json(tmp_path / "registry" / "index.json", _registry())
    package_root = tmp_path / "package"
    package_root.mkdir()
    (package_root / "cache.sqlite").write_text("", encoding="utf-8")

    with pytest.raises(RegistryHubAuditError, match="excluded public package artifact"):
        validate_registry_hub(tmp_path, registry, package_root)


def test_pap_registry_cli_accepts_default_registry(tmp_path):
    _write_json(tmp_path / "registry" / "index.json", _registry())

    assert main(["--root", str(tmp_path)]) == 0
