import os
import sys
import tempfile
import pytest
from pathlib import Path
from unittest.mock import MagicMock

# Add project root to sys.path
workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)

from long_term_memory import ConcurrencyAuditor
from core.discussion_room import DiscussionRoom


@pytest.fixture
def temp_workspace():
    """Scaffolds a mock temp workspace with agent_workspace subdirectory and python files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Scaffold agent_workspace dir
        agent_workspace = temp_path / "agent_workspace"
        agent_workspace.mkdir(parents=True, exist_ok=True)
        
        # 1. Write a secure python file
        secure_code = """
import sqlite3
import asyncio

class SecureStore:
    def __init__(self):
        self._lock = asyncio.Lock()
        
    async def write(self):
        async with self._lock:
            conn = sqlite3.connect("db.sqlite")
            # do work
        """
        (agent_workspace / "secure_db.py").write_text(secure_code, encoding="utf-8")
        
        # 2. Write an insecure python file
        insecure_code = """
import sqlite3

class InsecureStore:
    def write(self):
        conn = sqlite3.connect("db.sqlite")
        # raw write, no lock!
        """
        (agent_workspace / "insecure_db.py").write_text(insecure_code, encoding="utf-8")
        
        # 3. Write a file without sqlite3
        normal_code = """
print("hello world")
        """
        (agent_workspace / "normal.py").write_text(normal_code, encoding="utf-8")
        
        # 4. Write an insecure python file inside tests directory (should be skipped)
        tests_dir = agent_workspace / "tests"
        tests_dir.mkdir(parents=True, exist_ok=True)
        (tests_dir / "test_insecure_db.py").write_text(insecure_code, encoding="utf-8")
        
        # 5. Write an insecure python file inside .agent directory (should be skipped)
        agent_dir = temp_path / ".agent"
        agent_dir.mkdir(parents=True, exist_ok=True)
        (agent_dir / "some_agent_tool.py").write_text(insecure_code, encoding="utf-8")
        
        yield temp_dir


def test_static_concurrency_audit(temp_workspace):
    """Verify that ConcurrencyAuditor correctly identifies sqlite connection violations while skipping excluded dirs."""
    res = ConcurrencyAuditor.perform_static_audit(temp_workspace)
    assert res["status"] == "warning"
    assert res["risk_score"] > 0.0
    assert res["violations_found"] == 1
    
    violation = res["details"][0]
    assert violation["file"] == "insecure_db.py"
    assert "InsecureStore" in Path(violation["path"]).read_text(encoding="utf-8")
    
    # Excluded directories must be skipped
    violated_files = [v["file"] for v in res["details"]]
    assert "test_insecure_db.py" not in violated_files
    assert "some_agent_tool.py" not in violated_files


def test_concurrency_audit_and_broadcast(temp_workspace):
    """Verify that audit_and_broadcast runs static audit and broadcasts telemetry warnings in real-time."""
    # Register mock callback
    callback_called = []
    def mock_callback(session_id, warning_event):
        callback_called.append((session_id, warning_event))
        
    DiscussionRoom.register_callback(mock_callback)
    
    try:
        session_id = "test-audit-session-123"
        event = ConcurrencyAuditor.audit_and_broadcast(temp_workspace, session_id=session_id)
        
        # Assert returned event metadata
        assert event["session"] == session_id
        assert event["type"] == "concurrency_audit"
        assert event["concurrency_warning"] is True
        assert event["risk_score"] > 0.0
        assert "timestamp" in event
        
        # Assert callback was invoked
        assert len(callback_called) == 1
        cb_session_id, cb_event = callback_called[0]
        assert cb_session_id == session_id
        assert cb_event == event
    finally:
        # Cleanup callback
        if mock_callback in DiscussionRoom.telemetry_callbacks:
            DiscussionRoom.telemetry_callbacks.remove(mock_callback)
