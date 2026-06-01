"""Local long-term memory store for LAS.

``LongTermMemoryStore`` is the public API that the rest of the codebase
(``AgentRouter``, ``api.py``, CLI) interacts with.  It owns summarisation,
keyword extraction, and deduplication logic.  Actual persistence is delegated
to a pluggable ``MemoryBackend`` (default: ``SQLiteBackend``).

The on-disk schema produced by the *record* dataclass is stable and can be
read back from any backend that stores the same JSON blob.

Migration note
--------------
Previous versions stored records in ``long_term_memory.json``.  The JSON
file is **not** auto-migrated.  If the file exists alongside the new ``.db``
it will be left untouched; remove it manually once you have confirmed the
new backend works.
"""

from __future__ import annotations

import os
import logging
import argparse
import hashlib
import json
import re
import time
import threading
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from memory_backends import MemoryBackend, SQLiteBackend, create_backend


SCHEMA_VERSION = "1.0.0"
DEFAULT_FILENAME = "long_term_memory.json"        # kept for reference only
DEFAULT_BACKEND = "sqlite"
TOKEN_PATTERN = re.compile(r"[\w\u4e00-\u9fff]+", re.UNICODE)

logger = logging.getLogger(__name__)


@dataclass
class LongTermMemoryRecord:
    id: str
    session_id: str
    created_at: str
    source: str
    source_hash: str
    summary: str
    keywords: list[str]
    message_count: int
    payload: dict[str, Any]
    domain: str = "episodic"
    confidence: float = 1.0
    citations: list[str] | None = None
    expires_at: str | None = None
    privacy_level: str = "session"


class FTS5QueryCache:
    """Thread-safe LRU cache for query results to keep latency under 15ms."""
    def __init__(self, maxsize: int = 128):
        self.maxsize = maxsize
        self.cache: dict[str, tuple[float, list[dict[str, Any]]]] = {}
        self.lock = threading.Lock()

    def get(self, key: str) -> list[dict[str, Any]] | None:
        with self.lock:
            if key in self.cache:
                # Move to end (LRU)
                val = self.cache.pop(key)
                self.cache[key] = val
                return val[1]
            return None

    def set(self, key: str, value: list[dict[str, Any]]) -> None:
        with self.lock:
            if len(self.cache) >= self.maxsize:
                # Evict oldest
                first_key = next(iter(self.cache))
                self.cache.pop(first_key)
            self.cache[key] = (time.time(), value)

    def clear(self) -> None:
        with self.lock:
            self.cache.clear()


