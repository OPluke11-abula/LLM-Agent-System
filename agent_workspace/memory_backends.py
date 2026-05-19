"""Pluggable long-term memory backends for LAS.

This module defines the abstract ``MemoryBackend`` contract and ships a
zero-dependency ``SQLiteBackend`` as the default production adapter.  Future
backends (Qdrant, Chroma, Weaviate) implement the same three-method interface
so the rest of the codebase never needs to change.

Architecture note:
    The backend is a *storage* layer only.  Summarisation, keyword extraction,
    deduplication, and record formatting remain the responsibility of
    ``LongTermMemoryStore`` in ``long_term_memory.py``.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Abstract contract
# ---------------------------------------------------------------------------

class MemoryBackend(ABC):
    """Minimal contract every long-term memory backend must satisfy."""

    @abstractmethod
    def write(self, session_id: str, key: str, value: dict[str, Any]) -> None:
        """Persist *value* under *(session_id, key)*.

        If a record with the same ``(session_id, key)`` already exists the
        backend must silently skip or upsert — never raise on duplicate.
        """

    @abstractmethod
    def read(self, session_id: str, key: str) -> dict[str, Any] | None:
        """Return the value stored at *(session_id, key)*, or ``None``."""

    @abstractmethod
    def search(
        self,
        query: str,
        session_id: str | None = None,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Return up to *top_k* records whose stored value matches *query*.

        When *session_id* is given the search is scoped to that session.
        Ordering is backend-specific (keyword overlap for SQLite, cosine
        similarity for vector stores).
        """

    @abstractmethod
    def all_records(self) -> list[dict[str, Any]]:
        """Return every stored record (used for CLI ``list`` and API ``/v1/memory``)."""

    @abstractmethod
    def delete(self, session_id: str, key: str) -> bool:
        """Delete a record by session_id and key. Returns True if deleted, False if not found."""


# ---------------------------------------------------------------------------
# SQLite implementation — zero extra dependencies
# ---------------------------------------------------------------------------

