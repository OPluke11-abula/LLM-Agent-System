"""Automated integration tests for Forensic Correlator REST API and CLI surface (Phase 94 / GAP-07)."""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Ensure workspace and repository root are on path
workspace_dir = Path(__file__).resolve().parent.parent
repo_root = workspace_dir.parent
if str(workspace_dir) not in sys.path:
    sys.path.insert(0, str(workspace_dir))
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from agent_workspace.api import app
from agent_workspace.cli import handle_forensics, main as cli_main
from agent_workspace.core.audit_ledger import AuditLedger
from agent_workspace.core.runtime_events import RuntimeEventsLedger, RuntimeEventType
from agent_workspace.routes.dependencies import get_tenant_context
from agent_workspace.routes.pipeline import TaskRecord, _task_registry, _registry_lock


@pytest.fixture
def forensic_env():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        session_id = "SESSION-FORENSIC-P94"

        # 1. Populate AuditLedger
        audit_ledger = AuditLedger(workspace_path=str(tmp_path))
        audit_ledger.record_event(
            event_type="TASK_INTAKE",
            payload={"session_id": session_id, "intent": "Compliance verified intake"},
            tenant_id=session_id,
        )
        audit_ledger.record_event(
            event_type="ARCHITECTURE_GATE_APPROVED",
            payload={"session_id": session_id, "approver": "PO Luke"},
            tenant_id=session_id,
        )

        # 2. Populate RuntimeEventsLedger
        runtime_ledger = RuntimeEventsLedger(workspace_path=str(tmp_path))
        runtime_ledger.record_event(
            task_id=session_id,
            event_type=RuntimeEventType.STAGE_TRANSITION,
            payload={"stage": "ISOLATED_MUTATION"},
        )
        runtime_ledger.record_event(
            task_id=session_id,
            event_type=RuntimeEventType.REVIEW_VERIFIED,
            payload={"status": "PASS", "ladder_score": 1.0},
        )

        yield tmp_path, session_id


def test_audit_forensics_rest_endpoint(forensic_env):
    tmp_path, session_id = forensic_env
    app.dependency_overrides[get_tenant_context] = lambda: session_id

    try:
        with patch("agent_workspace.routes.audit.get_workspace", return_value=str(tmp_path)):
            client = TestClient(app)
            res = client.get(f"/v1/audit/forensics/{session_id}")
            assert res.status_code == 200
            data = res.json()
            assert data["status"] == "success"
            forensics = data["forensics"]
            assert forensics["session_id"] == session_id
            assert forensics["total_events"] == 4
            assert forensics["audit_event_count"] == 2
            assert forensics["runtime_event_count"] == 2
            assert forensics["is_tamper_free"] is True
            assert forensics["audit_chain_valid"] is True
            assert forensics["runtime_chain_valid"] is True
            assert len(forensics["timeline"]) == 4
    finally:
        app.dependency_overrides.pop(get_tenant_context, None)


def test_audit_forensics_export_rest_endpoint(forensic_env):
    tmp_path, session_id = forensic_env
    app.dependency_overrides[get_tenant_context] = lambda: session_id

    try:
        with patch("agent_workspace.routes.audit.get_workspace", return_value=str(tmp_path)):
            client = TestClient(app)
            res = client.post(f"/v1/audit/forensics/{session_id}/export")
            assert res.status_code == 200
            data = res.json()
            assert data["status"] == "success"
            assert data["session_id"] == session_id
            assert data["is_tamper_free"] is True
            assert data["total_events"] == 4

            receipt_file = Path(data["receipt_path"])
            assert receipt_file.exists()
            receipt_content = json.loads(receipt_file.read_text(encoding="utf-8"))
            assert receipt_content["session_id"] == session_id
            assert receipt_content["total_events"] == 4
    finally:
        app.dependency_overrides.pop(get_tenant_context, None)


def test_pipeline_task_forensics_endpoint(forensic_env):
    tmp_path, session_id = forensic_env

    # Register task record in pipeline registry
    mock_request = MagicMock()
    mock_request.task_id = session_id
    mock_result = MagicMock()
    mock_preservation = MagicMock()
    mock_ledger = MagicMock()

    record = TaskRecord(
        request=mock_request,
        result=mock_result,
        preservation_receipt=mock_preservation,
        ledger=mock_ledger,
    )
    with _registry_lock:
        _task_registry[session_id] = record

    try:
        with patch("agent_workspace.routes.pipeline.get_workspace", return_value=str(tmp_path)):
            client = TestClient(app)
            res = client.get(f"/v1/pipeline/tasks/{session_id}/forensics")
            assert res.status_code == 200
            data = res.json()
            assert data["status"] == "success"
            assert data["task_id"] == session_id
            assert data["forensics"]["total_events"] == 4
            assert data["forensics"]["is_tamper_free"] is True
    finally:
        with _registry_lock:
            _task_registry.pop(session_id, None)


def test_pipeline_task_forensics_not_found():
    client = TestClient(app)
    res = client.get("/v1/pipeline/tasks/NON_EXISTENT_SESSION_9999/forensics")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_cli_forensics_text_output(forensic_env, capsys, monkeypatch):
    tmp_path, session_id = forensic_env
    monkeypatch.setattr("agent_workspace.cli.workspace", str(tmp_path))

    args = MagicMock()
    args.session_id = session_id
    args.export = False
    args.output = None
    args.json = False

    handle_forensics(args)
    captured = capsys.readouterr()

    assert "LAS Dual-Stream Forensic Timeline & Integrity Audit" in captured.out
    assert session_id in captured.out
    assert "Tamper-Free Status : ✅ VERIFIED" in captured.out
    assert "Total Events       : 4" in captured.out
    assert "[Compliance]" in captured.out
    assert "[Runtime]" in captured.out


def test_cli_forensics_json_output(forensic_env, capsys, monkeypatch):
    tmp_path, session_id = forensic_env
    monkeypatch.setattr("agent_workspace.cli.workspace", str(tmp_path))

    args = MagicMock()
    args.session_id = session_id
    args.export = False
    args.output = None
    args.json = True

    handle_forensics(args)
    captured = capsys.readouterr()

    data = json.loads(captured.out)
    assert data["session_id"] == session_id
    assert data["total_events"] == 4
    assert data["is_tamper_free"] is True
    assert len(data["timeline"]) == 4


def test_cli_forensics_export(forensic_env, capsys, monkeypatch):
    tmp_path, session_id = forensic_env
    monkeypatch.setattr("agent_workspace.cli.workspace", str(tmp_path))

    export_path = tmp_path / "custom_forensic_receipt.json"

    args = MagicMock()
    args.session_id = session_id
    args.export = True
    args.output = str(export_path)
    args.json = False

    handle_forensics(args)
    captured = capsys.readouterr()

    assert f"Exported Receipt   : {export_path}" in captured.out
    assert export_path.exists()
    data = json.loads(export_path.read_text(encoding="utf-8"))
    assert data["session_id"] == session_id
    assert data["is_tamper_free"] is True


def test_cli_main_subcommand_dispatch(forensic_env, capsys, monkeypatch):
    tmp_path, session_id = forensic_env
    monkeypatch.setattr("agent_workspace.cli.workspace", str(tmp_path))

    monkeypatch.setattr(
        sys, "argv", ["las", "forensics", session_id, "--json"]
    )

    cli_main()
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["session_id"] == session_id
    assert data["total_events"] == 4
