import os
import sys
import json
import time
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure agent_workspace is in sys.path
workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)

from core.replay_logger import ReplayLogger
from api import app

REPLAYS_DIR = Path(workspace_dir) / "memory" / "replays"

@pytest.fixture(autouse=True)
def setup_api_workspace(tmp_path):
    import api
    global workspace_dir, REPLAYS_DIR

    orig = api.workspace
    orig_workspace_dir = workspace_dir
    orig_replays_dir = REPLAYS_DIR

    test_workspace = tmp_path / "workspace"
    test_workspace.mkdir(parents=True, exist_ok=True)
    workspace_dir = str(test_workspace)
    REPLAYS_DIR = Path(workspace_dir) / "memory" / "replays"
    api.workspace = workspace_dir
    yield
    api.workspace = orig
    workspace_dir = orig_workspace_dir
    REPLAYS_DIR = orig_replays_dir


@pytest.fixture(autouse=True)
def cleanup_replays():
    # Setup: clean up existing DBs starting with 'test-'
    if REPLAYS_DIR.exists():
        for f in REPLAYS_DIR.glob("test-*.db"):
            try:
                f.unlink()
            except Exception:
                pass
    yield
    # Teardown: clean up test DBs
    if REPLAYS_DIR.exists():
        for f in REPLAYS_DIR.glob("test-*.db"):
            try:
                f.unlink()
            except Exception:
                pass


def test_replay_logger_event_logging():
    session_id = "test-session-logging"
    payload1 = {"node": "node-1", "state": "active"}
    payload2 = {"node": "node-2", "state": "handoff"}

    # Log events
    ReplayLogger.log_event(workspace_dir, session_id, "node_transition", payload1)
    ReplayLogger.log_event(workspace_dir, session_id, "handoff_event", payload2)

    # Check database file existence
    db_path = REPLAYS_DIR / f"{session_id}.db"
    assert db_path.exists()

    # Query timeline
    timeline = ReplayLogger.get_session_timeline(workspace_dir, session_id)
    assert timeline is not None
    assert len(timeline) == 2

    assert timeline[0]["event_type"] == "node_transition"
    assert timeline[0]["payload"] == payload1
    assert "timestamp" in timeline[0]

    assert timeline[1]["event_type"] == "handoff_event"
    assert timeline[1]["payload"] == payload2
    assert "timestamp" in timeline[1]


def test_replay_logger_nonexistent_session():
    timeline = ReplayLogger.get_session_timeline(workspace_dir, "test-nonexistent")
    assert timeline is None


def test_replay_logger_cleanup():
    # Create mock session databases
    session_old = "test-session-old"
    session_new = "test-session-new"

    ReplayLogger.log_event(workspace_dir, session_old, "ping", {"data": "old"})
    ReplayLogger.log_event(workspace_dir, session_new, "ping", {"data": "new"})

    db_old_path = REPLAYS_DIR / f"{session_old}.db"
    db_new_path = REPLAYS_DIR / f"{session_new}.db"

    assert db_old_path.exists()
    assert db_new_path.exists()

    # Backdate the modification time of db_old to 8 days ago
    eight_days_ago = time.time() - (8 * 24 * 3600)
    os.utime(str(db_old_path), (eight_days_ago, eight_days_ago))

    # Clean up replays older than 7 days
    purged = ReplayLogger.clean_replays(workspace_dir, ttl_days=7)
    assert purged == 1

    assert not db_old_path.exists()
    assert db_new_path.exists()


def test_http_endpoints():
    client = TestClient(app)
    session_id = "test-http-session"

    # Write some events through logger
    payload = {"status": "success", "cost": 0.05}
    ReplayLogger.log_event(workspace_dir, session_id, "cost_telemetry", payload)

    # Test GET endpoint
    response = client.get(f"/v1/swarm/replays/{session_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["session_id"] == session_id
    assert len(data["timeline"]) == 1
    assert data["timeline"][0]["event_type"] == "cost_telemetry"
    assert data["timeline"][0]["payload"] == payload

    # Test GET for non-existent session
    response_404 = client.get("/v1/swarm/replays/test-http-missing")
    assert response_404.status_code == 404
    assert "not found" in response_404.json()["detail"].lower()

    # Test POST clean endpoint
    session_old = "test-http-old"
    ReplayLogger.log_event(workspace_dir, session_old, "ping", {})
    db_old_path = REPLAYS_DIR / f"{session_old}.db"
    assert db_old_path.exists()

    eight_days_ago = time.time() - (8 * 24 * 3600)
    os.utime(str(db_old_path), (eight_days_ago, eight_days_ago))

    clean_response = client.post("/v1/swarm/replays/clean", json={"ttl_days": 7})
    assert clean_response.status_code == 200
    clean_data = clean_response.json()
    assert clean_data["status"] == "success"
    assert clean_data["purged_count"] >= 1
    assert not db_old_path.exists()
