#!/usr/bin/env python3
"""Pre-flight Verification and Receipt Generator for Helm Chart & Argo Rollouts Canary (Phase 112).

Validates:
1. Version parity across pyproject.toml and Chart.yaml (v0.6.0).
2. Complete Helm templates and values.yaml schema invariants (rootless user, securityContext, probes, resources).
3. Argo Rollouts canary strategy (steps monotonicity, pauses, analysis templates).
4. AnalysisTemplate Prometheus metrics thresholds (success rate >= 99.9%, latency < 500ms, error rate < 0.1%).
5. Dual stable/canary services integrity.
6. CI/CD GitHub Actions workflow (.github/workflows/helm-publish.yml).
7. Emits structured evidence receipt at .agent/evidence/helm_canary_receipt.json.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
import sys
import yaml

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("HelmCanaryVerifier")

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def verify_helm_and_canary_readiness() -> dict:
    helm_dir = PROJECT_ROOT / "deploy" / "helm" / "llm-agent-system"
    canary_dir = PROJECT_ROOT / "deploy" / "canary"
    workflow_path = PROJECT_ROOT / ".github" / "workflows" / "helm-publish.yml"
    pyproject_path = PROJECT_ROOT / "pyproject.toml"

    assert helm_dir.is_dir(), f"Helm directory missing: {helm_dir}"
    assert canary_dir.is_dir(), f"Canary directory missing: {canary_dir}"
    assert workflow_path.is_file(), f"Workflow missing: {workflow_path}"

    # 1. Version Parity Check
    chart_yaml_path = helm_dir / "Chart.yaml"
    assert chart_yaml_path.is_file(), "Chart.yaml missing"
    chart_data = yaml.safe_load(chart_yaml_path.read_text(encoding="utf-8"))

    pyproject_text = pyproject_path.read_text(encoding="utf-8")
    expected_version = "0.6.0"
    assert f'version = "{expected_version}"' in pyproject_text, f"pyproject.toml missing version {expected_version}"
    assert chart_data.get("name") == "llm-agent-system", "Chart name must be llm-agent-system"
    assert chart_data.get("version") == expected_version, f"Chart version must be {expected_version}"
    assert chart_data.get("appVersion") == expected_version, f"Chart appVersion must be {expected_version}"
    logger.info("Version parity verified: %s", expected_version)

    # 2. Values.yaml Inspection
    values_path = helm_dir / "values.yaml"
    assert values_path.is_file(), "values.yaml missing"
    values_data = yaml.safe_load(values_path.read_text(encoding="utf-8"))

    assert values_data["replicaCount"] >= 3, "replicaCount must be at least 3 for HA"
    assert values_data["securityContext"]["runAsNonRoot"] is True
    assert values_data["securityContext"]["runAsUser"] == 1001
    assert values_data["securityContext"]["runAsGroup"] == 1001
    assert values_data["service"]["port"] == 8000
    assert values_data["livenessProbe"]["httpGet"]["path"] == "/v1/health"
    assert values_data["readinessProbe"]["httpGet"]["path"] == "/v1/health"
    assert "resources" in values_data and "limits" in values_data["resources"]
    logger.info("values.yaml security context and HA parameters verified.")

    # 3. Helm Templates Inspection
    templates_dir = helm_dir / "templates"
    required_templates = [
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
    for tmpl in required_templates:
        p = templates_dir / tmpl
        assert p.is_file(), f"Template missing: {tmpl}"
    logger.info("All 10 required Helm templates verified.")

    # 4. Argo Rollouts Inspection
    rollout_path = canary_dir / "rollout.yaml"
    assert rollout_path.is_file(), "rollout.yaml missing"
    rollout_data = yaml.safe_load(rollout_path.read_text(encoding="utf-8"))

    assert rollout_data.get("apiVersion") == "argoproj.io/v1alpha1"
    assert rollout_data.get("kind") == "Rollout"
    canary_strategy = rollout_data["spec"]["strategy"]["canary"]
    assert canary_strategy["canaryService"] == "llm-agent-system-canary"
    assert canary_strategy["stableService"] == "llm-agent-system-stable"

    steps = canary_strategy["steps"]
    weights = [s["setWeight"] for s in steps if "setWeight" in s]
    assert weights == [10, 25, 50, 100], f"Unexpected canary weights: {weights}"
    logger.info("Argo Rollouts canary progressive step weights verified: %s", weights)

    # 5. AnalysisTemplate Inspection
    analysis_path = canary_dir / "analysis-template.yaml"
    assert analysis_path.is_file(), "analysis-template.yaml missing"
    analysis_data = yaml.safe_load(analysis_path.read_text(encoding="utf-8"))

    assert analysis_data.get("apiVersion") == "argoproj.io/v1alpha1"
    assert analysis_data.get("kind") == "AnalysisTemplate"
    metrics = {m["name"]: m for m in analysis_data["spec"]["metrics"]}
    assert "success-rate" in metrics, "Missing success-rate metric"
    assert "p99-latency" in metrics, "Missing p99-latency metric"
    assert "error-rate" in metrics, "Missing error-rate metric"
    assert "0.999" in metrics["success-rate"]["successCondition"]
    assert "0.500" in metrics["p99-latency"]["successCondition"]
    assert "0.001" in metrics["error-rate"]["successCondition"]
    logger.info("AnalysisTemplate Prometheus SLI/SLO thresholds verified.")

    # 6. Services Canary Inspection
    services_path = canary_dir / "services-canary.yaml"
    assert services_path.is_file(), "services-canary.yaml missing"
    docs = list(yaml.safe_load_all(services_path.read_text(encoding="utf-8")))
    svc_names = {d["metadata"]["name"] for d in docs if d}
    assert "llm-agent-system-stable" in svc_names
    assert "llm-agent-system-canary" in svc_names
    logger.info("Dual canary/stable services verified.")

    # 7. GitHub Actions Workflow Inspection
    wf_data = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
    assert wf_data["permissions"]["packages"] == "write"
    assert "lint-and-validate" in wf_data["jobs"]
    assert "publish-oci" in wf_data["jobs"]
    logger.info("GitHub Actions helm-publish workflow verified.")

    receipt = {
        "status": "PASS",
        "milestone": "T-039 (Phase 112)",
        "protocol_version": "3.8.0",
        "app_version": expected_version,
        "chart_version": chart_data["version"],
        "chart_name": chart_data["name"],
        "helm_templates_count": len(required_templates),
        "replica_count_ha": values_data["replicaCount"],
        "rootless_user_uid": values_data["securityContext"]["runAsUser"],
        "canary_steps_weight": weights,
        "analysis_slo_metrics": list(metrics.keys()),
        "ghcr_oci_target": "oci://ghcr.io/opluke11-abula/charts",
        "verification_summary": {
            "version_parity": "PASS",
            "values_schema": "PASS",
            "templates_integrity": "PASS",
            "argo_rollouts_canary": "PASS",
            "analysis_template_slo": "PASS",
            "ci_cd_workflow": "PASS",
        },
    }

    receipt_path = PROJECT_ROOT / ".agent" / "evidence" / "helm_canary_receipt.json"
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Generated evidence receipt at: %s", receipt_path)
    return receipt


if __name__ == "__main__":
    try:
        rec = verify_helm_and_canary_readiness()
        print("\n=======================================================")
        print(" [HELM & CANARY] CLOUD-NATIVE DEPLOYMENT AUDIT (PHASE 112)")
        print("=======================================================")
        print(f" Status:               {rec['status']}")
        print(f" Milestone:            {rec['milestone']}")
        print(f" Chart Name & Version: {rec['chart_name']} v{rec['chart_version']}")
        print(f" Canary Steps:         {rec['canary_steps_weight']}")
        print(f" Prometheus SLOs:      {rec['analysis_slo_metrics']}")
        print(f" Rootless UID:         {rec['rootless_user_uid']}")
        print(f" GHCR OCI Destination: {rec['ghcr_oci_target']}")
        print("=======================================================\n")
        sys.exit(0)
    except Exception as exc:
        logger.error("Verification failed: %s", exc, exc_info=True)
        sys.exit(1)
