"""Local long-term memory store for LAS.

This is the first persistent-memory adapter. It is intentionally small and
dependency-free so it can run in development before a vector database backend is
introduced. The on-disk schema is stable JSON and can later be migrated to
Qdrant, Chroma, or Weaviate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "1.0.0"
DEFAULT_FILENAME = "long_term_memory.json"
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
    """JSON-backed persistent memory store with atomic writes."""

    def __init__(self, memory_dir: str | Path, filename: str = DEFAULT_FILENAME):
        self.memory_dir = Path(memory_dir)
        self.path = self.memory_dir / filename
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_file()

    def add_session_summary(self, session_id: str, messages: list[dict[str, Any]]) -> LongTermMemoryRecord | None:
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

        source_hash = self._hash({"session_id": session_id, "messages": normalized_messages})
        data = self._load()
        for record in data["records"]:
            if record.get("source_hash") == source_hash:
                return LongTermMemoryRecord(**record)

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
        data["records"].append(asdict(record))
        data["updated_at"] = record.created_at
        self._atomic_write(data)
        return record

    def query(self, query_text: str, session_id: str | None = None, limit: int = 5) -> list[dict[str, Any]]:
        data = self._load()
        query_tokens = set(self._keywords(query_text))
        scored: list[tuple[int, dict[str, Any]]] = []

        for record in data["records"]:
            if session_id and record.get("session_id") != session_id:
                continue
            haystack = set(record.get("keywords", []))
            if query_tokens:
                score = len(query_tokens & haystack)
            else:
                score = 0
            if query_text.lower() in record.get("summary", "").lower():
                score += 5
            scored.append((score, record))

        scored.sort(key=lambda item: (item[0], item[1].get("created_at", "")), reverse=True)
        return [record for score, record in scored[:limit] if score > 0 or not query_tokens]

    def all_records(self) -> list[dict[str, Any]]:
        return list(self._load()["records"])

    def _ensure_file(self) -> None:
        if not self.path.exists():
            self._atomic_write(
                {
                    "schema_version": SCHEMA_VERSION,
                    "created_at": self._now(),
                    "updated_at": self._now(),
                    "records": [],
                }
            )

    def _load(self) -> dict[str, Any]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = {}
        if data.get("schema_version") != SCHEMA_VERSION:
            data = {
                "schema_version": SCHEMA_VERSION,
                "created_at": self._now(),
                "updated_at": self._now(),
                "records": [],
            }
        data.setdefault("records", [])
        return data

    def _atomic_write(self, data: dict[str, Any]) -> None:
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(prefix=f".{self.path.name}.", suffix=".tmp", dir=self.memory_dir)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as tmp_file:
                json.dump(data, tmp_file, ensure_ascii=False, indent=2)
                tmp_file.write("\n")
            os.replace(tmp_name, self.path)
        finally:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)

    @staticmethod
    def _summarize(messages: list[dict[str, Any]]) -> str:
        first_user = next((message["user"] for message in messages if message["user"]), "")
        last_assistant = next((message["assistant"] for message in reversed(messages) if message["assistant"]), "")
        parts = [
            f"Conversation window with {len(messages)} exchanges.",
            f"First user request: {first_user[:240]}",
            f"Latest assistant response: {last_assistant[:360]}",
        ]
        return "\n".join(parts)

    @staticmethod
    def _keywords(text: str, limit: int = 32) -> list[str]:
        tokens = [token.lower() for token in TOKEN_PATTERN.findall(text) if len(token) > 1]
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
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect LAS local long-term memory.")
    parser.add_argument("command", choices=["list", "query"])
    parser.add_argument("--memory-dir", default=str(Path(__file__).resolve().parent / "memory"))
    parser.add_argument("--filename", default=DEFAULT_FILENAME)
    parser.add_argument("--q", default="")
    parser.add_argument("--session")
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()

    store = LongTermMemoryStore(args.memory_dir, filename=args.filename)
    if args.command == "list":
        records = store.all_records()
    else:
        records = store.query(args.q, session_id=args.session, limit=args.limit)
    print(json.dumps(records, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
