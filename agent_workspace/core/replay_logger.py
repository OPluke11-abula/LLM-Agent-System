import os
import sqlite3
import json
import logging
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional, Dict

logger = logging.getLogger("ReplayLogger")

class ReplayLogger:
    """
    Thread-safe SQLite-backed session replay registry logging chronological 
    WebSocket telemetry updates for each active crew session.
    """
    _lock = threading.Lock()

    @classmethod
    def _get_db_conn(cls, db_path: Path) -> sqlite3.Connection:
        conn = sqlite3.connect(str(db_path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        return conn

    @classmethod
    def _init_db(cls, db_path: Path) -> None:
        conn = cls._get_db_conn(db_path)
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS replay_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    payload TEXT NOT NULL
                )
                """
            )
            conn.commit()
        finally:
            conn.close()

    @classmethod
    def log_event(cls, workspace_path: str, session_id: str, event_type: str, payload: dict) -> None:
        """Logs a session telemetry event chronologically to a session-specific SQLite database."""
        if not session_id:
            return
            
        replays_dir = Path(workspace_path) / "memory" / "replays"
        with cls._lock:
            try:
                replays_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                logger.error(f"Failed to create replays directory: {e}")
                return

        db_path = replays_dir / f"{session_id}.db"
        
        # Initialize database tables
        cls._init_db(db_path)

        timestamp = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        payload_str = json.dumps(payload, ensure_ascii=False)

        with cls._lock:
            conn = cls._get_db_conn(db_path)
            try:
                conn.execute(
                    "INSERT INTO replay_events (timestamp, event_type, payload) VALUES (?, ?, ?)",
                    (timestamp, event_type, payload_str)
                )
                conn.commit()
            except Exception as e:
                logger.error(f"Failed to insert event for session {session_id}: {e}")
            finally:
                conn.close()

    @classmethod
    def get_session_timeline(cls, workspace_path: str, session_id: str) -> Optional[List[Dict[str, Any]]]:
        """Retrieves the chronological sequence of state changes for the given session ID."""
        if not session_id:
            return None
            
        replays_dir = Path(workspace_path) / "memory" / "replays"
        db_path = replays_dir / f"{session_id}.db"
        
        if not db_path.exists():
            return None

        timeline = []
        with cls._lock:
            conn = cls._get_db_conn(db_path)
            try:
                cursor = conn.execute("SELECT timestamp, event_type, payload FROM replay_events ORDER BY id ASC")
                for row in cursor.fetchall():
                    try:
                        payload = json.loads(row["payload"])
                    except Exception:
                        payload = {"raw": row["payload"]}
                    timeline.append({
                        "timestamp": row["timestamp"],
                        "event_type": row["event_type"],
                        "payload": payload
                    })
            except Exception as e:
                logger.error(f"Failed to query replay events for session {session_id}: {e}")
                return None
            finally:
                conn.close()
                
        return timeline

    @classmethod
    def clean_replays(cls, workspace_path: str, ttl_days: int) -> int:
        """Purges historical session replays older than a configurable TTL (in days)."""
        replays_dir = Path(workspace_path) / "memory" / "replays"
        if not replays_dir.exists():
            return 0

        threshold_time = time.time() - (ttl_days * 24 * 3600)
        deleted_count = 0

        with cls._lock:
            for file_path in replays_dir.glob("*.db"):
                try:
                    mtime = file_path.stat().st_mtime
                    if mtime < threshold_time:
                        file_path.unlink()
                        deleted_count += 1
                        logger.info(f"Purged stale replay database file: {file_path.name}")
                except Exception as e:
                    logger.error(f"Failed to purge replay file {file_path}: {e}")

        return deleted_count
