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
                        timestamp TEXT NOT NULL,
                        tenant_id TEXT DEFAULT 'default_tenant',
                        markup_multiplier REAL DEFAULT 1.5
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS stripe_sync_metadata (
                        tenant_id TEXT PRIMARY KEY,
                        last_synced_id INTEGER DEFAULT 0
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS tenant_subscription_status (
                        tenant_id TEXT PRIMARY KEY,
                        status TEXT NOT NULL,
                        stripe_customer_id TEXT,
                        stripe_subscription_id TEXT,
                        last_updated TEXT NOT NULL
                    )
                    """
                )
                conn.commit()
                # Run dynamic migration check for existing tables without tenant_id/markup_multiplier column
                try:
                    conn.execute("ALTER TABLE financial_ledger ADD COLUMN tenant_id TEXT DEFAULT 'default_tenant'")
                    conn.commit()
                except sqlite3.OperationalError:
                    pass

                try:
                    conn.execute("ALTER TABLE financial_ledger ADD COLUMN markup_multiplier REAL DEFAULT 1.5")
                    conn.commit()
                except sqlite3.OperationalError:
                    pass
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
        completion_tokens: int,
        tenant_id: str = "default_tenant",
        markup_multiplier: float | None = None
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
                        session_id, account_id, provider, model, prompt_tokens, completion_tokens, total_tokens, cost, timestamp, tenant_id, markup_multiplier
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (session_id, account_id, provider, model, prompt_tokens, completion_tokens, total_tokens, cost, now, tenant_id, markup_multiplier)
                )
                conn.commit()
                logger.info("[CFO Ledger Log] Session: %s, Cost: $%0.6f added.", session_id, cost)
            finally:
                conn.close()

        # Increment Prometheus tenant tokens
        try:
            try:
                from observability import PROMETHEUS_AVAILABLE, _get_or_create_metric
            except ImportError:
                from agent_workspace.observability import PROMETHEUS_AVAILABLE, _get_or_create_metric
            if PROMETHEUS_AVAILABLE:
                from prometheus_client import Counter
                tenant_tokens = _get_or_create_metric(Counter, "las_tenant_tokens_total", "Total tokens consumed by tenant", ["tenant_id", "token_type"])
                tenant_tokens.labels(tenant_id=tenant_id, token_type="prompt").inc(prompt_tokens)
                tenant_tokens.labels(tenant_id=tenant_id, token_type="completion").inc(completion_tokens)
                tenant_tokens.labels(tenant_id=tenant_id, token_type="total").inc(total_tokens)
        except Exception as e:
            logger.warning(f"Failed to record Prometheus tenant token metric: {e}")

        return cost

    def get_total_cost(self, filter_id: str | None = None, tenant_id: str = "default_tenant") -> float:
        """Calculates total cost across all sessions or filtered by session/account, isolated by tenant."""
        with self._lock:
            conn = self._get_conn()
            try:
                if filter_id:
                    cursor = conn.execute(
                        "SELECT SUM(cost) FROM financial_ledger WHERE tenant_id = ? AND (session_id = ? OR account_id = ?)",
                        (tenant_id, filter_id, filter_id)
                    )
                else:
                    cursor = conn.execute("SELECT SUM(cost) FROM financial_ledger WHERE tenant_id = ?", (tenant_id,))
                row = cursor.fetchone()
                total = row[0] if row and row[0] is not None else 0.0
            finally:
                conn.close()
        return float(total)

    def get_all_records(self, tenant_id: str = "default_tenant") -> list[dict[str, Any]]:
        """Returns all ledger transaction entries matching tenant_id."""
        with self._lock:
            conn = self._get_conn()
            try:
                cursor = conn.execute("SELECT * FROM financial_ledger WHERE tenant_id = ? ORDER BY timestamp ASC", (tenant_id,))
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
