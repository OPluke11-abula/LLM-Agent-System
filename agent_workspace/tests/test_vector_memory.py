import os
import sys
import math
import json
import pytest
from unittest.mock import MagicMock, patch

# Ensure agent_workspace is in sys.path
workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)

from core.embeddings import generate_mock_embedding, EmbeddingGenerator
from memory_backends import SQLiteBackend, ChromaBackend, PgvectorBackend, VectorMemoryStore
from long_term_memory import LongTermMemoryStore
from core.prompt_composer import PromptComposer


@pytest.fixture(autouse=True)
def reset_generator_cache():
    EmbeddingGenerator.reset_cache()
    yield
    EmbeddingGenerator.reset_cache()


def test_generate_mock_embedding():
    """Verify that generate_mock_embedding produces deterministic and L2-normalized float vectors."""
    text1 = "Hello, zero-trust autonomous sandbox!"
    text2 = "Hello, zero-trust autonomous sandbox!"
    text3 = "Different text"

    # Determinism
    emb1 = generate_mock_embedding(text1, dimension=1536)
    emb2 = generate_mock_embedding(text2, dimension=1536)
    emb3 = generate_mock_embedding(text3, dimension=1536)

    assert emb1 == emb2
    assert emb1 != emb3
    assert len(emb1) == 1536

    # L2-normalization check (sum of squares = 1.0)
    sum_sq1 = sum(x * x for x in emb1)
    sum_sq3 = sum(x * x for x in emb3)

    assert pytest.approx(sum_sq1, abs=1e-5) == 1.0
    assert pytest.approx(sum_sq3, abs=1e-5) == 1.0


# ---------------------------------------------------------------------------
# 2. Test Embedding Generator
# ---------------------------------------------------------------------------

def test_embedding_generator_mock_provider():
    """Verify that EmbeddingGenerator uses the mock provider when api keys are missing or provider=mock."""
    gen = EmbeddingGenerator(provider="mock")
    assert gen.provider == "mock"

    emb = gen.get_embedding("hello")
    assert len(emb) == 1536
    assert pytest.approx(sum(x * x for x in emb), abs=1e-5) == 1.0


def test_embedding_generator_defaults_to_mock_without_network_opt_in(monkeypatch):
    monkeypatch.delenv("EMBEDDING_PROVIDER", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    monkeypatch.delenv("EMBEDDING_ALLOW_NETWORK", raising=False)

    generator = EmbeddingGenerator()

    assert generator.provider == "mock"


@patch("httpx.Client")
def test_embedding_generator_openai_provider(mock_client_class):
    """Verify that EmbeddingGenerator makes correct POST requests to OpenAI endpoint."""
    mock_client = MagicMock()
    mock_client_class.return_value.__enter__.return_value = mock_client

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "data": [{"embedding": [0.1] * 1536}]
    }
    mock_client.post.return_value = mock_response

    gen = EmbeddingGenerator(provider="openai", api_key="sk-test-key")
    emb = gen.get_embedding("hello", dimension=1536)

    assert emb == [0.1] * 1536
    mock_client.post.assert_called_once()
    call_args = mock_client.post.call_args
    assert call_args[0][0] == "https://api.openai.com/v1/embeddings"
    assert call_args[1]["headers"]["Authorization"] == "Bearer sk-test-key"
    assert call_args[1]["json"]["dimensions"] == 1536


@patch("httpx.Client")
def test_embedding_generator_google_provider(mock_client_class):
    """Verify that EmbeddingGenerator makes correct POST requests to Google GenAI endpoint."""
    mock_client = MagicMock()
    mock_client_class.return_value.__enter__.return_value = mock_client

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "embedding": {"values": [0.2] * 768}
    }
    mock_client.post.return_value = mock_response

    gen = EmbeddingGenerator(provider="google", api_key="gemini-key")
    emb = gen.get_embedding("hello", dimension=768)

    assert emb == [0.2] * 768
    mock_client.post.assert_called_once()
    call_args = mock_client.post.call_args
    assert "text-embedding-004:embedContent" in call_args[0][0]
    assert "key=gemini-key" in call_args[0][0]
    assert call_args[1]["json"]["outputDimensionality"] == 768


# ---------------------------------------------------------------------------
# 3. Test ChromaBackend (REST HTTP APIs Mocked)
# ---------------------------------------------------------------------------

