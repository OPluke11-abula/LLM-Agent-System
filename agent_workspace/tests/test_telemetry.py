import os
import sys
import tempfile
import pytest
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add project root to sys.path
workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, workspace_dir)

from core.engine import AgentEngine
from core.workflow_engine import WorkflowEngine
from pydantic import BaseModel

# Mock tools
class MockSlowArgs(BaseModel):
    duration: float

def mock_slow(args: MockSlowArgs):
    return {"status": "slept"}

@pytest.fixture
def mock_workflow_env():
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        pap_dir = temp_path / ".agent"
        workflows_dir = pap_dir / "workflows"
        workflows_dir.mkdir(parents=True, exist_ok=True)
        
        with open(temp_path / "config.yaml", "w", encoding="utf-8") as f:
            f.write("llm:\n  provider: google-genai\n  model: gemini-2.5-flash\n")
            
        yield temp_dir

@pytest.mark.asyncio
async def test_telemetry_latency_and_cost_warnings(mock_workflow_env):
    temp_path = Path(mock_workflow_env)
    
    workflow_md = """---
id: telemetry_workflow
name: Telemetry Workflow
description: Test telemetry alerts
version: 1.0.0
steps:
  - step_id: step_1
    skill_id: mock_slow
    params:
      duration: 0.1
    on_failure: fail
    next_step: null
---
"""
    workflow_file = temp_path / ".agent" / "workflows" / "telemetry_workflow.md"
    workflow_file.write_text(workflow_md, encoding="utf-8")
    
    real_engine = AgentEngine(workspace_path=workspace_dir)
    real_engine.tools_registry["mock_slow"] = {
        "function": mock_slow,
        "args_model": MockSlowArgs,
        "description": "mock slow",
        "schema": MockSlowArgs.model_json_schema(),
        "wants_context": False,
        "is_markdown_skill": False,
    }
    
    workflow_engine = WorkflowEngine(real_engine)
    workflow_engine.workflows_dir = temp_path / ".agent" / "workflows"
    workflow_engine.runs_dir = workflow_engine.workflows_dir / "runs"
    workflow_engine.runs_dir.mkdir(parents=True, exist_ok=True)
    
    # Track received telemetry events
    received_events = []
    def callback(session_id, event):
        received_events.append(event)
        
    workflow_engine.register_callback(callback)
    
    # Mock AccountManager to return an active account approaching budget (900 used out of 1000)
    mock_acc_manager = MagicMock()
    mock_acc_manager.get_active_account.return_value = {
        "id": "mock-acc",
        "provider": "google-genai",
        "model": "gemini-2.5-flash",
        "token_budget": 1000,
        "tokens_used": 900,
        "is_active": True
    }
    
    # Mock time.perf_counter safely without raising StopIteration
    perf_calls = [10.0, 16.0]
    perf_calls_iter = iter(perf_calls)
    original_perf_counter = time.perf_counter
    def mock_perf_counter():
        try:
            return next(perf_calls_iter)
        except StopIteration:
            return original_perf_counter()
    
    with patch("core.workflow_engine.AccountManager", return_value=mock_acc_manager), \
         patch("time.perf_counter", new=mock_perf_counter):
         
        results = await workflow_engine.execute(
            workflow_id="telemetry_workflow",
            session_id="session-telemetry-1",
            payload={}
        )
        
    # Verify events were captured
    assert len(received_events) >= 2
    
    # First event is step_started
    assert received_events[0]["type"] == "step_started"
    
    # Second event is step_completed
    completed_event = received_events[1]
    assert completed_event["type"] == "step_completed"
    assert completed_event["status"] == "success"
    
    # Verify alerts triggered
    assert completed_event["active_latency_alert"] is True
    assert completed_event["cost_alert"] is True
    assert completed_event["duration_ms"] > 5000
