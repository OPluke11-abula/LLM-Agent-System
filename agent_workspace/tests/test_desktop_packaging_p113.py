"""Phase 113 Test Suite: Multi-Platform Desktop Packaging & Release Matrix Verification.

Validates:
1. Four-way semantic version parity (v0.6.0) across Python, Frontend, Tauri, and Cargo manifests.
2. Tauri 2.0 configuration bundle invariants for Windows (WiX/NSIS), macOS (DMG), and Linux (DEB/AppImage).
3. GitHub Actions multi-OS release matrix (windows-latest, macos-latest, ubuntu-22.04) and Linux dependencies.
4. Desktop matrix pre-flight verification script execution and evidence receipt generation.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def test_four_way_version_parity():
    """Verify bitwise semantic version consistency across all 4 project manifests."""
    pyproject_text = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    py_match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', pyproject_text)
    assert py_match is not None, "pyproject.toml missing version"
    py_ver = py_match.group(1).lstrip("v")

    package_data = json.loads((PROJECT_ROOT / "viewer" / "package.json").read_text(encoding="utf-8"))
    js_ver = package_data.get("version", "").lstrip("v")

    tauri_data = json.loads((PROJECT_ROOT / "viewer" / "src-tauri" / "tauri.conf.json").read_text(encoding="utf-8"))
    tauri_ver = tauri_data.get("version", "").lstrip("v")

    cargo_text = (PROJECT_ROOT / "viewer" / "src-tauri" / "Cargo.toml").read_text(encoding="utf-8")
    cargo_match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', cargo_text)
    assert cargo_match is not None, "Cargo.toml missing version"
    cargo_ver = cargo_match.group(1).lstrip("v")

    assert py_ver == js_ver == tauri_ver == cargo_ver == "0.6.0"


def test_tauri_bundle_configuration_invariants():
    """Verify Tauri bundle target settings for Windows, macOS, and Linux."""
    tauri_file = PROJECT_ROOT / "viewer" / "src-tauri" / "tauri.conf.json"
    data = json.loads(tauri_file.read_text(encoding="utf-8"))

    bundle = data.get("bundle", {})
    assert bundle.get("active") is True
    assert bundle.get("category") == "DeveloperTool"
    assert "LLM-Agent-System" in bundle.get("longDescription", "")

    # Windows WiX & NSIS
    windows_conf = bundle.get("windows", {})
    assert "wix" in windows_conf
    assert "nsis" in windows_conf
    assert windows_conf["nsis"].get("installMode") == "currentUser"

    # macOS DMG
    macos_conf = bundle.get("macOS", {})
    assert "dmg" in macos_conf
    assert macos_conf.get("minimumSystemVersion") == "10.13"

    # Linux Deb & AppImage
    linux_conf = bundle.get("linux", {})
    assert "deb" in linux_conf
    assert "appimage" in linux_conf
    deb_deps = linux_conf["deb"].get("depends", [])
    assert any("libwebkit2gtk" in dep for dep in deb_deps)


def test_github_actions_desktop_release_matrix():
    """Verify GitHub Actions release workflow matrix across Windows, macOS, and Linux."""
    workflow_path = PROJECT_ROOT / ".github" / "workflows" / "release.yml"
    parsed = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))

    jobs = parsed.get("jobs", {})
    assert "desktop-release" in jobs

    desktop_job = jobs["desktop-release"]
    strategy = desktop_job.get("strategy", {})
    matrix = strategy.get("matrix", {})
    includes = matrix.get("include", [])

    platforms = {item.get("platform") for item in includes}
    assert "windows-latest" in platforms
    assert "macos-latest" in platforms
    assert "ubuntu-22.04" in platforms

    # Ensure runs-on targets matrix
    assert desktop_job.get("runs-on") in ["${{ matrix.platform }}", "windows-latest"]

    # Verify Linux build dependency installation step
    steps = desktop_job.get("steps", [])
    linux_step = next((s for s in steps if "Install Linux Build Dependencies" in s.get("name", "")), None)
    assert linux_step is not None
    assert "libwebkit2gtk-4.1-dev" in linux_step.get("run", "")


def test_verify_desktop_matrix_script_and_receipt():
    """Verify that scripts/verify_desktop_matrix.py generates valid evidence receipt."""
    import sys
    sys.path.insert(0, str(PROJECT_ROOT))
    try:
        from scripts import verify_desktop_matrix

        receipt = verify_desktop_matrix.verify_desktop_matrix()
        assert receipt["status"] == "PASS"
        assert receipt["milestone"] == "T-040 (Phase 113)"
        assert receipt["app_version"] == "0.6.0"

        platforms = [p["os"] for p in receipt["desktop_platforms"]]
        assert "Windows" in platforms
        assert "macOS" in platforms
        assert "Linux" in platforms

        receipt_file = PROJECT_ROOT / ".agent" / "evidence" / "desktop_matrix_receipt.json"
        assert receipt_file.is_file()
    finally:
        if str(PROJECT_ROOT) in sys.path:
            sys.path.remove(str(PROJECT_ROOT))
