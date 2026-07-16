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

import os
import json
import sqlite3
import logging
import threading
import httpx
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agent_workspace.core.security import validate_session_id

logger = logging.getLogger(__name__)


def _offline_mode() -> bool:
    return os.environ.get("LAS_OFFLINE_MODE", "").lower() in {
        "1", "true", "yes"
    }


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

    def close(self) -> None:
        """Close connection to backend."""
        pass


class VectorMemoryStore(MemoryBackend):
    """Abstract base class for vector-enabled memory backends."""

    @abstractmethod
    def search_by_vector(
        self,
        embedding: list[float],
        session_id: str | None = None,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Search using a vector embedding directly."""


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

    _lock = threading.RLock()

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
        DELETE FROM memory_fts WHERE rowid = old.rowid;
    END;
    """

    _TRIGGER_UPDATE = """
    CREATE TRIGGER IF NOT EXISTS memory_fts_update AFTER UPDATE OF value ON memory_records BEGIN
        UPDATE memory_fts
        SET session_id = new.session_id,
            key = new.key,
            summary = json_extract(new.value, '$.summary'),
            keywords = json_extract(new.value, '$.keywords')
        WHERE rowid = new.rowid;
    END;
    """

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._connections = []
        # Initialise schema on the calling thread's connection.
        self._init_schema()

    def close(self) -> None:
        conn = getattr(self._local, "conn", None)
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
            self._local.conn = None
            with self._lock:
                if conn in self._connections:
                    self._connections.remove(conn)

    def close_all(self) -> None:
        with self._lock:
            for conn in self._connections:
                try:
                    conn.close()
                except Exception:
                    pass
            self._connections.clear()
        self._local.conn = None

    def __del__(self) -> None:
        self.close_all()

    # -- connection-per-thread ------------------------------------------------

    def _get_conn(self) -> sqlite3.Connection:
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(str(self.db_path), timeout=30.0)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.row_factory = sqlite3.Row
            self._local.conn = conn
            with self._lock:
                self._connections.append(conn)
        return conn

    def _init_schema(self) -> None:
        with self._lock:
            conn = self._get_conn()
            conn.executescript(self._DDL)
            conn.executescript(self._TRIGGER_INSERT)
            conn.executescript(self._TRIGGER_DELETE)
            conn.executescript(self._TRIGGER_UPDATE)
            conn.commit()

    # -- public API -----------------------------------------------------------

    def write(self, session_id: str, key: str, value: dict[str, Any]) -> None:
        session_id = validate_session_id(session_id)
        with self._lock:
            conn = self._get_conn()
            now = datetime.now(timezone.utc).isoformat()
            blob = json.dumps(value, ensure_ascii=False)
            conn.execute("BEGIN IMMEDIATE")
            try:
                conn.execute(
                    """
                    INSERT INTO memory_records (session_id, key, value, created_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(session_id, key) DO UPDATE SET value = excluded.value, created_at = excluded.created_at
                    """,
                    (session_id, key, blob, now),
                )
                conn.commit()
            except Exception:
                conn.rollback()
                raise

    def read(self, session_id: str, key: str) -> dict[str, Any] | None:
        session_id = validate_session_id(session_id)
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
        if session_id is not None:
            session_id = validate_session_id(session_id)
        conn = self._get_conn()

        # Build FTS5 match expression — quote each token to avoid syntax errors
        if ":" in query or '"' in query:
            fts_query = query
        else:
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
        session_id = validate_session_id(session_id)
        with self._lock:
            conn = self._get_conn()
            conn.execute("BEGIN IMMEDIATE")
            try:
                cursor = conn.execute(
                    "DELETE FROM memory_records WHERE session_id = ? AND key = ?",
                    (session_id, key),
                )
                conn.commit()
                return cursor.rowcount > 0
            except Exception:
                conn.rollback()
                raise


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
# File implementation — pure local files (episodic, semantic, handoff)
# ---------------------------------------------------------------------------

class FileBackend(MemoryBackend):
    """File-backed long-term memory storing records in standard PAP directories."""

    def __init__(self, memory_dir: str | Path) -> None:
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        (self.memory_dir / "episodic").mkdir(parents=True, exist_ok=True)
        (self.memory_dir / "semantic").mkdir(parents=True, exist_ok=True)
        (self.memory_dir / "handoff").mkdir(parents=True, exist_ok=True)

    def write(self, session_id: str, key: str, value: dict[str, Any]) -> None:
        domain = value.get("domain", "episodic")
        if domain == "episodic":
            target_dir = self.memory_dir / "episodic"
        elif domain in ("semantic", "preference"):
            target_dir = self.memory_dir / "semantic"
        elif domain == "handoff":
            target_dir = self.memory_dir / "handoff"
        else:
            target_dir = self.memory_dir
        
        target_dir.mkdir(parents=True, exist_ok=True)
        file_path = target_dir / f"{key}.json"
        
        import json
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(value, f, ensure_ascii=False, indent=2)

    def read(self, session_id: str, key: str) -> dict[str, Any] | None:
        for p in self.memory_dir.rglob(f"{key}.json"):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    import json
                    return json.load(f)
            except Exception:
                pass
        return None

    def search(
        self,
        query: str,
        session_id: str | None = None,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        tokens = [t.lower() for t in query.strip().split() if t]
        if not tokens:
            return self.all_records()[:top_k]
        
        matched = []
        for record in self.all_records():
            if session_id and record.get("session_id") != session_id:
                continue
            summary = (record.get("summary") or "").lower()
            keywords = [k.lower() for k in record.get("keywords") or []]
            
            score = 0
            for token in tokens:
                if token in summary:
                    score += 1
                for kw in keywords:
                    if token in kw:
                        score += 2
            if score > 0:
                matched.append((score, record))
        
        matched.sort(key=lambda x: x[0], reverse=True)
        return [r for score, r in matched[:top_k]]

    def all_records(self) -> list[dict[str, Any]]:
        records = []
        for p in self.memory_dir.rglob("*.json"):
            if p.name == "schema.json":
                continue
            try:
                with open(p, "r", encoding="utf-8") as f:
                    import json
                    records.append(json.load(f))
            except Exception:
                pass
        # Sort by created_at descending
        records.sort(key=lambda r: r.get("created_at", ""), reverse=True)
        return records

    def delete(self, session_id: str, key: str) -> bool:
        deleted = False
        for p in self.memory_dir.rglob(f"{key}.json"):
            try:
                p.unlink()
                deleted = True
            except Exception:
                pass
        return deleted


# ---------------------------------------------------------------------------
# Chroma REST implementation — pure HTTP REST APIs without binary chromadb
# ---------------------------------------------------------------------------

class ChromaBackend(VectorMemoryStore):
    """ChromaDB HTTP REST client backend."""
    _lock = threading.Lock()

    def __init__(self, db_path_or_memory_dir: str | Path) -> None:
        self.memory_dir = Path(db_path_or_memory_dir)
        self.sqlite_fallback = None
        self._local = threading.local()

        if _offline_mode():
            self.sqlite_fallback = SQLiteBackend(self.memory_dir / "long_term_memory.db")
            return

        self.host = os.environ.get("CHROMA_HOST", "localhost")
        self.port = os.environ.get("CHROMA_PORT", "8000")
        self.collection_name = os.environ.get("CHROMA_COLLECTION", "las_memory")
        self.base_url = f"http://{self.host}:{self.port}/api/v1"

        try:
            self._get_client()
            self._get_collection_id()
        except Exception as e:
            logger.warning("[ChromaBackend] Connection failed, falling back to SQLite. Error: %s", e)
            self.sqlite_fallback = SQLiteBackend(self.memory_dir / "long_term_memory.db")

    def _get_client(self) -> httpx.Client:
        client = getattr(self._local, "client", None)
        if client is None:
            client = httpx.Client(timeout=10.0)
            self._local.client = client
        return client

    def _init_collection(self) -> None:
        with self._lock:
            client = self._get_client()
            url = f"{self.base_url}/collections"
            payload = {"name": self.collection_name, "metadata": None, "get_or_create": True}
            response = client.post(url, json=payload)
            response.raise_for_status()
            self.collection_id = response.json()["id"]

    def _get_collection_id(self) -> str:
        if not hasattr(self, "collection_id") or not self.collection_id:
            self._init_collection()
        return self.collection_id

    def write(self, session_id: str, key: str, value: dict[str, Any]) -> None:
        if self.sqlite_fallback:
            self.sqlite_fallback.write(session_id, key, value)
            return
        try:
            client = self._get_client()
            coll_id = self._get_collection_id()
            url = f"{self.base_url}/collections/{coll_id}/upsert"

            embedding = value.get("payload", {}).get("embedding")
            if not embedding:
                from core.embeddings import generate_mock_embedding
                summary = value.get("summary", "") or key
                embedding = generate_mock_embedding(summary, 1536)

            payload = {
                "ids": [key],
                "embeddings": [embedding],
                "metadatas": [{"session_id": session_id, "key": key, "created_at": value.get("created_at", "")}],
                "documents": [json.dumps(value, ensure_ascii=False)]
            }
            response = client.post(url, json=payload)
            response.raise_for_status()
        except Exception as e:
            logger.warning("[ChromaBackend] Write failed, falling back to SQLite. Error: %s", e)
            if not self.sqlite_fallback:
                self.sqlite_fallback = SQLiteBackend(self.memory_dir / "long_term_memory.db")
            self.sqlite_fallback.write(session_id, key, value)

    def read(self, session_id: str, key: str) -> dict[str, Any] | None:
        if self.sqlite_fallback:
            return self.sqlite_fallback.read(session_id, key)
        try:
            client = self._get_client()
            coll_id = self._get_collection_id()
            url = f"{self.base_url}/collections/{coll_id}/get"
            payload = {
                "ids": [key],
                "where": {"session_id": session_id}
            }
            response = client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            documents = data.get("documents", [])
            if not documents or not documents[0]:
                return None
            return json.loads(documents[0])
        except Exception as e:
            logger.warning("[ChromaBackend] Read failed, falling back to SQLite. Error: %s", e)
            if not self.sqlite_fallback:
                self.sqlite_fallback = SQLiteBackend(self.memory_dir / "long_term_memory.db")
            return self.sqlite_fallback.read(session_id, key)

    def search(
        self,
        query: str,
        session_id: str | None = None,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        if self.sqlite_fallback:
            return self.sqlite_fallback.search(query, session_id=session_id, top_k=top_k)
        try:
            from core.embeddings import EmbeddingGenerator
            generator = EmbeddingGenerator()
            embedding = generator.get_embedding(query)
            return self.search_by_vector(embedding, session_id=session_id, top_k=top_k)
        except Exception as e:
            logger.warning("[ChromaBackend] Search failed, falling back to SQLite. Error: %s", e)
            if not self.sqlite_fallback:
                self.sqlite_fallback = SQLiteBackend(self.memory_dir / "long_term_memory.db")
            return self.sqlite_fallback.search(query, session_id=session_id, top_k=top_k)

    def search_by_vector(
        self,
        embedding: list[float],
        session_id: str | None = None,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        if self.sqlite_fallback:
            return self.sqlite_fallback.all_records()[:top_k]
        try:
            client = self._get_client()
            coll_id = self._get_collection_id()
            url = f"{self.base_url}/collections/{coll_id}/query"
            payload = {
                "query_embeddings": [embedding],
                "n_results": top_k,
                "include": ["documents", "metadatas", "distances"]
            }
            if session_id:
                payload["where"] = {"session_id": session_id}

            response = client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

            documents = data.get("documents", [])
            if not documents or not documents[0]:
                return []

            results = []
            for doc in documents[0]:
                if doc:
                    results.append(json.loads(doc))
            return results
        except Exception as e:
            logger.warning("[ChromaBackend] search_by_vector failed, falling back to SQLite. Error: %s", e)
            if not self.sqlite_fallback:
                self.sqlite_fallback = SQLiteBackend(self.memory_dir / "long_term_memory.db")
            return self.sqlite_fallback.all_records()[:top_k]

    def all_records(self) -> list[dict[str, Any]]:
        if self.sqlite_fallback:
            return self.sqlite_fallback.all_records()
        try:
            client = self._get_client()
            coll_id = self._get_collection_id()
            url = f"{self.base_url}/collections/{coll_id}/get"
            payload = {
                "limit": 10000,
                "include": ["documents"]
            }
            response = client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            documents = data.get("documents", [])
            if not documents:
                return []
            return [json.loads(doc) for doc in documents if doc]
        except Exception as e:
            logger.warning("[ChromaBackend] all_records failed, falling back to SQLite. Error: %s", e)
            if not self.sqlite_fallback:
                self.sqlite_fallback = SQLiteBackend(self.memory_dir / "long_term_memory.db")
            return self.sqlite_fallback.all_records()

    def delete(self, session_id: str, key: str) -> bool:
        if self.sqlite_fallback:
            return self.sqlite_fallback.delete(session_id, key)
        try:
            client = self._get_client()
            coll_id = self._get_collection_id()
            url = f"{self.base_url}/collections/{coll_id}/delete"
            payload = {
                "ids": [key],
                "where": {"session_id": session_id}
            }
            response = client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            return len(data) > 0 if isinstance(data, list) else bool(data)
        except Exception as e:
            logger.warning("[ChromaBackend] Delete failed, falling back to SQLite. Error: %s", e)
            if not self.sqlite_fallback:
                self.sqlite_fallback = SQLiteBackend(self.memory_dir / "long_term_memory.db")
            return self.sqlite_fallback.delete(session_id, key)

    def close(self) -> None:
        client = getattr(self._local, "client", None)
        if client is not None:
            try:
                client.close()
            except Exception:
                pass
            self._local.client = None
        if self.sqlite_fallback:
            self.sqlite_fallback.close()

    def __del__(self) -> None:
        self.close()


# ---------------------------------------------------------------------------
# Pgvector implementation — using psycopg2
# ---------------------------------------------------------------------------

class PgvectorBackend(VectorMemoryStore):
    """PostgreSQL / pgvector long-term memory backend."""
    _lock = threading.Lock()

    def __init__(self, db_path_or_memory_dir: str | Path) -> None:
        self.memory_dir = Path(db_path_or_memory_dir)
        self.sqlite_fallback = None
        self._local = threading.local()

        if _offline_mode():
            self.sqlite_fallback = SQLiteBackend(self.memory_dir / "long_term_memory.db")
            return

        self.host = os.environ.get("PG_HOST", "localhost")
        self.port = os.environ.get("PG_PORT", "5432")
        self.user = os.environ.get("PG_USER", "postgres")
        self.password = os.environ.get("PG_PASSWORD", "postgres")
        self.database = os.environ.get("PG_DATABASE", "postgres")

        try:
            import psycopg2
            conn = self._get_conn()
            self._init_schema(conn)
        except Exception as e:
            logger.warning("[PgvectorBackend] Connection failed, falling back to SQLite. Error: %s", e)
            self.sqlite_fallback = SQLiteBackend(self.memory_dir / "long_term_memory.db")

    def _get_conn(self):
        conn = getattr(self._local, "conn", None)
        if conn is None:
            import psycopg2
            conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                connect_timeout=5
            )
            conn.autocommit = True
            self._local.conn = conn
        return conn

    def _init_schema(self, conn) -> None:
        with self._lock:
            with conn.cursor() as cur:
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS las_memory (
                        session_id  VARCHAR(255) NOT NULL,
                        key         VARCHAR(255) NOT NULL,
                        value       TEXT NOT NULL,
                        created_at  VARCHAR(255) NOT NULL,
                        embedding   vector(1536),
                        PRIMARY KEY (session_id, key)
                    );
                """)

    def write(self, session_id: str, key: str, value: dict[str, Any]) -> None:
        if self.sqlite_fallback:
            self.sqlite_fallback.write(session_id, key, value)
            return
        try:
            conn = self._get_conn()
            embedding = value.get("payload", {}).get("embedding")
            if not embedding:
                from core.embeddings import generate_mock_embedding
                summary = value.get("summary", "") or key
                embedding = generate_mock_embedding(summary, 1536)

            blob = json.dumps(value, ensure_ascii=False)
            created_at = value.get("created_at", "")

            with self._lock:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO las_memory (session_id, key, value, created_at, embedding)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (session_id, key) DO UPDATE
                        SET value = EXCLUDED.value, created_at = EXCLUDED.created_at, embedding = EXCLUDED.embedding;
                    """, (session_id, key, blob, created_at, embedding))
        except Exception as e:
            logger.warning("[PgvectorBackend] Write failed, falling back to SQLite. Error: %s", e)
            if not self.sqlite_fallback:
                self.sqlite_fallback = SQLiteBackend(self.memory_dir / "long_term_memory.db")
            self.sqlite_fallback.write(session_id, key, value)

    def read(self, session_id: str, key: str) -> dict[str, Any] | None:
        if self.sqlite_fallback:
            return self.sqlite_fallback.read(session_id, key)
        try:
            conn = self._get_conn()
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT value FROM las_memory WHERE session_id = %s AND key = %s;",
                    (session_id, key)
                )
                row = cur.fetchone()
                if row is None:
                    return None
                return json.loads(row[0])
        except Exception as e:
            logger.warning("[PgvectorBackend] Read failed, falling back to SQLite. Error: %s", e)
            if not self.sqlite_fallback:
                self.sqlite_fallback = SQLiteBackend(self.memory_dir / "long_term_memory.db")
            return self.sqlite_fallback.read(session_id, key)

    def search(
        self,
        query: str,
        session_id: str | None = None,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        if self.sqlite_fallback:
            return self.sqlite_fallback.search(query, session_id=session_id, top_k=top_k)
        try:
            from core.embeddings import EmbeddingGenerator
            generator = EmbeddingGenerator()
            embedding = generator.get_embedding(query)
            return self.search_by_vector(embedding, session_id=session_id, top_k=top_k)
        except Exception as e:
            logger.warning("[PgvectorBackend] Search failed, falling back to SQLite. Error: %s", e)
            if not self.sqlite_fallback:
                self.sqlite_fallback = SQLiteBackend(self.memory_dir / "long_term_memory.db")
            return self.sqlite_fallback.search(query, session_id=session_id, top_k=top_k)

    def search_by_vector(
        self,
        embedding: list[float],
        session_id: str | None = None,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        if self.sqlite_fallback:
            return self.sqlite_fallback.all_records()[:top_k]
        try:
            conn = self._get_conn()
            with conn.cursor() as cur:
                if session_id:
                    cur.execute("""
                        SELECT value FROM las_memory
                        WHERE session_id = %s
                        ORDER BY embedding <=> %s::vector
                        LIMIT %s;
                    """, (session_id, embedding, top_k))
                else:
                    cur.execute("""
                        SELECT value FROM las_memory
                        ORDER BY embedding <=> %s::vector
                        LIMIT %s;
                    """, (embedding, top_k))
                rows = cur.fetchall()
                return [json.loads(row[0]) for row in rows]
        except Exception as e:
            logger.warning("[PgvectorBackend] search_by_vector failed, falling back to SQLite. Error: %s", e)
            if not self.sqlite_fallback:
                self.sqlite_fallback = SQLiteBackend(self.memory_dir / "long_term_memory.db")
            return self.sqlite_fallback.all_records()[:top_k]

    def all_records(self) -> list[dict[str, Any]]:
        if self.sqlite_fallback:
            return self.sqlite_fallback.all_records()
        try:
            conn = self._get_conn()
            with conn.cursor() as cur:
                cur.execute("SELECT value FROM las_memory ORDER BY created_at DESC;")
                rows = cur.fetchall()
                return [json.loads(row[0]) for row in rows]
        except Exception as e:
            logger.warning("[PgvectorBackend] all_records failed, falling back to SQLite. Error: %s", e)
            if not self.sqlite_fallback:
                self.sqlite_fallback = SQLiteBackend(self.memory_dir / "long_term_memory.db")
            return self.sqlite_fallback.all_records()

    def delete(self, session_id: str, key: str) -> bool:
        if self.sqlite_fallback:
            return self.sqlite_fallback.delete(session_id, key)
        try:
            conn = self._get_conn()
            with self._lock:
                with conn.cursor() as cur:
                    cur.execute(
                        "DELETE FROM las_memory WHERE session_id = %s AND key = %s;",
                        (session_id, key)
                    )
                    rowcount = cur.rowcount
                    return rowcount > 0
        except Exception as e:
            logger.warning("[PgvectorBackend] Delete failed, falling back to SQLite. Error: %s", e)
            if not self.sqlite_fallback:
                self.sqlite_fallback = SQLiteBackend(self.memory_dir / "long_term_memory.db")
            return self.sqlite_fallback.delete(session_id, key)

    def close(self) -> None:
        conn = getattr(self._local, "conn", None)
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
            self._local.conn = None
        if self.sqlite_fallback:
            self.sqlite_fallback.close()

    def __del__(self) -> None:
        self.close()


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

_BACKEND_REGISTRY: dict[str, type[MemoryBackend]] = {
    "sqlite": SQLiteBackend,
    "redis": RedisBackend,
    "file": FileBackend,
    "chroma": ChromaBackend,
    "pgvector": PgvectorBackend,
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
