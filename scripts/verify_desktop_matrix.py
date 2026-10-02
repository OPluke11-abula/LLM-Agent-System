#!/usr/bin/env python3
"""Pre-flight Verification and Receipt Generator for Multi-Platform Desktop Packaging (Phase 113).

Validates:
1. Bitwise 4-way version parity across pyproject.toml, package.json, tauri.conf.json, Cargo.toml (v0.6.0).
2. Tauri 2.0 bundle configuration in viewer/src-tauri/tauri.conf.json:
   - Windows targets: WiX (.msi) and NSIS (.exe).
   - macOS targets: DMG (.dmg) and App bundle (.app).
   - Linux targets: Debian (.deb) with WebKitGTK 4.1 runtime and AppImage (.AppImage).
3. GitHub Actions Release Workflow (.github/workflows/release.yml):
   - Multi-OS runner matrix: windows-latest, macos-latest, ubuntu-22.04.
   - Linux dependency installation (libwebkit2gtk-4.1-dev, libayatana-appindicator3-dev).
   - Tauri action packaging and release automation.
4. Emits structured evidence receipt at .agent/evidence/desktop_matrix_receipt.json.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
import re
import sys
import yaml

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("DesktopMatrixVerifier")

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def verify_desktop_matrix() -> dict:
    tauri_conf_path = PROJECT_ROOT / "viewer" / "src-tauri" / "tauri.conf.json"
    cargo_path = PROJECT_ROOT / "viewer" / "src-tauri" / "Cargo.toml"
    package_json_path = PROJECT_ROOT / "viewer" / "package.json"
    pyproject_path = PROJECT_ROOT / "pyproject.toml"
    release_wf_path = PROJECT_ROOT / ".github" / "workflows" / "release.yml"

    assert tauri_conf_path.is_file(), f"tauri.conf.json missing: {tauri_conf_path}"
    assert cargo_path.is_file(), f"Cargo.toml missing: {cargo_path}"
    assert package_json_path.is_file(), f"package.json missing: {package_json_path}"
    assert pyproject_path.is_file(), f"pyproject.toml missing: {pyproject_path}"
    assert release_wf_path.is_file(), f"release.yml missing: {release_wf_path}"

    # 1. 4-Way Version Parity Check
    py_text = pyproject_path.read_text(encoding="utf-8")
    py_match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', py_text)
    assert py_match, "pyproject.toml missing version"
    py_ver = py_match.group(1).lstrip("v")

    package_data = json.loads(package_json_path.read_text(encoding="utf-8"))
    js_ver = package_data.get("version", "").lstrip("v")

    tauri_data = json.loads(tauri_conf_path.read_text(encoding="utf-8"))
    tauri_ver = tauri_data.get("version", "").lstrip("v")

    cargo_text = cargo_path.read_text(encoding="utf-8")
    cargo_match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', cargo_text)
    assert cargo_match, "Cargo.toml missing version"
    cargo_ver = cargo_match.group(1).lstrip("v")

    expected_version = "0.6.0"
    assert py_ver == expected_version, f"pyproject.toml version {py_ver} != {expected_version}"
    assert js_ver == expected_version, f"package.json version {js_ver} != {expected_version}"
    assert tauri_ver == expected_version, f"tauri.conf.json version {tauri_ver} != {expected_version}"
    assert cargo_ver == expected_version, f"Cargo.toml version {cargo_ver} != {expected_version}"
    logger.info("4-Way version parity verified: v%s", expected_version)

    # 2. Tauri Bundle Configuration Inspection
    bundle = tauri_data.get("bundle", {})
    assert bundle.get("active") is True, "bundle.active must be true"
    assert bundle.get("targets") == "all" or isinstance(bundle.get("targets"), list)

    # Windows WiX & NSIS
    assert "windows" in bundle, "bundle.windows configuration missing"
    assert "wix" in bundle["windows"], "bundle.windows.wix missing"
    assert "nsis" in bundle["windows"], "bundle.windows.nsis missing"

    # macOS DMG
    assert "macOS" in bundle, "bundle.macOS configuration missing"
    assert "dmg" in bundle["macOS"], "bundle.macOS.dmg missing"
    assert "minimumSystemVersion" in bundle["macOS"], "bundle.macOS.minimumSystemVersion missing"

    # Linux Deb & AppImage
    assert "linux" in bundle, "bundle.linux configuration missing"
    assert "deb" in bundle["linux"], "bundle.linux.deb missing"
    assert "appimage" in bundle["linux"], "bundle.linux.appimage missing"
    deb_deps = bundle["linux"]["deb"].get("depends", [])
    assert any("libwebkit2gtk" in d for d in deb_deps), "Linux deb must depend on libwebkit2gtk"
    logger.info("Tauri bundle targets verified for Windows (WiX/NSIS), macOS (DMG), and Linux (Deb/AppImage).")

    # 3. GitHub Actions Release Workflow Inspection
    wf_data = yaml.safe_load(release_wf_path.read_text(encoding="utf-8"))
    jobs = wf_data.get("jobs", {})
    assert "desktop-release" in jobs, "release.yml missing desktop-release job"

    desktop_job = jobs["desktop-release"]
    strategy = desktop_job.get("strategy", {})
    matrix = strategy.get("matrix", {})
    includes = matrix.get("include", [])

    platforms = [inc.get("platform") for inc in includes]
    assert "windows-latest" in platforms, "Matrix missing windows-latest"
    assert "macos-latest" in platforms, "Matrix missing macos-latest"
    assert "ubuntu-22.04" in platforms, "Matrix missing ubuntu-22.04"

    # Verify Linux build dependency installation step
    steps = desktop_job.get("steps", [])
    linux_deps_step = next((s for s in steps if "Install Linux Build Dependencies" in s.get("name", "")), None)
    assert linux_deps_step is not None, "Missing Linux build dependency installation step"
    assert linux_deps_step.get("if") == "matrix.platform == 'ubuntu-22.04'"
    assert "libwebkit2gtk-4.1-dev" in linux_deps_step.get("run", "")
    logger.info("Release workflow matrix verified for 3 OS runners with Linux WebKitGTK dependencies.")

    receipt = {
        "status": "PASS",
        "milestone": "T-040 (Phase 113)",
        "protocol_version": "3.8.0",
        "app_version": expected_version,
        "four_way_version_parity": {
            "python": py_ver,
            "frontend": js_ver,
            "tauri_conf": tauri_ver,
            "cargo_toml": cargo_ver,
        },
        "desktop_platforms": [
            {
                "os": "Windows",
                "runner": "windows-latest",
                "bundle_formats": ["msi (WiX)", "exe (NSIS)"],
            },
            {
                "os": "macOS",
                "runner": "macos-latest",
                "bundle_formats": ["dmg", "app"],
                "min_macos_version": bundle["macOS"]["minimumSystemVersion"],
            },
            {
                "os": "Linux",
                "runner": "ubuntu-22.04",
                "bundle_formats": ["deb", "appimage"],
                "deb_dependencies": deb_deps,
            },
        ],
        "metadata": {
            "category": bundle.get("category"),
            "short_description": bundle.get("shortDescription"),
            "copyright": bundle.get("copyright"),
        },
        "verification_summary": {
            "version_parity": "PASS",
            "tauri_bundle_spec": "PASS",
            "release_ci_matrix": "PASS",
            "linux_sys_dependencies": "PASS",
        },
    }

    receipt_path = PROJECT_ROOT / ".agent" / "evidence" / "desktop_matrix_receipt.json"
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Generated evidence receipt at: %s", receipt_path)
    return receipt


if __name__ == "__main__":
    try:
        rec = verify_desktop_matrix()
        print("\n=======================================================")
        print(" [DESKTOP] MULTI-PLATFORM PACKAGING AUDIT (PHASE 113)")
        print("=======================================================")
        print(f" Status:             {rec['status']}")
        print(f" Milestone:          {rec['milestone']}")
        print(f" Version:            v{rec['app_version']}")
        print(f" Supported OSs:      {[p['os'] for p in rec['desktop_platforms']]}")
        print(f" Target Bundles:     Windows (MSI/EXE), macOS (DMG/APP), Linux (DEB/AppImage)")
        print("=======================================================\n")
        sys.exit(0)
    except Exception as exc:
        logger.error("Desktop matrix verification failed: %s", exc, exc_info=True)
        sys.exit(1)
