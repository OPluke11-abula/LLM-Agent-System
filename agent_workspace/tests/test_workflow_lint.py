from pathlib import Path

import pytest
import yaml

from agent_workspace.workflow_lint import WorkflowLintError, lint_workflow


def _write_yaml(path: Path, data: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


def _valid_manifest(root: Path) -> Path:
    (root / "docs" / "workflow").mkdir(parents=True, exist_ok=True)
    (root / "docs" / "workflow" / "SOURCE_OF_TRUTH.md").write_text("# Source", encoding="utf-8")
    return _write_yaml(
        root / ".agent" / "workflows" / "codex-development.yaml",
        {
            "id": "codex-development",
            "version": "0.1.0",
            "description": "Test workflow",
            "stages": [
                {
                    "id": "repo_audit",
                    "requires": [],
                    "produces": "docs/project/REPO_AUDIT.md",
                    "director_doc": "docs/workflow/SOURCE_OF_TRUTH.md",
                    "human_approval_required": True,
                    "allowed_actions": ["read_files", "git_status"],
                    "checkpoint_policy": "guided",
                    "risk_level": "low",
                },
                {
                    "id": "prd",
                    "requires": ["repo_audit"],
                    "produces": "docs/product/PRD.md",
                    "director_doc": "docs/workflow/SOURCE_OF_TRUTH.md",
                    "human_approval_required": True,
                    "allowed_actions": ["read_files"],
                    "checkpoint_policy": "guided",
                    "risk_level": "medium",
                },
            ],
        },
    )


def test_lint_workflow_accepts_valid_manifest_without_executing_stages(tmp_path):
    manifest = _valid_manifest(tmp_path)

    result = lint_workflow(tmp_path, manifest)

    assert result.workflow_id == "codex-development"
    assert result.stage_count == 2
    assert result.checkpoint_count == 0


def test_lint_workflow_rejects_missing_required_stage_field(tmp_path):
    manifest = _valid_manifest(tmp_path)
    data = yaml.safe_load(manifest.read_text(encoding="utf-8"))
    del data["stages"][0]["allowed_actions"]
    _write_yaml(manifest, data)

    with pytest.raises(WorkflowLintError, match="schema validation failed"):
        lint_workflow(tmp_path, manifest)


def test_lint_workflow_rejects_unknown_stage_dependency(tmp_path):
    manifest = _valid_manifest(tmp_path)
    data = yaml.safe_load(manifest.read_text(encoding="utf-8"))
    data["stages"][1]["requires"] = ["missing_stage"]
    _write_yaml(manifest, data)

    with pytest.raises(WorkflowLintError, match="unknown dependency"):
        lint_workflow(tmp_path, manifest)


def test_lint_workflow_rejects_checkpoint_workspace_escape(tmp_path):
    manifest = _valid_manifest(tmp_path)
    checkpoint = _write_yaml(
        tmp_path / ".agent" / "workflows" / "runs" / "bad-checkpoint.yaml",
        {
            "workflow_id": "codex-development",
            "stage_id": "repo_audit",
            "status": "completed",
            "artifact_path": "../outside.md",
            "artifact_hash": "a" * 64,
            "evidence_refs": ["docs/project/REPO_AUDIT.md"],
            "started_at": "2026-06-29T00:00:00Z",
            "completed_at": "2026-06-29T00:00:01Z",
            "verifier": "pytest",
            "unresolved_risks": [],
        },
    )

    with pytest.raises(WorkflowLintError, match="escapes workspace"):
        lint_workflow(tmp_path, manifest, [checkpoint])


def test_lint_workflow_accepts_valid_checkpoint(tmp_path):
    manifest = _valid_manifest(tmp_path)
    checkpoint = _write_yaml(
        tmp_path / ".agent" / "workflows" / "runs" / "repo-audit.yaml",
        {
            "workflow_id": "codex-development",
            "stage_id": "repo_audit",
            "status": "completed",
            "artifact_path": "docs/project/REPO_AUDIT.md",
            "artifact_hash": "b" * 64,
            "evidence_refs": ["docs/project/REPO_AUDIT.md"],
            "started_at": "2026-06-29T00:00:00Z",
            "completed_at": "2026-06-29T00:00:01Z",
            "verifier": "pytest",
            "unresolved_risks": [],
        },
    )

    result = lint_workflow(tmp_path, manifest, [checkpoint])

    assert result.checkpoint_count == 1