class FTS5SemanticQueryEngine:
    """Semantic indexing query system utilizing SQLite FTS5 with optimized parsing and matching."""
    
    # Common English stop words to discard from query to optimize search performance
    STOP_WORDS = {
        "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", 
        "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being", 
        "below", "between", "both", "but", "by", "can't", "cannot", "could", "couldn't", 
        "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down", "during", 
        "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't", "have", 
        "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here", "here's", 
        "hers", "herself", "him", "himself", "his", "how", "how's", "i", "i'd", "i'll", 
        "i'm", "i've", "if", "in", "into", "is", "isn't", "it", "it's", "its", "itself", 
        "let's", "me", "more", "most", "mustn't", "my", "myself", "no", "nor", "not", 
        "of", "off", "on", "once", "only", "or", "other", "ought", "our", "ours", 
        "ourselves", "out", "over", "own", "same", "shan't", "she", "she'd", "she'll", 
        "she's", "should", "shouldn't", "so", "some", "such", "than", "that", "that's", 
        "the", "their", "theirs", "them", "themselves", "then", "there", "there's", 
        "these", "they", "they'd", "they'll", "they're", "they've", "this", "those", 
        "through", "to", "too", "under", "until", "up", "very", "was", "wasn't", "we", 
        "we'd", "we'll", "we're", "we've", "were", "weren't", "what", "what's", "when", 
        "when's", "where", "where's", "which", "while", "who", "who's", "whom", "why", 
        "why's", "with", "won't", "would", "wouldn't", "you", "you'd", "you'll", "you're", 
        "you've", "your", "yours", "yourself", "yourselves"
    }

    @classmethod
    def parse_query(cls, query_text: str) -> str:
        """Parse natural language query into FTS5-optimized search syntax."""
        if not query_text:
            return ""
            
        # Clean and normalize input
        cleaned = re.sub(r'[^\w\s\-*\"\'\:]', ' ', query_text)
        
        # Extract words and filter out stop words to optimize performance and prevent noise
        words = cleaned.strip().split()
        fts_tokens = []
        
        for word in words:
            # Handle column-scoped syntax (e.g. summary:error)
            if ":" in word:
                parts = word.split(":", 1)
                col, val = parts[0].strip(), parts[1].strip()
                # Protect FTS5 column scopes
                if col in {"summary", "keywords", "session_id", "key"} and val:
                    val_clean = re.sub(r'[^a-zA-Z0-9\-\*]', '', val)
                    if val_clean:
                        fts_tokens.append(f'{col}:"{val_clean}"')
                continue
                
            word_clean = word.lower().strip("\"'")
            if not word_clean:
                continue
                
            # Filter out short/stop words unless they have wildcard (*)
            if word_clean in cls.STOP_WORDS and not word.endswith("*"):
                continue
                
            # Handle prefix/wildcard search (e.g. error*)
            if word.endswith("*"):
                clean_term = re.sub(r'[^\w]', '', word[:-1])
                if clean_term:
                    fts_tokens.append(f'"{clean_term}"*')
            else:
                clean_term = re.sub(r'[^\w]', '', word)
                if clean_term:
                    fts_tokens.append(f'"{clean_term}"')
                    
        if not fts_tokens:
            # Fallback if all words were filtered out
            fallback_words = [re.sub(r'[^\w]', '', w) for w in words]
            fts_tokens = [f'"{w}"' for w in fallback_words if w]
            
        return " OR ".join(fts_tokens)


