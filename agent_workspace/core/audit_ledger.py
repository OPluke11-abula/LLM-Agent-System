import os
import sqlite3
import json
import hashlib
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("AuditLedger")

class AuditLedger:
    """
    Cryptographically chained, immutable SQLite-based audit trail
    implementing SOC2 security audit trail capabilities.
    """
    _initialized_dbs = set()

    def __init__(self, workspace_path: str):
        self.workspace_path = os.path.abspath(workspace_path)
        self.db_dir = Path(self.workspace_path) / "memory"
        self.db_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.db_dir / "audit_ledger.db"
        self._lock = threading.Lock()
        
        db_path_str = str(self.db_path)
        if db_path_str not in AuditLedger._initialized_dbs:
            self._init_db()
            AuditLedger._initialized_dbs.add(db_path_str)

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
                    CREATE TABLE IF NOT EXISTS audit_ledger (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        event_type TEXT NOT NULL,
                        payload TEXT NOT NULL,
                        previous_hash TEXT NOT NULL,
                        current_hash TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        tenant_id TEXT DEFAULT 'default_tenant'
                    )
                    """
                )
                conn.commit()
                # Run dynamic migration check for existing tables without tenant_id column
                try:
                    conn.execute("ALTER TABLE audit_ledger ADD COLUMN tenant_id TEXT DEFAULT 'default_tenant'")
                    conn.commit()
                except sqlite3.OperationalError:
                    pass
            finally:
                conn.close()

    def record_event(self, event_type: str, payload: Dict[str, Any], tenant_id: str = "default_tenant") -> int:
        """Records an audited event, cryptographically chaining it to the previous record."""
        payload_str = json.dumps(payload, sort_keys=True)
        timestamp = datetime.now(timezone.utc).isoformat()

        with self._lock:
            conn = self._get_conn()
            try:
                # 1. Fetch previous hash
                cursor = conn.execute("SELECT current_hash FROM audit_ledger ORDER BY id DESC LIMIT 1")
                row = cursor.fetchone()
                previous_hash = row["current_hash"] if row else "0" * 64

                # 2. Calculate current hash
                hash_input = f"{previous_hash}{payload_str}{timestamp}"
                current_hash = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()

                # 3. Insert record
                cursor = conn.execute(
                    """
                    INSERT INTO audit_ledger (event_type, payload, previous_hash, current_hash, timestamp, tenant_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (event_type, payload_str, previous_hash, current_hash, timestamp, tenant_id)
                )
                conn.commit()
                row_id = cursor.lastrowid or 0
                logger.debug(f"[AuditLedger] Recorded event ID {row_id}: type '{event_type}', hash {current_hash[:8]}")
                return row_id
            finally:
                conn.close()

    def verify_chain_integrity(self) -> Dict[str, Any]:
        """
        Validates the complete log chain integrity.
        Returns validation status and the exact log ID of any tampered record.
        """
        with self._lock:
            conn = self._get_conn()
            try:
                cursor = conn.execute("SELECT * FROM audit_ledger ORDER BY id ASC")
                rows = cursor.fetchall()
            finally:
                conn.close()

        expected_previous_hash = "0" * 64
        for row in rows:
            row_id = row["id"]
            stored_previous_hash = row["previous_hash"]
            stored_current_hash = row["current_hash"]
            stored_payload_str = row["payload"]
            stored_timestamp = row["timestamp"]

            # 1. Assert previous hash match
            if stored_previous_hash != expected_previous_hash:
                logger.error(f"[AuditLedger] Chain broken at ID {row_id}: previous_hash mismatch.")
                return {"valid": False, "tampered_id": row_id, "error": "previous_hash mismatch"}

            # 2. Re-compute and assert current hash
            # Reconstruct payload sorting keys to ensure deterministic serialization
            try:
                payload = json.loads(stored_payload_str)
                payload_str = json.dumps(payload, sort_keys=True)
            except Exception:
                # If JSON parsing fails, fall back to the raw stored string
                payload_str = stored_payload_str

            recalculated_hash_input = f"{stored_previous_hash}{payload_str}{stored_timestamp}"
            recalculated_hash = hashlib.sha256(recalculated_hash_input.encode("utf-8")).hexdigest()

            if stored_current_hash != recalculated_hash:
                logger.error(f"[AuditLedger] Hash verification failed at ID {row_id}: content hash mismatch.")
                return {"valid": False, "tampered_id": row_id, "error": "current_hash mismatch"}

            expected_previous_hash = stored_current_hash

        return {"valid": True, "tampered_id": None}

    def get_logs(self, event_type: Optional[str] = None, tenant_id: str = "default_tenant") -> List[Dict[str, Any]]:
        """Queries log entries, optionally filtered by event_type, isolated by tenant."""
        with self._lock:
            conn = self._get_conn()
            try:
                if event_type:
                    cursor = conn.execute(
                        "SELECT * FROM audit_ledger WHERE tenant_id = ? AND event_type = ? ORDER BY id ASC",
                        (tenant_id, event_type)
                    )
                else:
                    cursor = conn.execute("SELECT * FROM audit_ledger WHERE tenant_id = ? ORDER BY id ASC", (tenant_id,))
                records = []
                for row in cursor.fetchall():
                    rec = dict(row)
                    try:
                        rec["payload"] = json.loads(rec["payload"])
                    except Exception:
                        pass
                    records.append(rec)
                return records
            finally:
                conn.close()

    def reset_ledger(self) -> None:
        """Truncates the ledger database records."""
        with self._lock:
            conn = self._get_conn()
            try:
                conn.execute("DELETE FROM audit_ledger")
                conn.commit()
                logger.info("[AuditLedger] Audit ledger cleared successfully.")
            finally:
                conn.close()
