"""Working memory management for agent router sessions."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

from agent_workspace.core.security import safe_workspace_path, validate_session_id


class MemoryManager:
    """Manage per-session working memory files."""

    def __init__(self, memory_dir: str, session_id: str = "default") -> None:
        self.session_id = validate_session_id(session_id)
        self.memory_path = str(safe_workspace_path(memory_dir, f"{self.session_id}.json"))
        self._ensure_file_exists()

    def _ensure_file_exists(self) -> None:
        os.makedirs(os.path.dirname(self.memory_path), exist_ok=True)
        if not os.path.isfile(self.memory_path):
            self._write({})

    def load(self) -> dict[str, Any]:
        try:
            with open(self.memory_path, "r", encoding="utf-8") as file:
                return json.load(file)
        except (json.JSONDecodeError, OSError, IOError):
            return {}

    def save(self, data: dict[str, Any]) -> None:
        self._write(data)

    def append_conversation(self, user_input: str, assistant_response: str) -> bool:
        """Append one exchange and return True when the retention window rolled."""
        memory = self.load()
        memory.setdefault("conversations", [])
        memory["conversations"].append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user": user_input,
                "assistant": assistant_response,
            }
        )

        limit_reached = False
        if len(memory["conversations"]) > 20:
            memory["conversations"] = memory["conversations"][-20:]
            limit_reached = True

        self.save(memory)
        return limit_reached

    def get_recent_context(self, n: int = 5) -> list[dict[str, Any]]:
        memory = self.load()
        conversations = memory.get("conversations", [])
        return conversations[-n:]

    def _write(self, data: dict[str, Any]) -> None:
        with open(self.memory_path, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
