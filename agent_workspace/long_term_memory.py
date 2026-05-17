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

import argparse
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from memory_backends import MemoryBackend, SQLiteBackend, create_backend


SCHEMA_VERSION = "1.0.0"
DEFAULT_FILENAME = "long_term_memory.json"        # kept for reference only
DEFAULT_BACKEND = "sqlite"
TOKEN_PATTERN = re.compile(r"[\w\u4e00-\u9fff]+", re.UNICODE)


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

    def query(
        self,
        query_text: str,
        session_id: str | None = None,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Search long-term memory for records matching *query_text*."""
        return self._backend.search(query_text, session_id=session_id, top_k=limit)

    def all_records(self) -> list[dict[str, Any]]:
        """Return every stored record."""
        return self._backend.all_records()

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


if __name__ == "__main__":
    main()