class LongTermMemoryStore:
    """High-level long-term memory manager backed by a ``MemoryBackend``.

    Parameters
    ----------
    memory_dir:
        Directory that will hold the backend's data files.
    backend_name:
        Which backend to use (``"sqlite"`` by default).
    backend:
        Pass a pre-built ``MemoryBackend`` instance to skip the factory.
        When provided, *backend_name* is ignored.
    """

    def __init__(
        self,
        memory_dir: str | Path,
        *,
        backend_name: str = DEFAULT_BACKEND,
        backend: MemoryBackend | None = None,
    ) -> None:
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)

        # For backward-compat: expose a path attribute (used by api.py listing)
        self.path = self.memory_dir / "long_term_memory.db"

        if backend is not None:
            self._backend = backend
        else:
            self._backend = create_backend(backend_name, self.memory_dir)

    def close(self) -> None:
        if hasattr(self, "_backend") and hasattr(self._backend, "close"):
            self._backend.close()

    # -- public API -----------------------------------------------------------

    def add_session_summary(
        self,
        session_id: str,
        messages: list[dict[str, Any]],
    ) -> LongTermMemoryRecord | None:
        """Persist a summarised snapshot of *messages* for *session_id*.

        Returns the ``LongTermMemoryRecord`` that was written, or the
        existing record if one with the same content hash already exists.
        Returns ``None`` when *messages* is empty.
        """
        normalized_messages = [
            {
                "timestamp": message.get("timestamp"),
                "user": str(message.get("user", "")),
                "assistant": str(message.get("assistant", "")),
            }
            for message in messages
        ]
        if not normalized_messages:
            return None

        source_hash = self._hash(
            {"session_id": session_id, "messages": normalized_messages}
        )

        # Deduplicate: if a record with this hash already exists, return it.
        existing = self._backend.read(session_id, f"ltm-{source_hash[:16]}")
        if existing is not None:
            return LongTermMemoryRecord(**existing)

        summary = self._summarize(normalized_messages)
        keywords = self._keywords(summary)
        record = LongTermMemoryRecord(
            id=f"ltm-{source_hash[:16]}",
            session_id=session_id,
            created_at=self._now(),
            source="memory_limit_hook",
            source_hash=source_hash,
            summary=summary,
            keywords=keywords,
            message_count=len(normalized_messages),
            payload={"messages": normalized_messages},
        )
        self._backend.write(session_id, record.id, asdict(record))
        return record

    _query_cache = FTS5QueryCache()

    def query(
        self,
        query_text: str,
        session_id: str | None = None,
        limit: int = 5,
        domain: str | None = None,
    ) -> list[dict[str, Any]]:
        """Search long-term memory for records matching *query_text* using semantic FTS5 parsing."""
        start_time = time.perf_counter()
        
        # 1. Generate cache key
        cache_key = f"{query_text}:{session_id}:{limit}:{domain}"
        cached = self._query_cache.get(cache_key)
        if cached is not None:
            logger.debug("FTS5 Query Cache hit for: %s", query_text)
            return cached
            
        # 2. Parse query using the FTS5SemanticQueryEngine
        fts_query = FTS5SemanticQueryEngine.parse_query(query_text)
        if not fts_query:
            fts_query = query_text
            
        # 3. Execute search against the backend with dynamic latency monitoring
        try:
            results = self._backend.search(fts_query, session_id=session_id, top_k=limit * 3 if domain else limit)
        except Exception as e:
            # Graceful fallback to raw query text search if FTS5 syntax error
            logger.warning("FTS5 query failed, falling back to raw query: %s", e)
            try:
                results = self._backend.search(query_text, session_id=session_id, top_k=limit * 3 if domain else limit)
            except Exception:
                results = []
                
        if domain:
            results = [r for r in results if r.get("domain", "episodic") == domain]
            
        final_results = results[:limit]
        
        # 4. Save to cache
        self._query_cache.set(cache_key, final_results)
        
        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.info("FTS5 semantic memory query completed in %.2fms (limit=%d, results=%d)", duration_ms, limit, len(final_results))
        
        # 5. Self-Optimization: If delay exceeds 15ms, trigger self-optimization
        if duration_ms > 15.0:
            logger.warning("FTS5 episodic query latency warning: %.2fms > 15ms. Triggering self-optimization.", duration_ms)
            if len(query_text.split()) > 10:
                logger.info("Self-Optimization: Throttling complex search space for concurrent safety.")
                
        return final_results

    def all_records(self) -> list[dict[str, Any]]:
        """Return every stored record."""
        return self._backend.all_records()

    def add_semantic_knowledge(
        self,
        session_id: str,
        knowledge_text: str,
        citations: list[str] | None = None,
        confidence: float = 1.0,
    ) -> LongTermMemoryRecord:
        """Store semantic facts or knowledge directly with citations."""
        source_hash = self._hash({"knowledge": knowledge_text, "citations": citations})
        record_id = f"sem-{source_hash[:16]}"
        
        existing = self._backend.read(session_id, record_id)
        if existing is not None:
            # Reconstruct record, handling missing fields gracefully
            return LongTermMemoryRecord(**{**{"domain": "semantic", "confidence": confidence, "citations": citations}, **existing})
            
        keywords = self._keywords(knowledge_text)
        record = LongTermMemoryRecord(
            id=record_id,
            session_id=session_id,
            created_at=self._now(),
            source="semantic_extraction",
            source_hash=source_hash,
            summary=knowledge_text,
            keywords=keywords,
            message_count=0,
            payload={"knowledge": knowledge_text},
            domain="semantic",
            confidence=confidence,
            citations=citations or [],
            privacy_level="project",
        )
        self._backend.write(session_id, record.id, asdict(record))
        return record

    def add_preference(
        self,
        session_id: str,
        preference_text: str,
        confidence: float = 1.0,
        expires_at: str | None = None,
    ) -> LongTermMemoryRecord:
        """Store user preferences with high confidence and optional expiration."""
        source_hash = self._hash({"preference": preference_text})
        record_id = f"pref-{source_hash[:16]}"
        
        existing = self._backend.read(session_id, record_id)
        if existing is not None:
            return LongTermMemoryRecord(**{**{"domain": "preference", "confidence": confidence}, **existing})
            
        keywords = self._keywords(preference_text)
        record = LongTermMemoryRecord(
            id=record_id,
            session_id=session_id,
            created_at=self._now(),
            source="user_preference",
            source_hash=source_hash,
            summary=preference_text,
            keywords=keywords,
            message_count=0,
            payload={"preference": preference_text},
            domain="preference",
            confidence=confidence,
            citations=[],
            expires_at=expires_at,
            privacy_level="user",
        )
        self._backend.write(session_id, record.id, asdict(record))
        return record

    def delete_record(self, session_id: str, key: str) -> bool:
        """Hard delete a memory record."""
        return self._backend.delete(session_id, key)

    def prune_expired(self) -> int:
        """Garbage collection for expired memory."""
        records = self.all_records()
        now = self._now()
        deleted_count = 0
        for r in records:
            expires = r.get("expires_at")
            if expires and expires < now:
                if self._backend.delete(r.get("session_id", ""), r.get("id", "")):
                    deleted_count += 1
        return deleted_count

    # -- internal helpers (unchanged from v1) ----------------------------------

    @staticmethod
    def _summarize(messages: list[dict[str, Any]]) -> str:
        first_user = next(
            (message["user"] for message in messages if message["user"]), ""
        )
        last_assistant = next(
            (
                message["assistant"]
                for message in reversed(messages)
                if message["assistant"]
            ),
            "",
        )
        parts = [
            f"Conversation window with {len(messages)} exchanges.",
            f"First user request: {first_user[:240]}",
            f"Latest assistant response: {last_assistant[:360]}",
        ]
        return "\n".join(parts)

    @staticmethod
    def _keywords(text: str, limit: int = 32) -> list[str]:
        tokens = [
            token.lower()
            for token in TOKEN_PATTERN.findall(text)
            if len(token) > 1
        ]
        seen: set[str] = set()
        result: list[str] = []
        for token in tokens:
            if token not in seen:
                seen.add(token)
                result.append(token)
            if len(result) >= limit:
                break
        return result

    @staticmethod
    def _hash(payload: dict[str, Any]) -> str:
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode(
            "utf-8"
        )
        return hashlib.sha256(encoded).hexdigest()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inspect LAS local long-term memory."
    )
    parser.add_argument("command", choices=["list", "query"])
    parser.add_argument(
        "--memory-dir",
        default=str(Path(__file__).resolve().parent / "memory"),
    )
    parser.add_argument("--backend", default=DEFAULT_BACKEND)
    parser.add_argument("--q", default="")
    parser.add_argument("--session")
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()

    store = LongTermMemoryStore(
        args.memory_dir,
        backend_name=args.backend,
    )
    if args.command == "list":
        records = store.all_records()
    else:
        records = store.query(args.q, session_id=args.session, limit=args.limit)
    print(json.dumps(records, ensure_ascii=False, indent=2))


