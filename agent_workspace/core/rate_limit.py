from __future__ import annotations

import asyncio
import sqlite3
import time
from pathlib import Path


class RateLimitStateUnavailable(RuntimeError):
    pass


class TenantRequestRateLimiter:
    def __init__(self, db_path: str | Path, *, limit: int = 10, window_seconds: float = 10.0):
        if limit <= 0 or window_seconds <= 0:
            raise ValueError("limit and window_seconds must be positive")
        self.db_path = Path(db_path)
        self.limit = limit
        self.window_seconds = window_seconds

    def _consume(self, tenant_id: str) -> bool:
        if not tenant_id or not isinstance(tenant_id, str):
            raise ValueError("tenant_id is required")
        now = time.time()
        cutoff = now - self.window_seconds
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(str(self.db_path), timeout=5.0) as conn:
                conn.execute("PRAGMA busy_timeout = 5000")
                conn.execute("BEGIN IMMEDIATE")
                conn.execute(
                    "CREATE TABLE IF NOT EXISTS tenant_request_rate ("
                    "tenant_id TEXT NOT NULL, requested_at REAL NOT NULL)"
                )
                conn.execute("DELETE FROM tenant_request_rate WHERE requested_at < ?", (cutoff,))
                count = conn.execute(
                    "SELECT COUNT(*) FROM tenant_request_rate WHERE tenant_id = ? AND requested_at >= ?",
                    (tenant_id, cutoff),
                ).fetchone()[0]
                if count >= self.limit:
                    conn.commit()
                    return True
                conn.execute(
                    "INSERT INTO tenant_request_rate (tenant_id, requested_at) VALUES (?, ?)",
                    (tenant_id, now),
                )
                conn.commit()
                return False
        except (sqlite3.Error, OSError) as exc:
            raise RateLimitStateUnavailable("shared tenant rate-limit state is unavailable") from exc

    async def is_rate_limited(self, tenant_id: str) -> bool:
        return await asyncio.to_thread(self._consume, tenant_id)
