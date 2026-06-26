import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from agent_workspace.tool_manifest import (
    parse_requirements,
    parse_pyproject_dependencies,
    audit_dependency_license,
    audit_licenses,
)


def test_parse_requirements(tmp_path):
    req_file = tmp_path / "requirements.txt"
    req_file.write_text(
        "# Some comment\n"
        "pydantic>=2.0.0\n"
        "fastapi[standard]>=0.115.0\n"
        "  \n"
        "watchdog==3.0.0\n",
        encoding="utf-8"
    )

    packages = parse_requirements(req_file)
    assert sorted(packages) == ["fastapi", "pydantic", "watchdog"]


def test_parse_pyproject_dependencies_pep621(tmp_path):
    pyproject_file = tmp_path / "pyproject.toml"
    pyproject_file.write_text(
        "[project]\n"
        "name = \"my-project\"\n"
        "dependencies = [\n"
        "    \"jinja2>=3.0.0\",\n"
        "    'cryptography>=41.0.0'\n"
        "]\n",
        encoding="utf-8"
    )

    packages = parse_pyproject_dependencies(pyproject_file)
    assert sorted(packages) == ["cryptography", "jinja2"]


def test_parse_pyproject_dependencies_poetry(tmp_path):
    pyproject_file = tmp_path / "pyproject.toml"
    pyproject_file.write_text(
        "[tool.poetry.dependencies]\n"
        "python = \"^3.9\"\n"
        "redis = \"^5.0.0\"\n",
        encoding="utf-8"
    )

    packages = parse_pyproject_dependencies(pyproject_file)
    assert sorted(packages) == ["python", "redis"]


@patch("importlib.metadata.distribution")
def test_audit_dependency_license_allow(mock_dist):
    # Mocking standard MIT license
    mock_metadata = MagicMock()
    mock_metadata.get.return_value = "MIT"
    mock_metadata.get_all.return_value = ["License :: OSI Approved :: MIT License"]
    mock_dist.return_value.metadata = mock_metadata

    status, lic = audit_dependency_license("pydantic")
    assert status == "ALLOW"
    assert "MIT" in lic


@patch("importlib.metadata.distribution")
def test_audit_dependency_license_warn(mock_dist):
    # Mocking PolyForm license
    mock_metadata = MagicMock()
    mock_metadata.get.return_value = "PolyForm Noncommercial 1.0.0"
    mock_metadata.get_all.return_value = []
    mock_dist.return_value.metadata = mock_metadata

    status, lic = audit_dependency_license("some-polyform-pkg")
    assert status == "WARN"
    assert "PolyForm" in lic


@patch("importlib.metadata.distribution")
def test_audit_dependency_license_deny(mock_dist):
    # Mocking GPL license
    mock_metadata = MagicMock()
    mock_metadata.get.return_value = "GPL v3"
    mock_metadata.get_all.return_value = ["License :: OSI Approved :: GNU General Public License v3 (GPLv3)"]
    mock_dist.return_value.metadata = mock_metadata

    # By default, copyleft is not blocked unless specified
    status, lic = audit_dependency_license("gpl-pkg", block_copyleft=False)
    assert status == "ALLOW"

    # Block copyleft
    status, lic = audit_dependency_license("gpl-pkg", block_copyleft=True)
    assert status == "DENY"


@patch("importlib.metadata.distribution")
def test_audit_dependency_license_unknown(mock_dist):
    # Mocking unknown license
    mock_metadata = MagicMock()
    mock_metadata.get.return_value = "MyCustomNonStandardLicense"
    mock_metadata.get_all.return_value = []
    mock_dist.return_value.metadata = mock_metadata

    status, lic = audit_dependency_license("custom-pkg")
    assert status == "UNKNOWN"
    assert lic == "MyCustomNonStandardLicense"


def test_audit_dependency_license_not_installed():
    # Package not installed raises PackageNotFoundError
    status, lic = audit_dependency_license("pkg-that-does-not-exist")
    assert status == "UNKNOWN"
    assert lic is None


@patch("importlib.metadata.distribution")
def test_audit_licenses_combined(mock_dist, tmp_path):
    mock_metadata = MagicMock()
    mock_metadata.get.return_value = "Apache 2.0"
    mock_metadata.get_all.return_value = []
    mock_dist.return_value.metadata = mock_metadata

    req_file = tmp_path / "requirements.txt"
    req_file.write_text("jinja2>=3.0.0\n", encoding="utf-8")

    results = audit_licenses(tmp_path)
    assert "jinja2" in results
    assert results["jinja2"][0] == "ALLOW"
