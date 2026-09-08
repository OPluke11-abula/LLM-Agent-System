import sys
from pathlib import Path

# Add project root and workspace to sys.path
root_dir = Path(__file__).resolve().parents[2]
workspace_dir = root_dir / "agent_workspace"
for p in (str(root_dir), str(workspace_dir)):
    if p not in sys.path:
        sys.path.insert(0, p)

import pytest
import os
import json
from pathlib import Path
from agent_workspace.topology_bridge import TopologyEvent, TopologyEmitter


def test_topology_event_creation():
    evt = TopologyEvent.create(
        session_id="test-session-123",
        node_type="agent",
        status="running",
        payload={"agent_name": "Developer"}
    )
    assert evt.session_id == "test-session-123"
    assert evt.node_type == "agent"
    assert evt.status == "running"
    assert evt.payload["agent_name"] == "Developer"

    d = evt.to_dict()
    assert d["session_id"] == "test-session-123"
    assert d["node_type"] == "agent"


def test_topology_event_invalid_type():
    with pytest.raises(ValueError, match="Unsupported node_type"):
        TopologyEvent.create(session_id="sess", node_type="invalid_type")


def test_topology_emitter_record_and_persist(tmp_path):
    output_file = tmp_path / "topology_state.json"
    emitter = TopologyEmitter(session_id="session-emitter-1", output_path=output_file)

    evt1 = TopologyEvent.create(
        session_id="session-emitter-1",
        node_id="root-1",
        node_type="session_root",
        status="running"
    )
    emitter.record_event(evt1)

    evt2 = TopologyEvent.create(
        session_id="session-emitter-1",
        node_id="agent-1",
        parent_node_id="root-1",
        node_type="agent",
        edge_type="handoff",
        status="completed"
    )
    emitter.record_event(evt2)

    assert output_file.exists()
    data = json.loads(output_file.read_text(encoding="utf-8"))
    assert data["session_id"] == "session-emitter-1"
    assert len(data["nodes"]) == 2
    assert len(data["edges"]) == 1
