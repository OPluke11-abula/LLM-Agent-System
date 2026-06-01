import os
import sys
import tempfile
import pytest
import json
import time
import threading
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

# Add project root to sys.path
workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)

from long_term_memory import LongTermMemoryStore, FTS5SemanticQueryEngine, FTS5QueryCache
from memory_backends import SQLiteBackend


def test_fts5_semantic_query_syntax_parsing():
    """Verify natural language queries are parsed into proper FTS5-optimized syntax."""
    # 1. Stop words filtering
    q1 = "the database connection error"
    parsed1 = FTS5SemanticQueryEngine.parse_query(q1)
    assert parsed1 == '"database" OR "connection" OR "error"'

    # 2. Prefix/wildcard search
    q2 = "exception* retry"
    parsed2 = FTS5SemanticQueryEngine.parse_query(q2)
    assert parsed2 == '"exception"* OR "retry"'

    # 3. Column-scoped syntax
    q3 = "summary:failure core"
    parsed3 = FTS5SemanticQueryEngine.parse_query(q3)
    assert parsed3 == 'summary:"failure" OR "core"'

    # 4. Safe punctuation normalization
    q4 = "sqlite! operational-error: locked;"
    parsed4 = FTS5SemanticQueryEngine.parse_query(q4)
    # Punctuations are cleared/spaced. operational-error: locked -> core tokenized search.
    assert '"sqlite"' in parsed4
    assert '"locked"' in parsed4

    # 5. Empty or completely stop-words fallback
    q5 = "the in to"
    parsed5 = FTS5SemanticQueryEngine.parse_query(q5)
    # Should fallback to basic terms without raising errors
    assert parsed5 == '"the" OR "in" OR "to"'


def test_fts5_table_indexing_and_query_cache(tmp_path):
    """Verify that records are indexed correctly in FTS5 table and cache handles hits/misses."""
    # 1. Initialize LongTermMemoryStore with SQLiteBackend
    db_dir = tmp_path / "memory"
    store = LongTermMemoryStore(db_dir, backend_name="sqlite")
    
    session_id = "session-fts5"
    
    # 2. Add some test records
    record1 = store.add_preference(
        session_id=session_id,
        preference_text="User prefers using a dark theme with blue highlight styles."
    )
    record2 = store.add_semantic_knowledge(
        session_id=session_id,
        knowledge_text="AST-audited dynamic code generation gateway prevents remote execution exploits."
    )
    
    assert record1 is not None
    assert record2 is not None
    
    # 3. Clear cache before query to verify indexing search works on database
    store._query_cache.clear()
    
    # 4. Search via the new FTS5 semantic engine
    results1 = store.query("dark theme", session_id=session_id)
    assert len(results1) == 1
    assert results1[0]["id"] == record1.id
    
    # 5. Verify the second search hits the query cache (latency must be near 0ms)
    start = time.perf_counter()
    results2 = store.query("dark theme", session_id=session_id)
    duration_ms = (time.perf_counter() - start) * 1000
    
    assert len(results2) == 1
    assert results2[0]["id"] == record1.id
    assert duration_ms < 2.0  # Cache hits must be extremely fast, well under 2ms
    
    # 6. Query semantic knowledge with column scopes
    results3 = store.query("summary:AST-audited", session_id=session_id)
    assert len(results3) == 1
    assert results3[0]["id"] == record2.id
    
    store.close()


def test_concurrent_multi_agent_long_term_memory_queries(tmp_path):
    """Verify FTS5 semantic query execution under highly concurrent multi-agent access."""
    db_dir = tmp_path / "memory"
    store = LongTermMemoryStore(db_dir, backend_name="sqlite")
    
    session_id = "session-concurrent"
    
    # Add several distinct records
    store.add_semantic_knowledge(session_id, "CTO handles architectural design decomposition.")
    store.add_semantic_knowledge(session_id, "Dev handles highly efficient React components.")
    store.add_semantic_knowledge(session_id, "QA handles strict unit and integration testing.")
    store.add_semantic_knowledge(session_id, "CFO handles token consumption budgets.")
    store.add_preference(session_id, "The user prefers automated pipeline deployment.")
    
    # We will launch multiple threads representing concurrent agents searching memory simultaneously
    errors = []
    latencies = []
    
    threads = []
    queries = [
        "architectural design",
        "React components",
        "integration testing",
        "token consumption",
        "pipeline deployment",
        "architectural React",
        "automated budgets",
        "strict CFO",
        "components QA",
        "user design"
    ]

    # Warm up thread-local connections to avoid counting SQLite file open latency (Task 21-02)
    warmup_threads = []
    for q in queries:
        t = threading.Thread(target=lambda q=q: store.query(q, session_id=session_id))
        warmup_threads.append(t)
        t.start()
    for t in warmup_threads:
        t.join()

    # Clear cache to force database reads across threads for the timed run
    store._query_cache.clear()
    
    def agent_worker(query_term: str):
        try:
            start = time.perf_counter()
            res = store.query(query_term, session_id=session_id)
            latencies.append((time.perf_counter() - start) * 1000)
            # Assert some results are found (or at least no exception is raised)
            assert isinstance(res, list)
        except Exception as e:
            errors.append(e)
            
    for q in queries:
        t = threading.Thread(target=agent_worker, args=(q,))
        threads.append(t)
        t.start()
        
    for t in threads:
        t.join()
        
    # Assert no concurrency errors or lock deadlocks happened
    assert len(errors) == 0, f"Encountered concurrency errors: {errors}"
    
    # Assert retrieval delays are managed and average latency is kept low (well under 25ms cold startup limit)
    avg_latency = sum(latencies) / len(latencies)
    assert avg_latency < 25.0, f"Average query latency too high: {avg_latency:.2f}ms"
    
    store.close()