@patch("httpx.Client")
def test_chroma_backend_crud(mock_client_class, tmp_path):
    """Verify write, read, search, delete, and all_records for ChromaBackend via HTTP mock."""
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_client_class.return_value.__enter__.return_value = mock_client

    # Mock the responses for /collections, /upsert, /get, /query, /delete
    mock_response_init = MagicMock()
    mock_response_init.json.return_value = {"id": "col-uuid-12345"}

    mock_response_write = MagicMock()
    mock_response_write.json.return_value = {}

    mock_response_read = MagicMock()
    mock_record = {
        "id": "ltm-123",
        "session_id": "sess-abc",
        "created_at": "2026-06-03T23:00:00Z",
        "summary": "This is a summary",
        "payload": {"messages": [], "embedding": [0.1] * 1536}
    }
    mock_response_read.json.return_value = {
        "documents": [json.dumps(mock_record)]
    }

    mock_response_query = MagicMock()
    mock_response_query.json.return_value = {
        "documents": [[json.dumps(mock_record)]],
        "metadatas": [[{"session_id": "sess-abc"}]],
        "distances": [[0.05]]
    }

    mock_response_delete = MagicMock()
    mock_response_delete.json.return_value = ["ltm-123"]

    # Map side effects to endpoints
    def post_side_effect(url, **kwargs):
        resp = MagicMock()
        if "/collections" in url and not url.endswith("delete") and not url.endswith("get") and not url.endswith("query") and not url.endswith("upsert"):
            return mock_response_init
        elif url.endswith("/upsert"):
            return mock_response_write
        elif url.endswith("/get"):
            return mock_response_read
        elif url.endswith("/query"):
            return mock_response_query
        elif url.endswith("/delete"):
            return mock_response_delete
        return resp

    mock_client.post.side_effect = post_side_effect

    # Initialize ChromaBackend
    backend = ChromaBackend(tmp_path)
    assert backend.sqlite_fallback is None

    # Write
    backend.write("sess-abc", "ltm-123", mock_record)

    # Read
    res_read = backend.read("sess-abc", "ltm-123")
    assert res_read == mock_record

    # Search
    res_search = backend.search("query-text", session_id="sess-abc", top_k=5)
    assert len(res_search) == 1
    assert res_search[0]["id"] == "ltm-123"

    # Delete
    deleted = backend.delete("sess-abc", "ltm-123")
    assert deleted is True


# ---------------------------------------------------------------------------
# 4. Test PgvectorBackend (psycopg2 Driver Mocked)
# ---------------------------------------------------------------------------

def test_pgvector_backend_crud(tmp_path):
    """Verify PgvectorBackend schemas, connection, inserts, and cosine queries using psycopg2 mock."""
    mock_db = {}

    # Mock psycopg2 connection and cursor
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur

    # Mock cursor.fetchall to return simulated database rows
    def execute_side_effect(query_str, params=None):
        if "SELECT value FROM las_memory" in query_str:
            if "WHERE session_id = %s AND key = %s" in query_str:
                sess_id, key = params
                val = mock_db.get((sess_id, key))
                mock_cur.fetchone.return_value = [val] if val else None
            elif "ORDER BY embedding <=> %s::vector" in query_str:
                mock_cur.fetchall.return_value = [[v] for v in mock_db.values()]
            else:
                mock_cur.fetchall.return_value = [[v] for v in mock_db.values()]
        elif "INSERT INTO las_memory" in query_str:
            sess_id, key, val, _, _ = params
            mock_db[(sess_id, key)] = val
        elif "DELETE FROM las_memory" in query_str:
            sess_id, key = params
            if (sess_id, key) in mock_db:
                del mock_db[(sess_id, key)]
                mock_cur.rowcount = 1
            else:
                mock_cur.rowcount = 0

    mock_cur.execute.side_effect = execute_side_effect

    # Mock psycopg2 module
    mock_psycopg2 = MagicMock()
    mock_psycopg2.connect.return_value = mock_conn
    sys.modules["psycopg2"] = mock_psycopg2

    try:
        backend = PgvectorBackend(tmp_path)
        assert backend.sqlite_fallback is None

        # Write
        record = {"id": "ltm-999", "summary": "Postgres test summary", "payload": {}}
        backend.write("sess-pg", "ltm-999", record)

        # Read
        read_val = backend.read("sess-pg", "ltm-999")
        assert read_val == record

        # Search
        search_res = backend.search("query text", session_id="sess-pg", top_k=2)
        assert len(search_res) == 1
        assert search_res[0]["id"] == "ltm-999"

        # Delete
        assert backend.delete("sess-pg", "ltm-999") is True
        assert backend.delete("sess-pg", "ltm-999") is False

    finally:
        # Clean up mock module
        sys.modules.pop("psycopg2", None)


