import os
import sys
import tempfile
import json
import pytest
import jsonschema
from pathlib import Path

# Add project root to sys.path
workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, workspace_dir)

from core.engine import AgentEngine


@pytest.fixture
def mock_handoff_env():
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
            
        # Create dummy config.yaml
        with open(temp_path / "agent_workspace" / "config.yaml", "w", encoding="utf-8") as f:
            f.write("llm:\n  provider: google-genai\n  model: gemini-2.5-flash\n")
            
        yield temp_dir


def test_handoff_export_and_import(mock_handoff_env):
    temp_path = Path(mock_handoff_env)
    workspace_path = temp_path / "agent_workspace"
    
    # 1. Create a dummy session working memory file
    session_id = "test-agent-session"
    session_memory = {
        "conversations": [
            {"user": "Hello", "assistant": "Hi there!"}
        ]
    }
    
    session_file = workspace_path / "memory" / f"{session_id}.json"
    session_file.write_text(json.dumps(session_memory, ensure_ascii=False), encoding="utf-8")
    
    # Initialize AgentEngine with our temporary workspace path
    engine = AgentEngine(workspace_path=str(workspace_path))
    
    # 2. Export Handoff
    context_summary = "State after step 1 execution successfully saved."
    handoff_id = engine.export_handoff(session_id=session_id, context_summary=context_summary)
    
    assert handoff_id.startswith("handoff-")
    
    # Check that handoff JSON was created under .agent/memory/handoff/
    handoff_file = temp_path / ".agent" / "memory" / "handoff" / f"{handoff_id}.json"
    assert handoff_file.is_file()
    
    packet = json.loads(handoff_file.read_text(encoding="utf-8"))
    assert packet["protocol"] == "PAP-Handoff"
    assert packet["context_summary"] == context_summary
    assert packet["pending_steps"] == ["Resume LAS session from exported handoff state."]
    assert packet["memory_snapshot"]["session_id"] == session_id
    assert packet["memory_snapshot"]["working_memory"] == session_memory
    assert "checksum" in packet

    schema_path = Path(__file__).resolve().parents[2] / "spec" / "memory.schema.json"
    memory_schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.validate(instance={"handoff": packet}, schema=memory_schema)
    
    # 3. Import and restore (remove session memory first to check restoration)
    session_file.unlink()
    assert not session_file.exists()
    
    imported_packet = engine.import_handoff(handoff_id=handoff_id)
    
    assert imported_packet["handoff_id"] == handoff_id
    assert session_file.is_file()
    
    restored_memory = json.loads(session_file.read_text(encoding="utf-8"))
    assert restored_memory == session_memory


def test_handoff_import_accepts_legacy_packet_without_pending_steps(mock_handoff_env):
    import hashlib

    temp_path = Path(mock_handoff_env)
    workspace_path = temp_path / "agent_workspace"
    handoff_id = "handoff-legacy"
    memory_snapshot = {
        "session_id": "legacy-session",
        "working_memory": {"conversations": [{"user": "Legacy", "assistant": "OK"}]},
    }
    payload = {
        "task_state": {},
        "context_summary": "Legacy handoff packet before pending_steps.",
        "memory_snapshot": memory_snapshot,
    }
    checksum = hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    packet = {
        "protocol": "PAP-Handoff",
        "version": "1.0.0",
        "handoff_id": handoff_id,
        "created_at": "2026-06-29T00:00:00+00:00",
        **payload,
        "checksum": checksum,
    }
    handoff_dir = temp_path / ".agent" / "memory" / "handoff"
    handoff_dir.mkdir(parents=True, exist_ok=True)
    (handoff_dir / f"{handoff_id}.json").write_text(
        json.dumps(packet, ensure_ascii=False),
        encoding="utf-8",
    )

    engine = AgentEngine(workspace_path=str(workspace_path))
    imported_packet = engine.import_handoff(handoff_id=handoff_id)

    restored = workspace_path / "memory" / "legacy-session.json"
    assert imported_packet["handoff_id"] == handoff_id
    assert restored.is_file()
    assert json.loads(restored.read_text(encoding="utf-8")) == memory_snapshot["working_memory"]


def test_handoff_checksum_tamper_detection(mock_handoff_env):
    temp_path = Path(mock_handoff_env)
    workspace_path = temp_path / "agent_workspace"
    
    session_id = "attacker-session"
    session_memory = {"conversations": []}
    
    session_file = workspace_path / "memory" / f"{session_id}.json"
    session_file.write_text(json.dumps(session_memory, ensure_ascii=False), encoding="utf-8")
    
    engine = AgentEngine(workspace_path=str(workspace_path))
    handoff_id = engine.export_handoff(session_id=session_id, context_summary="Clean state")
    
    handoff_file = temp_path / ".agent" / "memory" / "handoff" / f"{handoff_id}.json"
    packet = json.loads(handoff_file.read_text(encoding="utf-8"))
    
    # Tamper with the packet: change summary to try executing dynamic action
    packet["context_summary"] = "Attacker modified state!"
    
    # Write tampered packet back to disk
    handoff_file.write_text(json.dumps(packet, ensure_ascii=False), encoding="utf-8")
    
    # Import should fail with ValueError because checksum mismatches
    with pytest.raises(ValueError) as excinfo:
        engine.import_handoff(handoff_id=handoff_id)
    assert "integrity verification failed" in str(excinfo.value)
