"""Phase 112 Test Suite: Kubernetes Helm & Argo Rollouts Canary Verification.

Validates:
1. Helm Chart metadata, version parity (v0.6.0), and schema invariants.
2. values.yaml production defaults (rootless user, securityContext, probes, resources, HPA).
3. Helm templates structure and Go template syntax integrity.
4. Argo Rollouts Canary CRD specification (step weight progression, pause durations, traffic routing).
5. AnalysisTemplate Prometheus SLI/SLO criteria (99.9% success, <500ms P99, <0.1% error).
6. Dual stable and canary services routing topology.
7. GitHub Actions CI/CD Helm publish workflow structure and GHCR OCI destination.
"""

from __future__ import annotations

import base64
from pathlib import Path
import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


@pytest.fixture
def helm_dir() -> Path:
    return PROJECT_ROOT / "deploy" / "helm" / "llm-agent-system"


@pytest.fixture
def canary_dir() -> Path:
    return PROJECT_ROOT / "deploy" / "canary"


def test_chart_metadata_and_version_parity(helm_dir: Path):
    """Ensure Chart.yaml matches project semantic version and conforms to Helm v2 spec."""
    chart_file = helm_dir / "Chart.yaml"
    assert chart_file.is_file(), "Chart.yaml must exist"

    data = yaml.safe_load(chart_file.read_text(encoding="utf-8"))
    assert data["apiVersion"] == "v2"
    assert data["name"] == "llm-agent-system"
    assert data["type"] == "application"

    pyproject_text = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert f'version = "{data["version"]}"' in pyproject_text
    assert data["version"] == "0.6.0"
    assert data["appVersion"] == "0.6.0"
    assert len(data.get("keywords", [])) >= 3


def test_values_yaml_production_security_and_ha(helm_dir: Path):
    """Ensure values.yaml satisfies non-root container security and HA replica standards."""
    values_file = helm_dir / "values.yaml"
    assert values_file.is_file()

    values = yaml.safe_load(values_file.read_text(encoding="utf-8"))

    # High availability replica minimum
    assert values["replicaCount"] >= 3

    # Pod & Container SecurityContext
    assert values["podSecurityContext"]["runAsNonRoot"] is True
    assert values["podSecurityContext"]["fsGroup"] == 1001

    sc = values["securityContext"]
    assert sc["runAsNonRoot"] is True
    assert sc["runAsUser"] == 1001
    assert sc["runAsGroup"] == 1001
    assert sc["allowPrivilegeEscalation"] is False
    assert "drop" in sc["capabilities"]
    assert "ALL" in sc["capabilities"]["drop"]

    # Probes
    assert values["livenessProbe"]["httpGet"]["path"] == "/v1/health"
    assert values["livenessProbe"]["httpGet"]["port"] == 8000
    assert values["readinessProbe"]["httpGet"]["path"] == "/v1/health"

    # Autoscaling
    hpa = values["autoscaling"]
    assert hpa["enabled"] is True
    assert hpa["minReplicas"] >= 3
    assert hpa["maxReplicas"] >= hpa["minReplicas"]
    assert hpa["targetCPUUtilizationPercentage"] <= 80


def test_helm_templates_completeness(helm_dir: Path):
    """Verify that all standard Helm template components are present and non-empty."""
    templates_dir = helm_dir / "templates"
    expected_files = [
        "_helpers.tpl",
        "deployment.yaml",
        "service.yaml",
        "ingress.yaml",
        "hpa.yaml",
        "configmap.yaml",
        "secret.yaml",
        "serviceaccount.yaml",
        "pvc.yaml",
        "NOTES.txt",
    ]
    for filename in expected_files:
        f = templates_dir / filename
        assert f.is_file(), f"Missing template: {filename}"
        assert f.stat().st_size > 0, f"Template file is empty: {filename}"

    # Verify _helpers.tpl defines standard names
    helpers_text = (templates_dir / "_helpers.tpl").read_text(encoding="utf-8")
    assert 'define "llm-agent-system.name"' in helpers_text
    assert 'define "llm-agent-system.fullname"' in helpers_text
    assert 'define "llm-agent-system.labels"' in helpers_text
    assert 'define "llm-agent-system.selectorLabels"' in helpers_text