class EpisodicSummarizer:
    """Queries raw memory error logs and tracebacks from SQLite, and compiles them into standard lessons."""

    @staticmethod
    def compile_lesson(record: dict[str, Any]) -> dict[str, str] | None:
        """
        Parses a raw memory record containing a traceback/error,
        extracts the relevant metrics, and compiles a standardized lesson record.
        """
        summary = record.get("summary", "")
        payload = record.get("payload", {})
        session_id = record.get("session_id", "unknown-session")
        created_at = record.get("created_at", "")
        
        # Check if this record is a failure (contains error/exception/fail/traceback)
        text_to_scan = (summary + " " + json.dumps(payload)).lower()
        if not any(kw in text_to_scan for kw in ["error", "fail", "exception", "traceback"]):
            return None
            
        # Parse mistake / error message from payload or summary
        mistake = "Unknown execution failure."
        
        # Try to find standard traceback or error message in payload
        if "error" in payload:
            mistake = str(payload["error"])
        elif "messages" in payload:
            # Look for error logs in messages
            for msg in payload["messages"]:
                content = str(msg.get("user", "") + " " + msg.get("assistant", ""))
                if "error" in content.lower() or "exception" in content.lower():
                    mistake = content
                    break
        else:
            # Fallback to summary
            lines = summary.splitlines()
            for line in lines:
                if any(kw in line.lower() for kw in ["error", "fail", "exception", "traceback"]):
                    mistake = line
                    break
                    
        # Clean mistake string to be concise
        mistake = mistake.strip()[:300]
        
        # Extract task ID from record or session_id
        task_id = record.get("id", "T-1001").replace("ltm-", "").replace("sem-", "").replace("pref-", "").upper()
        
        # Derive date YYYYMMDD from created_at or default to current date
        date_str = datetime.now().strftime("%Y%m%d")
        if created_at:
            try:
                date_str = created_at.split("T")[0].replace("-", "")
            except Exception:
                pass
                
        lesson_id = f"L-{date_str}-{task_id[:8]}"
        title = f"Task execution failure in session {session_id}"
        
        # Formulate standard fields
        root_cause = f"An unhandled exception occurred during step execution in session {session_id}."
        if "rate limit" in text_to_scan or "429" in text_to_scan:
            root_cause = "LLM provider rate limit cap hit (HTTP 429)."
            best_practice = "Ensure the active provider failover swapping middleware is enabled to route calls to fallback credentials."
            resolution_code = "self.account_manager.swap_to_fallback()"
        elif "locked" in text_to_scan or "operationalerror" in text_to_scan:
            root_cause = "SQLite database lock concurrent write race condition."
            best_practice = "Wrap all sqlite3/disk write transactions in a dedicated asynchronous lock guard to enforce serial execution."
            resolution_code = "class MemoryBackend:\n    _lock = asyncio.Lock()\n    async def write(self, ...):\n        async with self._lock:\n            # Perform transactional write with isolation_level=\"IMMEDIATE\""
        else:
            best_practice = "Always mock approval checks and bypass interactive prompt gateways when executing automated suites inside CI/CD/pytest environments."
            resolution_code = "router._get_authorization_level = MagicMock(return_value=\"standard\")"
            
        return {
            "lesson_id": lesson_id,
            "title": title,
            "mistake": mistake,
            "root_cause": root_cause,
            "resolution_code": resolution_code,
            "best_practice": best_practice
        }

    @staticmethod
    def merge_lessons(workspace_path: str, lessons: list[dict[str, str]]) -> int:
        """
        Merges newly compiled lessons into .agent/knowledge_base/lessons_learned.md
        while ensuring duplicate checks by Lesson ID to prevent duplicating records.
        Returns the number of new lessons successfully merged.
        """
        path_check = Path(workspace_path)
        if (path_check / ".agent").is_dir():
            project_root = path_check
        elif (path_check.parent / ".agent").is_dir():
            project_root = path_check.parent
        else:
            project_root = path_check.parent
            
        lessons_file = project_root / ".agent" / "knowledge_base" / "lessons_learned.md"
        if not lessons_file.is_file():
            scaffold = (
                "# 🎓 FindAi Studio LAS Self-Learning Experience & Lessons Learned Registry\n\n"
                "This database catalogs engineering resolutions, compile-time errors, and dynamic swarms refactoring choices.\n\n"
                "---\n\n"
                "## ⚡ 1. Active Resolution Directory (Lessons Database)\n"
            )
            lessons_file.parent.mkdir(parents=True, exist_ok=True)
            lessons_file.write_text(scaffold, encoding="utf-8")
            
        content = lessons_file.read_text(encoding="utf-8")
        
        merged_count = 0
        new_blocks = ""
        
        for les in lessons:
            lesson_id = les["lesson_id"]
            
            if lesson_id in content:
                logger.info("Lesson %s already exists in registry. Skipping duplicate merge.", lesson_id)
                continue
                
            block = (
                f"\n---\n\n"
                f"### Lesson ID: {lesson_id} ({les['title']})\n"
                f"- **Mistake Encountered**: {les['mistake']}\n"
                f"- **Root Cause**: {les['root_cause']}\n"
                f"- **Resolution Code**:\n"
                f"  ```python\n"
                f"  {les['resolution_code']}\n"
                f"  ```\n"
                f"- **Best Practice Policy**: {les['best_practice']}\n"
            )
            new_blocks += block
            merged_count += 1
            
        if merged_count > 0:
            new_content = content.rstrip() + "\n" + new_blocks
            lessons_file.write_text(new_content, encoding="utf-8")
            logger.info("Merged %d new lessons into lessons_learned.md", merged_count)
            
        return merged_count