class SQLiteBackend(MemoryBackend):
    """SQLite-backed long-term memory with FTS5 full-text search.

    Schema
    ------
    ``memory_records`` stores the authoritative JSON blob.
    ``memory_fts`` is a virtual FTS5 table that mirrors ``summary`` and
    ``keywords`` for fast text search.  The two tables are kept in sync by
    triggers so callers only interact with ``memory_records``.
    """

    _DDL = """
    CREATE TABLE IF NOT EXISTS memory_records (
        session_id  TEXT    NOT NULL,
        key         TEXT    NOT NULL,
        value       TEXT    NOT NULL,
        created_at  TEXT    NOT NULL,
        PRIMARY KEY (session_id, key)
    );

    CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
        session_id,
        key,
        summary,
        keywords
    );
    """

    _TRIGGER_INSERT = """
    CREATE TRIGGER IF NOT EXISTS memory_fts_insert AFTER INSERT ON memory_records BEGIN
        INSERT INTO memory_fts(rowid, session_id, key, summary, keywords)
        VALUES (
            new.rowid,
            new.session_id,
            new.key,
            json_extract(new.value, '$.summary'),
            json_extract(new.value, '$.keywords')
        );
    END;
    """

    _TRIGGER_DELETE = """
    CREATE TRIGGER IF NOT EXISTS memory_fts_delete AFTER DELETE ON memory_records BEGIN
        INSERT INTO memory_fts(memory_fts, rowid, session_id, key, summary, keywords)
        VALUES (
            'delete',
            old.rowid,
            old.session_id,
            old.key,
            json_extract(old.value, '$.summary'),
            json_extract(old.value, '$.keywords')
        );
    END;
    """

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        # Initialise schema on the calling thread's connection.
        self._init_schema()

    # -- connection-per-thread ------------------------------------------------

    def _get_conn(self) -> sqlite3.Connection:
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(str(self.db_path))
            conn.execute("PRAGMA journal_mode=WAL")
            conn.row_factory = sqlite3.Row
            self._local.conn = conn
        return conn

    def _init_schema(self) -> None:
        conn = self._get_conn()
        conn.executescript(self._DDL)
        conn.executescript(self._TRIGGER_INSERT)
        conn.executescript(self._TRIGGER_DELETE)
        conn.commit()

    # -- public API -----------------------------------------------------------

    def write(self, session_id: str, key: str, value: dict[str, Any]) -> None:
        conn = self._get_conn()
        now = datetime.now(timezone.utc).isoformat()
        blob = json.dumps(value, ensure_ascii=False)
        conn.execute(
            """
            INSERT INTO memory_records (session_id, key, value, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(session_id, key) DO UPDATE SET value = excluded.value, created_at = excluded.created_at
            """,
            (session_id, key, blob, now),
        )
        conn.commit()

    def read(self, session_id: str, key: str) -> dict[str, Any] | None:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT value FROM memory_records WHERE session_id = ? AND key = ?",
            (session_id, key),
        ).fetchone()
        if row is None:
            return None
        return json.loads(row["value"])

    def search(
        self,
        query: str,
        session_id: str | None = None,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        conn = self._get_conn()

        # Build FTS5 match expression — quote each token to avoid syntax errors
        tokens = query.strip().split()
        if not tokens:
            return self.all_records()[:top_k]

        fts_query = " OR ".join(f'"{t}"' for t in tokens)

        if session_id:
            rows = conn.execute(
                """
                SELECT r.value
                FROM memory_fts f
                JOIN memory_records r ON r.rowid = f.rowid
                WHERE memory_fts MATCH ? AND f.session_id = ?
                ORDER BY rank
                LIMIT ?
                """,
                (fts_query, session_id, top_k),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT r.value
                FROM memory_fts f
                JOIN memory_records r ON r.rowid = f.rowid
                WHERE memory_fts MATCH ?
                ORDER BY rank
                LIMIT ?
                """,
                (fts_query, top_k),
            ).fetchall()

        return [json.loads(row["value"]) for row in rows]

    def all_records(self) -> list[dict[str, Any]]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT value FROM memory_records ORDER BY created_at DESC"
        ).fetchall()
        return [json.loads(row["value"]) for row in rows]

    def delete(self, session_id: str, key: str) -> bool:
        conn = self._get_conn()
        cursor = conn.execute(
            "DELETE FROM memory_records WHERE session_id = ? AND key = ?",
            (session_id, key),
        )
        conn.commit()
        return cursor.rowcount > 0


# ---------------------------------------------------------------------------
# Redis implementation — using RediSearch (Redis Stack)
# ---------------------------------------------------------------------------

class RedisBackend(MemoryBackend):
    """Redis-backed long-term memory with RediSearch for full-text search.

    Requires `redis` Python package and a Redis server running Redis Stack.
    """

    def __init__(self, db_path: str | Path) -> None:
        import redis
        import os
        
        # db_path is mostly ignored for Redis, but we use env var
        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
        self.client = redis.Redis.from_url(redis_url, decode_responses=True)
        self.index_name = "memory_idx"
        self._init_schema()

    def _init_schema(self) -> None:
        from redis.commands.search.field import TextField, TagField
        from redis.commands.search.indexDefinition import IndexDefinition, IndexType
        import redis.exceptions

        try:
            self.client.ft(self.index_name).info()
        except redis.exceptions.ResponseError:
            # Index does not exist, create it
            schema = (
                TagField("session_id"),
                TextField("key"),
                TextField("summary"),
                TextField("keywords"),
                TextField("value")
            )
            definition = IndexDefinition(prefix=["memory:"], index_type=IndexType.HASH)
            try:
                self.client.ft(self.index_name).create_index(schema, definition=definition)
            except redis.exceptions.ResponseError as e:
                import logging
                logging.getLogger(__name__).warning("Could not create Redis search index: %s", e)

    def write(self, session_id: str, key: str, value: dict[str, Any]) -> None:
        import json
        from datetime import datetime, timezone
        
        now = datetime.now(timezone.utc).isoformat()
        blob = json.dumps(value, ensure_ascii=False)
        redis_key = f"memory:{session_id}:{key}"
        
        self.client.hset(redis_key, mapping={
            "session_id": session_id,
            "key": key,
            "summary": value.get("summary", "") or "",
            "keywords": value.get("keywords", "") or "",
            "value": blob,
            "created_at": now
        })

    def read(self, session_id: str, key: str) -> dict[str, Any] | None:
        import json
        redis_key = f"memory:{session_id}:{key}"
        blob = self.client.hget(redis_key, "value")
        if blob is None:
            return None
        return json.loads(str(blob))

    def search(
        self,
        query: str,
        session_id: str | None = None,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        import json
        from redis.commands.search.query import Query
        import redis.exceptions

        tokens = query.strip().split()
        if not tokens:
            return self.all_records()[:top_k]

        fts_query = " | ".join(tokens)
        
        if session_id:
            # Escape session_id for tag query if it has dashes
            escaped_session = session_id.replace("-", "\\-")
            fts_query = f"(@session_id:{{{escaped_session}}}) ({fts_query})"
            
        q = Query(fts_query).paging(0, top_k)
        
        try:
            res = self.client.ft(self.index_name).search(q)
            return [json.loads(str(doc.value)) for doc in res.docs]
        except redis.exceptions.ResponseError:
            # Fallback if RediSearch is not available or query is malformed
            return []

    def all_records(self) -> list[dict[str, Any]]:
        import json
        records = []
        cursor = "0"
        while cursor != 0:
            cursor, keys = self.client.scan(cursor=cursor, match="memory:*", count=100)
            for key in keys:
                blob = self.client.hget(key, "value")
                if blob:
                    records.append(json.loads(str(blob)))
        return records

    def delete(self, session_id: str, key: str) -> bool:
        redis_key = f"memory:{session_id}:{key}"
        return self.client.delete(redis_key) > 0


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

_BACKEND_REGISTRY: dict[str, type[MemoryBackend]] = {
    "sqlite": SQLiteBackend,
    "redis": RedisBackend,
}


def create_backend(backend_name: str, memory_dir: str | Path) -> MemoryBackend:
    """Instantiate a ``MemoryBackend`` by name.

    Parameters
    ----------
    backend_name:
        Registry key — currently ``"sqlite"`` is the only built-in option.
    memory_dir:
        Directory that will hold the backend's data files.

    Returns
    -------
    MemoryBackend
        Ready-to-use backend instance.

    Raises
    ------
    ValueError
        If *backend_name* is not found in the registry.
    """
    cls = _BACKEND_REGISTRY.get(backend_name.strip().lower())
    if cls is None:
        supported = ", ".join(sorted(_BACKEND_REGISTRY))
        raise ValueError(
            f"Unknown memory backend '{backend_name}'. Supported: {supported}"
        )

    memory_dir = Path(memory_dir)

    if cls is SQLiteBackend:
        return SQLiteBackend(memory_dir / "long_term_memory.db")

    # Generic fallback — future backends may need different constructor args.
    return cls(memory_dir)  # type: ignore[call-arg]