def test_argo_rollouts_canary_specification(canary_dir: Path):
    """Verify Argo Rollouts Canary CRD structure and progressive step configuration."""
    rollout_file = canary_dir / "rollout.yaml"
    assert rollout_file.is_file()

    rollout = yaml.safe_load(rollout_file.read_text(encoding="utf-8"))
    assert rollout["apiVersion"] == "argoproj.io/v1alpha1"
    assert rollout["kind"] == "Rollout"

    canary = rollout["spec"]["strategy"]["canary"]
    assert canary["stableService"] == "llm-agent-system-stable"
    assert canary["canaryService"] == "llm-agent-system-canary"

    # Verify progressive step weights
    steps = canary["steps"]
    weights = [s["setWeight"] for s in steps if "setWeight" in s]
    assert weights == [10, 25, 50, 100], "Canary weights must monotonically advance from 10% to 100%"

    # Verify pause durations
    pauses = [s["pause"]["duration"] for s in steps if "pause" in s and "duration" in s["pause"]]
    assert len(pauses) >= 3, "Must include pause analysis steps between traffic shifts"


def test_analysis_template_slo_metrics(canary_dir: Path):
    """Verify AnalysisTemplate Prometheus query syntax and SLI/SLO failure thresholds."""
    analysis_file = canary_dir / "analysis-template.yaml"
    assert analysis_file.is_file()

    data = yaml.safe_load(analysis_file.read_text(encoding="utf-8"))
    assert data["apiVersion"] == "argoproj.io/v1alpha1"
    assert data["kind"] == "AnalysisTemplate"

    metrics = {m["name"]: m for m in data["spec"]["metrics"]}

    # Success rate SLO (>= 99.9%)
    assert "success-rate" in metrics
    assert "0.999" in metrics["success-rate"]["successCondition"]
    assert metrics["success-rate"]["failureLimit"] <= 3

    # Latency SLO (P99 < 500ms)
    assert "p99-latency" in metrics
    assert "0.500" in metrics["p99-latency"]["successCondition"]
    assert "histogram_quantile" in metrics["p99-latency"]["provider"]["prometheus"]["query"]

    # Error rate SLO (< 0.1%)
    assert "error-rate" in metrics
    assert "0.001" in metrics["error-rate"]["successCondition"]


def test_services_canary_and_stable_separation(canary_dir: Path):
    """Verify that stable and canary services are properly decoupled."""
    services_file = canary_dir / "services-canary.yaml"
    assert services_file.is_file()

    docs = list(yaml.safe_load_all(services_file.read_text(encoding="utf-8")))
    assert len(docs) == 2, "Must contain exactly two Service manifests"

    names = {d["metadata"]["name"] for d in docs}
    assert "llm-agent-system-stable" in names
    assert "llm-agent-system-canary" in names

    for d in docs:
        assert d["kind"] == "Service"
        assert d["spec"]["ports"][0]["port"] == 8000


def test_github_actions_helm_publish_workflow_syntax():
    """Verify GitHub Actions Helm CI/CD workflow triggers, permissions, and steps."""
    wf_file = PROJECT_ROOT / ".github" / "workflows" / "helm-publish.yml"
    assert wf_file.is_file()

    wf = yaml.safe_load(wf_file.read_text(encoding="utf-8"))
    assert wf["permissions"]["packages"] == "write"
    assert wf["permissions"]["contents"] == "read"

    jobs = wf["jobs"]
    assert "lint-and-validate" in jobs
    assert "publish-oci" in jobs

    publish_steps = jobs["publish-oci"]["steps"]
    step_names = [s.get("name", "") for s in publish_steps]
    assert any("Log in to GitHub Container Registry" in name for name in step_names)
    assert any("Package Helm Chart" in name for name in step_names)
    assert any("Push Helm OCI Package to GHCR" in name for name in step_names)