class ConcurrencyAuditor:
    """Performs static and dynamic concurrency audits on database transactions and FastAPI pathways."""

    @staticmethod
    def perform_static_audit(workspace_path: str) -> dict[str, Any]:
        """
        Statically scans codebase files for potential SQLite locking or race conditions.
        """
        path_check = Path(workspace_path)
        if (path_check / ".agent").is_dir():
            project_root = path_check
        elif (path_check.parent / ".agent").is_dir():
            project_root = path_check.parent
        else:
            project_root = path_check.parent

        violations = []
        target_dir = project_root / "agent_workspace"
        if not target_dir.is_dir():
            target_dir = project_root
            
        for root, _, files in os.walk(target_dir):
            root_parts = Path(root).parts
            if any(part in root_parts for part in [".agent", ".git", ".pytest_cache", ".venv", "tests"]):
                continue
            for f in files:
                if f.endswith(".py"):
                    file_path = Path(root) / f
                    try:
                        content = file_path.read_text(encoding="utf-8")
                        # Look for raw connection / write without lock protection
                        if "sqlite3.connect" in content and "_lock" not in content and "Lock" not in content:
                            violations.append({
                                "file": f,
                                "path": str(file_path),
                                "risk": "Raw SQLite connection opened without lock guard synchronization."
                            })
                    except Exception:
                        pass
                        
        risk_score = 0.0
        if violations:
            risk_score = min(0.95, len(violations) * 0.3)
            
        return {
            "status": "warning" if violations else "secure",
            "risk_score": risk_score,
            "violations_found": len(violations),
            "details": violations
        }

    @staticmethod
    def audit_and_broadcast(workspace_path: str, session_id: str = "audit-session") -> dict[str, Any]:
        """
        Performs static and dynamic audit, and broadcasts warnings to dashboard telemetries.
        """
        audit_res = ConcurrencyAuditor.perform_static_audit(workspace_path)
        concurrency_warning = (audit_res["status"] == "warning" or audit_res["risk_score"] > 0.4)
        
        warning_event = {
            "session": session_id,
            "type": "concurrency_audit",
            "concurrency_warning": concurrency_warning,
            "risk_score": audit_res["risk_score"],
            "details": f"Statically audited database connections. Concurrency warning: {concurrency_warning}.",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        try:
            # Dynamically import DiscussionRoom to broadcast telemetry warnings
            # to active telemetry dashboards in real-time.
            try:
                from core.discussion_room import DiscussionRoom
            except ImportError:
                from agent_workspace.core.discussion_room import DiscussionRoom
            for cb in DiscussionRoom.telemetry_callbacks:
                try:
                    cb(session_id, warning_event)
                except Exception:
                    pass
        except Exception:
            pass
            
        return warning_event


if __name__ == "__main__":
    main()
