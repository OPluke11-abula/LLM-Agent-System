import pytest
import os
import json
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from long_term_memory import LongTermMemoryStore, LongTermMemoryRecord
from api import app
from conftest import auth_headers

@pytest.fixture
def temp_memory_store(tmp_path):
    """Create a temporary SQLite memory store."""
    db_dir = tmp_path / "memory"
    store = LongTermMemoryStore(db_dir, backend_name="sqlite")
    yield store
    store.close()


def test_record_backwards_compatibility():
    """Verify that from_dict safely reconstructs records with missing fields (like category) or extra fields."""
    raw_old_record = {
        "id": "sem-12345",
        "session_id": "session-old",
        "created_at": "2026-06-01T00:00:00Z",
        "source": "manual",
        "source_hash": "hash123",
        "summary": "This is old knowledge.",
        "keywords": ["old", "knowledge"],
        "message_count": 0,
        "payload": {},
        "domain": "semantic",
        "confidence": 0.8,
        # 'category' is missing
        "extra_field_from_future": "ignore_me"  # extra field
    }

    record = LongTermMemoryRecord.from_dict(raw_old_record)
    assert record.id == "sem-12345"
    assert record.category == "general"  # defaulted correctly
    assert not hasattr(record, "extra_field_from_future")  # stripped extra fields


def test_re_ranking_and_diversity(temp_memory_store):
    """Verify that retrieve_and_format_context prioritizes domain weights and diversity partitioning."""
    session_id = "test-session-rank"

    # 1. Add older preference memory (highest weight, should be prioritized despite age)
    pref_time = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    pref_record = LongTermMemoryRecord(
        id="pref-user1",
        session_id=session_id,
        created_at=pref_time,
        source="user",
        source_hash="h1",
        summary="User prefers Python over Java.",
        keywords=["python", "java"],
        message_count=0,
        payload={},
        domain="preference",
        confidence=1.0,
        category="user/preferences"
    )
    temp_memory_store._backend.write(session_id, pref_record.id, pref_record.__dict__)

    # 2. Add semantic memory (medium weight)
    sem_record = LongTermMemoryRecord(
        id="sem-proj1",
        session_id=session_id,
        created_at=datetime.now(timezone.utc).isoformat(),
        source="doc",
        source_hash="h2",
        summary="Database is SQLite in WAL mode.",
        keywords=["sqlite", "wal"],
        message_count=0,
        payload={},
        domain="semantic",
        confidence=1.0,
        category="project/database"
    )
    temp_memory_store._backend.write(session_id, sem_record.id, sem_record.__dict__)

    # 3. Add 4 episodic summaries (standard weight)
    for i in range(4):
        epi_time = (datetime.now(timezone.utc) - timedelta(days=i)).isoformat()
        epi_record = LongTermMemoryRecord(
            id=f"ltm-epi{i}",
            session_id=session_id,
            created_at=epi_time,
            source="chat_summary",
            source_hash=f"epi-hash{i}",
            summary=f"Episodic memory details for chat unit {i}.",
            keywords=["chat", f"unit{i}"],
            message_count=2,
            payload={},
            domain="episodic",
            confidence=0.9,
            category="episodic/chats"
        )
        temp_memory_store._backend.write(session_id, epi_record.id, epi_record.__dict__)

    # Let's retrieve context
    # Query matching everything
    context = temp_memory_store.retrieve_and_format_context("Python SQLite chat", session_id=session_id, limit=5)

    assert "User prefers Python over Java." in context
    assert "Database is SQLite in WAL mode." in context

    # Check diversity partitioning: episodic memories should be capped at limit - 2 (5 - 2 = 3)
    # Even though there are 4 episodic records matching the terms, only 3 should be formatted.
    assert "Episodic memory details for chat unit 0." in context
    assert "Episodic memory details for chat unit 1." in context
    assert "Episodic memory details for chat unit 2." in context
    assert "Episodic memory details for chat unit 3." not in context  # capped due to diversity partitioning!


def test_update_and_batch_move_apis():
    """Verify that update and batch-move endpoints function correctly via TestClient."""
    import uuid
    unique_suffix = uuid.uuid4().hex[:8]
    client = TestClient(app)
    headers = auth_headers()

    # 1. Create a preference memory
    create_payload = {
        "session": "test-api-session",
        "preference": f"Pre-existing user coding preference {unique_suffix}.",
        "confidence": 0.9,
        "expires_at": None
    }
    resp = client.post("/v1/memory/preference", json=create_payload, headers=headers)
    assert resp.status_code == 200
    created_data = resp.json()
    record_id = created_data["record"]["id"]

    # Verify it exists
    get_resp = client.get("/v1/memory", headers=headers)
    assert get_resp.status_code == 200
    records = get_resp.json()["records"]
    assert any(r["id"] == record_id and r["category"] == "general" for r in records)

    # 2. Update memory fields (summary, domain, category, confidence)
    update_payload = {
        "session_id": "test-api-session",
        "key": record_id,
        "summary": f"Updated preference summary text {unique_suffix}.",
        "domain": "preference",
        "category": "user/style/coding",
        "confidence": 1.0,
        "expires_at": None,
        "citations": ["doc-style"]
    }
    update_resp = client.post("/v1/memory/update", json=update_payload, headers=headers)
    assert update_resp.status_code == 200

    # Verify updates
    get_resp = client.get("/v1/memory", headers=headers)
    records = get_resp.json()["records"]
    updated_rec = next(r for r in records if r["id"] == record_id)
    assert updated_rec["summary"] == f"Updated preference summary text {unique_suffix}."
    assert updated_rec["category"] == "user/style/coding"
    assert updated_rec["confidence"] == 1.0
    assert updated_rec["citations"] == ["doc-style"]

    # 3. Batch move category
    batch_payload = {
        "items": [
            {"session_id": "test-api-session", "key": record_id}
        ],
        "new_category": "archive/old-preferences"
    }
    batch_resp = client.post("/v1/memory/batch-move", json=batch_payload, headers=headers)
    assert batch_resp.status_code == 200
    assert batch_resp.json()["moved_count"] == 1

    # Verify move
    get_resp = client.get("/v1/memory", headers=headers)
    records = get_resp.json()["records"]
    moved_rec = next(r for r in records if r["id"] == record_id)
    assert moved_rec["category"] == "archive/old-preferences"

    # Cleanup
    del_resp = client.delete(f"/v1/memory/test-api-session/{record_id}", headers=headers)
    assert del_resp.status_code == 200
