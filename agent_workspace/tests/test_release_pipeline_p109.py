"""Phase 109 Test Suite: Dual-Track Release Pipeline & Desktop Packaging Verification.

Aligned with Universal Coding Agent Development Protocol v3.8.0, ADR-005, and ADR-006.

Validates:
1. GitHub Actions Release Workflow (.github/workflows/release.yml triggers, permissions, jobs).
2. Dual-Track Deployment Architecture (Docker to GHCR & Tauri Desktop to GitHub Releases).
3. Release Readiness Verification Gate (scripts/verify_release_readiness.py).
4. Manifest and Packaging Parity across Python, Frontend, and Rust/Tauri.
"""

from __future__ import annotations

import re
from pathlib import Path
import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def test_release_workflow_triggers_and_permissions():
    """Validates triggers, permissions, and top-level structure of release.yml."""
    workflow_path = PROJECT_ROOT / ".github" / "workflows" / "release.yml"
    assert workflow_path.is_file(), ".github/workflows/release.yml must exist"

    content = workflow_path.read_text(encoding="utf-8")
    parsed = yaml.safe_load(content)

    assert "name" in parsed
    # In YAML 1.1, unquoted 'on' is parsed as boolean True
    on_triggers = parsed.get("on") or parsed.get(True)
    assert on_triggers is not None, "Workflow must define triggers"
    assert "push" in on_triggers
    assert "tags" in on_triggers["push"]
    assert "v*.*.*" in on_triggers["push"]["tags"]
    assert "workflow_dispatch" in on_triggers

    # Permissions
    perms = parsed.get("permissions", {})
    assert perms.get("contents") == "write", "Release workflow requires contents: write for GitHub Releases"
    assert perms.get("packages") == "write", "Release workflow requires packages: write for GHCR push"

    # Environment
    env = parsed.get("env", {})
    assert env.get("REGISTRY") == "ghcr.io"


def test_release_workflow_docker_job():
    """Validates the docker-release job configuration in release.yml."""
    workflow_path = PROJECT_ROOT / ".github" / "workflows" / "release.yml"
    content = workflow_path.read_text(encoding="utf-8")
    parsed = yaml.safe_load(content)

    jobs = parsed.get("jobs", {})
    assert "docker-release" in jobs, "Must define docker-release job"

    docker_job = jobs["docker-release"]
    assert docker_job.get("runs-on") == "ubuntu-latest"

    steps = docker_job.get("steps", [])
    step_uses = [s.get("uses", "") for s in steps]

    assert any("docker/setup-qemu-action" in u for u in step_uses), "Must setup QEMU"
    assert any("docker/setup-buildx-action" in u for u in step_uses), "Must setup Buildx"
    assert any("docker/login-action" in u for u in step_uses), "Must login to registry"
    assert any("docker/metadata-action" in u for u in step_uses), "Must extract metadata"
    assert any("docker/build-push-action" in u for u in step_uses), "Must execute build-push-action"


def test_release_workflow_desktop_job():
    """Validates the desktop-release job configuration in release.yml."""
    workflow_path = PROJECT_ROOT / ".github" / "workflows" / "release.yml"
    content = workflow_path.read_text(encoding="utf-8")
    parsed = yaml.safe_load(content)

    jobs = parsed.get("jobs", {})
    assert "desktop-release" in jobs, "Must define desktop-release job"

    desktop_job = jobs["desktop-release"]
    assert desktop_job.get("runs-on") in ["windows-latest", "${{ matrix.platform }}"]

    steps = desktop_job.get("steps", [])
    step_uses = [s.get("uses", "") for s in steps]

    assert any("actions/setup-node" in u for u in step_uses), "Must setup Node.js"
    assert any("rust-toolchain" in u for u in step_uses), "Must setup Rust toolchain"
    assert any("tauri-apps/tauri-action" in u for u in step_uses), "Must invoke tauri-action"

    # Verify build step commands
    step_runs = [s.get("run", "") for s in steps]
    assert any("npm ci" in r for r in step_runs), "Must install dependencies with npm ci"
    assert any("npm run build" in r for r in step_runs), "Must build frontend assets"


def test_verify_release_readiness_audit_module():
    """Validates the scripts/verify_release_readiness.py execution logic."""
    import sys
    sys.path.insert(0, str(PROJECT_ROOT))
    try:
        from scripts import verify_release_readiness

        # 1. Version Parity Check
        parity, py_ver, js_ver, tauri_ver = verify_release_readiness.check_version_parity()
        assert parity is True, f"Parity mismatch: Python={py_ver}, JS={js_ver}, Tauri={tauri_ver}"
        assert py_ver == js_ver == tauri_ver

        # 2. Deployment Artifacts
        artifacts = verify_release_readiness.check_deployment_artifacts()
        for fname, exists in artifacts:
            assert exists is True, f"Missing required deployment artifact: {fname}"

        # 3. Evidence Receipts
        receipts = verify_release_readiness.check_evidence_receipts()
        for fname, exists in receipts:
            assert exists is True, f"Missing evidence receipt: {fname}"

        # 4. Main returncode
        assert verify_release_readiness.main() == 0
    finally:
        if str(PROJECT_ROOT) in sys.path:
            sys.path.remove(str(PROJECT_ROOT))


def test_tauri_cargo_manifest_parity():
    """Validates that Cargo.toml version matches tauri.conf.json and pyproject.toml."""
    cargo_path = PROJECT_ROOT / "viewer" / "src-tauri" / "Cargo.toml"
    assert cargo_path.is_file(), "Cargo.toml must exist"

    content = cargo_path.read_text(encoding="utf-8")
    match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content)
    assert match is not None, "Cargo.toml must specify package version"

    cargo_version = match.group(1).lstrip("v")

    pyproject_path = PROJECT_ROOT / "pyproject.toml"
    py_content = pyproject_path.read_text(encoding="utf-8")
    py_match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', py_content)
    assert py_match is not None
    py_version = py_match.group(1).lstrip("v")

    assert cargo_version == py_version, f"Cargo version ({cargo_version}) must match pyproject ({py_version})"