# ---------------------------------------------------------------------------
# 5. Test SQLite Fallbacks
# ---------------------------------------------------------------------------

def test_chroma_fallback_to_sqlite(tmp_path):
    """Verify ChromaBackend automatically falls back to SQLiteBackend when server fails."""
    # Patch httpx to raise exception during init
    with patch("httpx.Client.post", side_effect=ConnectionError("Chroma down")):
        backend = ChromaBackend(tmp_path)
        assert backend.sqlite_fallback is not None
        assert isinstance(backend.sqlite_fallback, SQLiteBackend)

        # CRUD operations should work via SQLite fallback
        record = {
            "id": "fallback-test",
            "session_id": "sess-fb",
            "created_at": "2026-06-03T23:00:00Z",
            "summary": "Chroma fallback",
            "keywords": [],
            "message_count": 0,
            "payload": {}
        }
        backend.write("sess-fb", "key-fb", record)
        assert backend.read("sess-fb", "key-fb") == record
        assert len(backend.search("fallback", "sess-fb")) == 1
        assert backend.delete("sess-fb", "key-fb") is True


def test_pgvector_fallback_to_sqlite(tmp_path):
    """Verify PgvectorBackend automatically falls back to SQLiteBackend when driver is missing."""
    # Ensure psycopg2 is not in sys.modules to simulate missing package
    sys.modules.pop("psycopg2", None)

    backend = PgvectorBackend(tmp_path)
    assert backend.sqlite_fallback is not None
    assert isinstance(backend.sqlite_fallback, SQLiteBackend)

    record = {
        "id": "fallback-test-pg",
        "session_id": "sess-fb-pg",
        "created_at": "2026-06-03T23:00:00Z",
        "summary": "Pg fallback",
        "keywords": [],
        "message_count": 0,
        "payload": {}
    }
    backend.write("sess-fb-pg", "key-fb-pg", record)
    assert backend.read("sess-fb-pg", "key-fb-pg") == record
    assert len(backend.search("fallback", "sess-fb-pg")) == 1


# ---------------------------------------------------------------------------
# 6. Test PromptComposer & SSTI Delimiters Escaping
# ---------------------------------------------------------------------------

def test_prompt_composer_ssti_and_semantic_injection(tmp_path):
    """Verify that PromptComposer escapes Jinja2 delimiter strings and injects long-term memory."""
    # Create configuration yaml file in project workspace
    config_path = tmp_path / "config.yaml"
    config_path.write_text("memory:\n  backend: sqlite\n  long_term_enabled: true\n", encoding="utf-8")

    # Create prompts folder inside .agent
    prompts_dir = tmp_path / ".agent" / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)

    # Create a dummy prompt with task_description variable
    dummy_prompt = """---
id: test_prompt
version: 1.0.0
variables:
  - task_description
  - unsafe_var
template: "Task: {{ task_description }}\\nUnsafe: {{ unsafe_var }}"
---
"""
    prompt_file = prompts_dir / "test_prompt.md"
    prompt_file.write_text(dummy_prompt, encoding="utf-8")

    # Add a memory record using LongTermMemoryStore
    memory_dir = tmp_path / "memory"
    store = LongTermMemoryStore(memory_dir, backend_name="sqlite")

    # Populate memory
    store.add_semantic_knowledge(
        session_id="sess-pc",
        knowledge_text="This is a historical reference to building safe systems."
    )

    composer = PromptComposer(workspace_path=str(tmp_path))

    # Unsafe Jinja input
    unsafe_input = "{{ 999 * 999 }}"
    task_desc = "building safe systems"

    variables = {
        "task_description": task_desc,
        "unsafe_var": unsafe_input
    }

    rendered = composer.build("test_prompt", variables)

    # 1. SSTI Escaping Assertion
    assert "{% raw %}{{{% endraw %}" in rendered
    assert "{% raw %}}}{% endraw %}" in rendered
    assert "998001" not in rendered  # Jinja template execution blocked!

    # 2. Semantic Context Insertion Assertion
    assert "## 🧠 RELEVANT HISTORICAL CONTEXT (Long-Term Memories):" in rendered
    assert "historical reference to building safe systems" in rendered
