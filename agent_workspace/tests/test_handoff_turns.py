import os
import sys
import tempfile
import json
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

# Add project root to sys.path
workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, workspace_dir)

from core.engine import AgentEngine
from core.router import AgentRouter
from api import app, get_engine, generate_jwt


@pytest.fixture
def mock_turns_env():
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create standard PAP folders
        pap_dir = temp_path / ".agent"
        pap_dir.mkdir(parents=True, exist_ok=True)
        (pap_dir / "skills").mkdir(parents=True, exist_ok=True)
        (temp_path / "agent_workspace" / "memory").mkdir(parents=True, exist_ok=True)
        
        # Create dummy agent_tasks.md
        with open(pap_dir / "agent_tasks.md", "w", encoding="utf-8") as f:
            f.write("# Task Queue\n- [ ] Task A\n- [x] Task B\n")
            
        # Create dummy config.yaml with custom turns threshold
        with open(temp_path / "agent_workspace" / "config.yaml", "w", encoding="utf-8") as f:
            f.write("agent:\n  handoff_threshold: 3\nllm:\n  provider: google-genai\n  model: gemini-2.5-flash\n")
            
        yield temp_dir


def test_session_turns_increment_and_auto_handoff(mock_turns_env):
    temp_path = Path(mock_turns_env)
    workspace_path = temp_path / "agent_workspace"
    
    session_id = "turns-session"
    session_memory = {"conversations": []}
    session_file = workspace_path / "memory" / f"{session_id}.json"
    session_file.write_text(json.dumps(session_memory), encoding="utf-8")
    
    engine = AgentEngine(workspace_path=str(workspace_path))
    assert engine.handoff_threshold == 3
    
    # 1. First turn: increment turns
    turns, triggered, handoff_id = engine.increment_turns(session_id, "Context summary 1")
    assert turns == 1
    assert not triggered
    assert handoff_id is None
    
    # 2. Second turn: increment turns
    turns, triggered, handoff_id = engine.increment_turns(session_id, "Context summary 2")
    assert turns == 2
    assert not triggered
    assert handoff_id is None
    
    # 3. Third turn (threshold met!): should trigger handoff automatically
    turns, triggered, handoff_id = engine.increment_turns(session_id, "Context summary 3")
    assert turns == 3
    assert triggered
    assert handoff_id is not None
    assert handoff_id.startswith("handoff-")
    
    # 4. Check that prompt markdown file was created
    handoff_dir = temp_path / ".agent" / "memory" / "handoff"
    prompt_file = handoff_dir / f"{handoff_id}_prompt.md"
    assert prompt_file.is_file()
    
    prompt_content = prompt_file.read_text(encoding="utf-8")
    assert "Warm Thread Handoff Prompt" in prompt_content
    assert handoff_id in prompt_content
    assert "Context summary 3" in prompt_content
    assert "import_handoff" in prompt_content


def test_api_turns_and_handoff_endpoints(mock_turns_env):
    temp_path = Path(mock_turns_env)
    workspace_path = temp_path / "agent_workspace"
    
    session_id = "api-turns-session"
    session_memory = {"conversations": []}
    session_file = workspace_path / "memory" / f"{session_id}.json"
    session_file.write_text(json.dumps(session_memory), encoding="utf-8")
    
    # Force use our temporary engine in the API
    engine = AgentEngine(workspace_path=str(workspace_path))
    import api
    api._engine = engine
    
    client = TestClient(app)
    headers = {"Authorization": f"Bearer {generate_jwt({'tenant_id': 'test_tenant', 'role': 'tenant'})}"}
    
    # Test GET /turns initially
    resp = client.get(f"/v1/sessions/{session_id}/turns", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == session_id
    assert data["turns"] == 0
    assert data["threshold"] == 3
    assert not data["should_glow"]
    
    # Increment turns on backend manually and test endpoint
    engine.increment_turns(session_id, "Test turns")
    resp = client.get(f"/v1/sessions/{session_id}/turns", headers=headers)
    data = resp.json()
    assert data["turns"] == 1
    assert not data["should_glow"]
    
    # Hit threshold
    engine.increment_turns(session_id, "Test turns")
    engine.increment_turns(session_id, "Test turns")
    resp = client.get(f"/v1/sessions/{session_id}/turns", headers=headers)
    data = resp.json()
    assert data["turns"] == 3
    assert data["should_glow"]
    
    # Test POST /handoff manually
    resp = client.post(f"/v1/sessions/{session_id}/handoff", headers=headers)
    assert resp.status_code == 200
    handoff_data = resp.json()
    assert handoff_data["status"] == "success"
    assert handoff_data["handoff_id"].startswith("handoff-")
    assert "Warm Thread Handoff Prompt" in handoff_data["prompt"]
