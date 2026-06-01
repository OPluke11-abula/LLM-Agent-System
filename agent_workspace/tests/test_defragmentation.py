import os
import sys
import json
import tempfile
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

# Add project root to sys.path
workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, workspace_dir)

from core.memory import ContextDefragmenter
from api import app, get_engine


@pytest.fixture
def mock_handoff_env():
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create standard PAP folders
        agent_dir = temp_path / ".agent"
        handoff_dir = agent_dir / "memory" / "handoff"
        handoff_dir.mkdir(parents=True, exist_ok=True)
        
        # Create first handoff file (older)
        handoff_1 = {
            "protocol": "PAP-Handoff",
            "handoff_id": "handoff-1",
            "created_at": "2026-06-01T08:00:00Z",
            "checksum": "abc123sha",
            "memory_snapshot": {
                "working_memory": {
                    "conversations": [
                        {"user": "Hello agent", "assistant": "Hi user", "timestamp": "2026-06-01T07:55:00Z"},
                        {"user": "Implement Phase A", "assistant": "Sure, let's do Phase A", "timestamp": "2026-06-01T07:56:00Z"}
                    ]
                }
            },
            "task_state": {
                "agent_tasks_content": "- [ ] Implement Phase A\n- [ ] Write tests\n"
            }
        }
        (handoff_dir / "handoff-1.json").write_text(json.dumps(handoff_1), encoding="utf-8")
        
        # Create second handoff file (newer, with duplicate conversation and reconciled tasks)
        handoff_2 = {
            "protocol": "PAP-Handoff",
            "handoff_id": "handoff-2",
            "created_at": "2026-06-01T09:00:00Z",
            "checksum": "def456sha",
            "memory_snapshot": {
                "working_memory": {
                    "conversations": [
                        # Duplicate conversation
                        {"user": "Implement Phase A", "assistant": "Sure, let's do Phase A", "timestamp": "2026-06-01T07:56:00Z"},
                        # New conversation
                        {"user": "Run the tests", "assistant": "Running now", "timestamp": "2026-06-01T08:30:00Z"}
                    ]
                }
            },
            "task_state": {
                "agent_tasks_content": "- [x] Implement Phase A\n- [ ] Write tests\n- [ ] Stage changes\n"
            }
        }
        (handoff_dir / "handoff-2.json").write_text(json.dumps(handoff_2), encoding="utf-8")
        
        # Set workspace and project parent mock paths for the test
        # ContextDefragmenter expects project_root to be Path(workspace_path).parent
        # So we can pass str(temp_path / "agent_workspace") as the workspace_path.
        workspace_path = temp_path / "agent_workspace"
        workspace_path.mkdir(parents=True, exist_ok=True)
        
        yield str(workspace_path)


def test_context_defragmenter_core_logic(mock_handoff_env):
    defragmenter = ContextDefragmenter(mock_handoff_env)
    session_id = "test-session"
    
    result = defragmenter.defragment(session_id)
    assert result["status"] == "success"
    assert result["session_id"] == session_id
    
    # Fragmentation rate checks:
    # Total convers: 2 (handoff 1) + 2 (handoff 2) = 4
    # Total tasks: 2 (handoff 1) + 3 (handoff 2) = 5
    # Total items = 9
    # Unique convers: 3
    # Unique tasks: 3 ("Implement Phase A", "Write tests", "Stage changes")
    # Unique items = 6
    # Fragmentation rate = 1 - 6/9 = 0.33
    assert result["fragmentation_rate"] == pytest.approx(0.33, abs=0.01)
    
    # Reconciliation efficiency check
    # Conflicts resolved = 3
    # Reconciliation efficiency = 1 - (3 * 0.02 / 9) = 1 - 0.0067 = 0.99
    assert result["reconciliation_efficiency"] == pytest.approx(0.99, abs=0.01)
    
    # Verify Knowledge Graph structure
    kg = result["knowledge_graph"]
    assert "nodes" in kg
    assert "edges" in kg
    
    # Verify tasks map reconciliation: completed [x] wins
    task_nodes = [node for node in kg["nodes"] if node["type"] == "task"]
    assert len(task_nodes) == 3
    
    for tn in task_nodes:
        if tn["properties"]["label"] == "Implement Phase A":
            assert tn["properties"]["status"] == "completed"
        elif tn["properties"]["label"] == "Write tests":
            assert tn["properties"]["status"] == "pending"
            
    # Verify file persistence
    project_root = Path(mock_handoff_env).parent
    graph_file = project_root / ".agent" / "memory" / "defragmented_graph.json"
    assert graph_file.is_file()
    
    saved_kg = json.loads(graph_file.read_text(encoding="utf-8"))
    assert len(saved_kg["nodes"]) == len(kg["nodes"])


def test_api_defragment_endpoints(mock_handoff_env):
    # Setup FastAPI api workspace path
    import api
    api.workspace = mock_handoff_env
    
    client = TestClient(app)
    session_id = "api-test-session"
    
    # Trigger defragmentation sweep
    resp = client.post(f"/v1/sessions/{session_id}/defragment")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["session_id"] == session_id
    assert "fragmentation_rate" in data
    assert "reconciliation_efficiency" in data
    
    # Fetch metrics
    resp_metrics = client.get(f"/v1/sessions/{session_id}/defragment/metrics")
    assert resp_metrics.status_code == 200
    metrics_data = resp_metrics.json()
    assert metrics_data["session_id"] == session_id
    assert metrics_data["fragmentation_rate"] == data["fragmentation_rate"]
    assert metrics_data["reconciliation_efficiency"] == data["reconciliation_efficiency"]
