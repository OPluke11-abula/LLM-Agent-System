import os
import sys
import tempfile
import pytest
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

# Add project root to sys.path
workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)

from api import app
from observability import get_telemetry_router, TelemetryRouter
from core.ledger import FinancialLedger
from core.sandbox import SandboxGuard

@pytest.fixture
def temp_workspace():
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create standard .agent folders
        agent_dir = Path(temp_dir) / ".agent"
        agent_dir.mkdir(parents=True, exist_ok=True)
        (agent_dir / "memory").mkdir(parents=True, exist_ok=True)
        yield temp_dir

def test_telemetry_router_buffering(temp_workspace):
    router = TelemetryRouter(temp_workspace)
    session_id = "test-session-telemetry"
    
    # Assert initial empty buffer
    assert len(router.get_metrics(session_id)) == 0
    
    # Record a telemetry metric
    router.record_metric(session_id, latency_ms=15.0, ws_latency_ms=10.0)
    
    metrics = router.get_metrics(session_id)
    assert len(metrics) == 1
    m = metrics[0]
    assert m["session_id"] == session_id
    assert m["latency_ms"] == 15.0
    assert m["ws_latency_ms"] == 10.0
    assert isinstance(m["cpu_percent"], float)
    assert isinstance(m["memory_mb"], float)
    assert isinstance(m["usd_cost"], float)

def test_telemetry_router_thread_safety(temp_workspace):
    router = TelemetryRouter(temp_workspace)
    session_id = "concurrent-session"
    
    threads = []
    def worker():
        for _ in range(10):
            router.record_metric(session_id, latency_ms=5.0, ws_latency_ms=2.0)
            
    for _ in range(5):
        t = threading.Thread(target=worker)
        threads.append(t)
        t.start()
        
    for t in threads:
        t.join()
        
    metrics = router.get_metrics(session_id)
    assert len(metrics) == 50

def test_api_endpoints_for_sandbox_and_telemetry():
    client = TestClient(app)
    session_id = "api-test-session"
    
    # Initialize sandbox stats
    SandboxGuard.total_executions = 10
    SandboxGuard.blocked_executions = 2
    SandboxGuard.allowed_executions = 8
    SandboxGuard.last_execution_status = "allowed"
    
    # Test Sandbox status endpoint
    response = client.get(f"/v1/sessions/{session_id}/sandbox/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["total_executions"] == 10
    assert data["blocked_executions"] == 2
    assert data["allowed_executions"] == 8
    assert data["last_execution_status"] == "allowed"

    # Test Telemetry endpoint
    response_telemetry = client.get(f"/v1/sessions/{session_id}/telemetry")
    assert response_telemetry.status_code == 200
    tel_data = response_telemetry.json()
    assert tel_data["session_id"] == session_id
    assert len(tel_data["metrics"]) >= 1
