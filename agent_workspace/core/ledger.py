import os
import sqlite3
import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

class FinancialLedger:
    """Persistent, SQLite-based dynamic token financial ledger tracking API expenses."""

    def __init__(self, workspace_path: str):
        self.workspace_path = os.path.abspath(workspace_path)
        self.db_dir = Path(self.workspace_path) / "memory"
        self.db_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.db_dir / "financial_ledger.db"
        self._lock = threading.Lock()
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._lock:
            conn = self._get_conn()
            try:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS financial_ledger (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        account_id TEXT NOT NULL,
                        provider TEXT NOT NULL,
                        model TEXT NOT NULL,
                        prompt_tokens INTEGER NOT NULL,
                        completion_tokens INTEGER NOT NULL,
                        total_tokens INTEGER NOT NULL,
                        cost REAL NOT NULL,
                        timestamp TEXT NOT NULL
                    )
                    """
                )
                conn.commit()
            finally:
                conn.close()

    def estimate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        """Estimates the API cost based on token consumption and model tier."""
        m_lower = model.lower()
        if "pro" in m_lower:
            # $15 per M prompt tokens, $45 per M completion tokens
            return (prompt_tokens * 0.000015) + (completion_tokens * 0.000045)
        elif "claude-3-5" in m_lower:
            return (prompt_tokens * 0.000003) + (completion_tokens * 0.000015)
        elif "flash" in m_lower:
            # $0.075 per M prompt tokens, $0.30 per M completion tokens
            return (prompt_tokens * 0.000000075) + (completion_tokens * 0.0000003)
        else:
            # Default mid-tier pricing
            return (prompt_tokens * 0.000002) + (completion_tokens * 0.000008)

    def record_transaction(
        self,
        session_id: str,
        account_id: str,
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int
    ) -> float:
        """Records a token usage transaction to the financial ledger SQLite database."""
        total_tokens = prompt_tokens + completion_tokens
        cost = self.estimate_cost(model, prompt_tokens, completion_tokens)
        now = datetime.now(timezone.utc).isoformat()

        with self._lock:
            conn = self._get_conn()
            try:
                conn.execute(
                    """
                    INSERT INTO financial_ledger (
                        session_id, account_id, provider, model, prompt_tokens, completion_tokens, total_tokens, cost, timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (session_id, account_id, provider, model, prompt_tokens, completion_tokens, total_tokens, cost, now)
                )
                conn.commit()
                logger.info("[CFO Ledger Log] Session: %s, Cost: $%0.6f added.", session_id, cost)
            finally:
                conn.close()
        return cost

    def get_total_cost(self, filter_id: str | None = None) -> float:
        """Calculates total cost across all sessions or filtered by session/account."""
        with self._lock:
            conn = self._get_conn()
            try:
                if filter_id:
                    cursor = conn.execute(
                        "SELECT SUM(cost) FROM financial_ledger WHERE session_id = ? OR account_id = ?",
                        (filter_id, filter_id)
                    )
                else:
                    cursor = conn.execute("SELECT SUM(cost) FROM financial_ledger")
                row = cursor.fetchone()
                total = row[0] if row and row[0] is not None else 0.0
            finally:
                conn.close()
        return float(total)

    def get_all_records(self) -> list[dict[str, Any]]:
        """Returns all ledger transaction entries."""
        with self._lock:
            conn = self._get_conn()
            try:
                cursor = conn.execute("SELECT * FROM financial_ledger ORDER BY timestamp ASC")
                records = [dict(row) for row in cursor.fetchall()]
            finally:
                conn.close()
        return records

    def reset_ledger(self) -> None:
        """Truncates the ledger database records."""
        with self._lock:
            conn = self._get_conn()
            try:
                conn.execute("DELETE FROM financial_ledger")
                conn.commit()
                logger.info("[CFO Ledger Log] Financial ledger cleared successfully.")
            finally:
                conn.close()
