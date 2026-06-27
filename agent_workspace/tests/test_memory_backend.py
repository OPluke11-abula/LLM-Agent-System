import os
import json
import pytest
from pathlib import Path
from agent_workspace.core.conductor import build_default_conductor_plan
from agent_workspace.long_term_memory import LongTermMemoryStore
from agent_workspace.memory_backends import FileBackend
from agent_workspace.routes.schemas import PreferenceRequest

def test_file_backend_crud(tmp_path):
    # Instantiate FileBackend in the temp directory
    backend = FileBackend(tmp_path)

    session_id = "test-session"

    # 1. Verify directories are created
    assert (tmp_path / "episodic").is_dir()
    assert (tmp_path / "semantic").is_dir()
    assert (tmp_path / "handoff").is_dir()

    # 2. Write episodic memory
    episodic_record = {
        "id": "ltm-episodic1",
        "session_id": session_id,
        "created_at": "2026-05-20T12:00:00Z",
        "source": "memory_limit_hook",
        "source_hash": "hash1",
        "summary": "This is an episodic conversation about task manager layout.",
        "keywords": ["layout", "task", "manager"],
        "message_count": 2,
        "payload": {},
        "domain": "episodic",
        "confidence": 1.0,
        "privacy_level": "session"
    }
    backend.write(session_id, "ltm-episodic1", episodic_record)

    # Check that file is created under episodic subfolder
    file_path = tmp_path / "episodic" / "ltm-episodic1.json"
    assert file_path.is_file()

    # Read back and assert equality
    read_data = backend.read(session_id, "ltm-episodic1")
    assert read_data == episodic_record

    # 3. Write semantic memory
    semantic_record = {
        "id": "sem-semantic1",
        "session_id": session_id,
        "created_at": "2026-05-20T12:05:00Z",
        "source": "semantic_extraction",
        "source_hash": "hash2",
        "summary": "Using SQLite with FTS5 gives virtual table capabilities.",
        "keywords": ["sqlite", "fts5", "virtual"],
        "message_count": 0,
        "payload": {},
        "domain": "semantic",
        "confidence": 1.0,
        "privacy_level": "project"
    }
    backend.write(session_id, "sem-semantic1", semantic_record)

    # Check that file is created under semantic subfolder
    assert (tmp_path / "semantic" / "sem-semantic1.json").is_file()

    # 4. Write handoff memory
    handoff_record = {
        "id": "handoff-1",
        "session_id": session_id,
        "created_at": "2026-05-20T12:10:00Z",
        "source": "handoff_export",
        "source_hash": "hash3",
        "summary": "Transferring state to another agent.",
        "keywords": ["handoff", "transfer"],
        "message_count": 0,
        "payload": {},
        "domain": "handoff",
        "confidence": 1.0,
        "privacy_level": "project"
    }
    backend.write(session_id, "handoff-1", handoff_record)

    assert (tmp_path / "handoff" / "handoff-1.json").is_file()

    # 5. Get all records
    all_records = backend.all_records()
    assert len(all_records) == 3
    # Check sorting order: handoff-1 (created 12:10) -> sem-semantic1 (created 12:05) -> ltm-episodic1 (created 12:00)
    assert all_records[0]["id"] == "handoff-1"
    assert all_records[1]["id"] == "sem-semantic1"
    assert all_records[2]["id"] == "ltm-episodic1"

    # 6. Test search matching
    search_results = backend.search("SQLite FTS5")
    assert len(search_results) == 1
    assert search_results[0]["id"] == "sem-semantic1"

    # Test search with session filtering
    search_results_filtered = backend.search("layout", session_id="other-session")
    assert len(search_results_filtered) == 0

    search_results_success = backend.search("layout", session_id=session_id)
    assert len(search_results_success) == 1
    assert search_results_success[0]["id"] == "ltm-episodic1"

    # 7. Delete record
    assert backend.delete(session_id, "sem-semantic1") is True
    assert backend.read(session_id, "sem-semantic1") is None
    assert (tmp_path / "semantic" / "sem-semantic1.json").exists() is False
    assert len(backend.all_records()) == 2


def test_preference_request_preserves_category_for_memory_console(tmp_path):
    request = PreferenceRequest.model_validate({
        "session": "memory-ui-session",
        "preference": "Prefer concise Traditional Chinese replies.",
        "confidence": 0.9,
        "category": "user/preferences/style",
    })

    assert request.category == "user/preferences/style"

    store = LongTermMemoryStore(tmp_path, backend_name="sqlite")
    try:
        record = store.add_preference(
            session_id=request.session,
            preference_text=request.preference,
            confidence=request.confidence,
            expires_at=request.expires_at,
            category=request.category,
        )
        assert record.category == "user/preferences/style"
        assert store.all_records()[0]["category"] == "user/preferences/style"
    finally:
        store.close()


def test_route_outcome_memory_records_adaptive_routing_payload(tmp_path):
    store = LongTermMemoryStore(tmp_path, backend_name="sqlite")
    try:
        plan = build_default_conductor_plan(
            task_id="session-routing:compilation",
            task_summary="Fix router telemetry and run focused tests.",
            session_id="session-routing",
            task_type="compilation",
            intent="TASK",
            resolved_tools=["run_tests"],
            selected_account={
                "id": "primary",
                "provider": "google-genai",
                "model": "gemini-2.5-pro",
            },
            max_iterations=5,
            max_tool_calls=15,
        )

        record = store.add_route_outcome(
            session_id="session-routing",
            conductor_plan=plan.model_dump(mode="json"),
            success=True,
            latency_ms=1234,
            token_count=4096,
            human_intervention_count=1,
        )

        stored = store.all_records()[0]
        assert record.id.startswith("outcome-")
        assert stored["source"] == "routing_outcome"
        assert stored["category"] == "routing/outcome"
        assert stored["payload"]["record_type"] == "routing_outcome"
        assert stored["payload"]["execution_mode"] == "pro"
        assert stored["payload"]["success"] is True
        assert stored["payload"]["token_count"] == 4096
        assert stored["payload"]["latency_ms"] == 1234
        assert stored["payload"]["human_intervention_count"] == 1
        assert "google-genai/gemini-2.5-pro" in stored["summary"]
    finally:
        store.close()
