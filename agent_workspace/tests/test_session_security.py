import os
from pathlib import Path
import pytest
import subprocess
import sys

from agent_workspace.core.security import safe_workspace_path, validate_session_id
from agent_workspace.core.router import MemoryManager
from agent_workspace.core.replay_logger import ReplayLogger
from agent_workspace.core.account_manager import AccountManager
from agent_workspace.core.memory import ContextDefragmenter
from agent_workspace.core.workflow_engine import WorkflowEngine
from agent_workspace.memory_backends import SQLiteBackend


@pytest.mark.parametrize("session_id", ["session-01", "A_b-9", "x" * 128])
def test_validate_session_id_accepts_contract_values(session_id):
    assert validate_session_id(session_id) == session_id


@pytest.mark.parametrize(
    "session_id",
    [
        "",
        "x" * 129,
        "../escape",
        r"..\escape",
        r"nested/..\escape",
        "%2e%2e",
        "%2f",
        "%5c",
        "/etc/passwd",
        r"C:\Windows\temp",
        r"\\server\share\session",
        "nested/../../escape",
    ],
)
def test_validate_session_id_rejects_path_inputs(session_id):
    with pytest.raises(ValueError):
        validate_session_id(session_id)


def test_safe_workspace_path_resolves_contained_relative_path(tmp_path):
    result = safe_workspace_path(tmp_path, "memory/session-01.json")
    assert result == (tmp_path / "memory" / "session-01.json").resolve()
    assert result.is_relative_to(tmp_path.resolve())


@pytest.mark.parametrize(
    "relative_path",
    [
        "../escape.json",
        r"..\escape.json",
        r"nested/..\..\escape.json",
        "%2e%2e/escape.json",
        "%2fetc/passwd",
        "%5cetc%5cpasswd",
        "/etc/passwd",
        r"C:\Windows\temp\x.json",
        r"\\server\share\x.json",
    ],
)
def test_safe_workspace_path_rejects_workspace_escape_inputs(tmp_path, relative_path):
    with pytest.raises(ValueError):
        safe_workspace_path(tmp_path, relative_path)


def test_memory_manager_uses_contained_session_file(tmp_path):
    manager = MemoryManager(str(tmp_path / "memory"), "session-01")
    manager.save({"ok": True})

    assert manager.memory_path == str((tmp_path / "memory" / "session-01.json").resolve())
    assert manager.load() == {"ok": True}


@pytest.mark.parametrize("session_id", ["../escape", r"..\escape", "%2e%2e"])
def test_memory_manager_rejects_unsafe_session_file_names(tmp_path, session_id):
    with pytest.raises(ValueError):
        MemoryManager(str(tmp_path / "memory"), session_id)


@pytest.mark.parametrize("session_id", ["../escape", r"..\escape", "%2e%2e", r"C:\temp"])
def test_replay_logger_rejects_unsafe_session_file_names(tmp_path, session_id):
    with pytest.raises(ValueError):
        ReplayLogger.log_event(str(tmp_path), session_id, "test", {})

    with pytest.raises(ValueError):
        ReplayLogger.get_session_timeline(str(tmp_path), session_id)


@pytest.mark.parametrize("session_id", ["../escape", r"..\escape", "%2e%2e", r"C:\temp"])
def test_sqlite_backend_rejects_unsafe_session_inputs(tmp_path, session_id):
    backend = SQLiteBackend(tmp_path / "memory.db")
    try:
        with pytest.raises(ValueError):
            backend.write(session_id, "key", {"value": 1})
        with pytest.raises(ValueError):
            backend.read(session_id, "key")
        with pytest.raises(ValueError):
            backend.delete(session_id, "key")
        with pytest.raises(ValueError):
            backend.search("value", session_id=session_id)
    finally:
        backend.close()


def test_session_state_boundaries_reject_unsafe_ids(tmp_path):
    with pytest.raises(ValueError):
        AccountManager.register_session_tenant("../escape", "tenant-a")
    with pytest.raises(ValueError):
        AccountManager.get_session_tenant("../escape")
    with pytest.raises(ValueError):
        ContextDefragmenter(str(tmp_path)).defragment("../escape")


@pytest.mark.parametrize("session_id", ["../escape", "%2e%2e", r"C:\temp", r"\\server\share\session"])
def test_workflow_run_path_rejects_unsafe_session_ids(tmp_path, session_id):
    engine = WorkflowEngine(type("Engine", (), {"workspace_path": str(tmp_path / "agent_workspace")})())
    with pytest.raises(PermissionError):
        engine._get_run_file(session_id)


def test_security_imports_work_without_legacy_core_alias():
    root = Path(__file__).parents[2]
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from agent_workspace.core.account_manager import AccountManager; "
                "from agent_workspace.memory_backends import SQLiteBackend; "
                "from agent_workspace.core.workflow_engine import WorkflowEngine; "
                "from agent_workspace.core.audit_ledger import AuditLedger; "
                "from agent_workspace.core.discussion_room import ProofOfConsensus"
            ),
        ],
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
