import os
import sqlite3
import json
import hashlib
import logging
import threading
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from core.merkle import MerkleTree
except ImportError:
    from agent_workspace.core.merkle import MerkleTree

try:
    from core.broker import get_broker, RedisSwarmBroker
except ImportError:
    from agent_workspace.core.broker import get_broker, RedisSwarmBroker

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
        current_hashes = []
        for row in rows:
            row_id = row["id"]
            stored_previous_hash = row["previous_hash"]
            stored_current_hash = row["current_hash"]
            stored_payload_str = row["payload"]
            stored_timestamp = row["timestamp"]

            # 1. Assert previous hash match
            if stored_previous_hash != expected_previous_hash:
                logger.error(f"[AuditLedger] Chain broken at ID {row_id}: previous_hash mismatch.")
                return {"valid": False, "tampered_id": row_id, "error": "previous_hash mismatch", "merkle_root": "0" * 64}

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
                return {"valid": False, "tampered_id": row_id, "error": "current_hash mismatch", "merkle_root": "0" * 64}

            expected_previous_hash = stored_current_hash
            current_hashes.append(stored_current_hash)

        merkle_root = MerkleTree(current_hashes).root
        return {"valid": True, "tampered_id": None, "merkle_root": merkle_root}

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

    def get_logs_after(self, after_id: int) -> List[Dict[str, Any]]:
        """Queries local ledger logs where ID > after_id."""
        with self._lock:
            conn = self._get_conn()
            try:
                cursor = conn.execute("SELECT * FROM audit_ledger WHERE id > ? ORDER BY id ASC", (after_id,))
                records = []
                for row in cursor.fetchall():
                    rec = dict(row)
                    records.append(rec)
                return records
            finally:
                conn.close()

    def insert_raw_event(self, id: int, event_type: str, payload_str: str, previous_hash: str, current_hash: str, timestamp: str, tenant_id: str) -> None:
        """Restores a raw event, manually specifying the ID and hashes to self-heal replicas."""
        with self._lock:
            conn = self._get_conn()
            try:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO audit_ledger (id, event_type, payload, previous_hash, current_hash, timestamp, tenant_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (id, event_type, payload_str, previous_hash, current_hash, timestamp, tenant_id)
                )
                conn.commit()
            finally:
                conn.close()

    def generate_merkle_proof(self, event_id: int) -> Optional[Dict[str, Any]]:
        """
        Generates a Merkle Proof for a specific event ID.
        Returns a dictionary containing the merkle proof (list of sibling hashes and positions),
        the root hash, and the event's current_hash.
        """
        with self._lock:
            conn = self._get_conn()
            try:
                cursor = conn.execute("SELECT id, current_hash FROM audit_ledger ORDER BY id ASC")
                rows = cursor.fetchall()
            finally:
                conn.close()

        if not rows:
            return None

        event_hashes = [row["current_hash"] for row in rows]
        event_ids = [row["id"] for row in rows]

        if event_id not in event_ids:
            return None

        target_idx = event_ids.index(event_id)
        target_hash = event_hashes[target_idx]

        # Build tree levels
        levels = []
        current_level = [hashlib.sha256(h.encode("utf-8")).hexdigest() for h in event_hashes]
        levels.append(current_level)

        while len(current_level) > 1:
            next_level = []
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                right = current_level[i + 1] if i + 1 < len(current_level) else left
                combined = left + right
                parent_hash = hashlib.sha256(combined.encode("utf-8")).hexdigest()
                next_level.append(parent_hash)
            current_level = next_level
            levels.append(current_level)

        root_hash = current_level[0] if current_level else "0" * 64

        # Generate proof path
        proof = []
        idx = target_idx
        for level in levels[:-1]:
            if idx % 2 == 0:
                sibling_idx = idx + 1
                if sibling_idx < len(level):
                    sibling_hash = level[sibling_idx]
                else:
                    sibling_hash = level[idx]
                position = "right"
            else:
                sibling_idx = idx - 1
                sibling_hash = level[sibling_idx]
                position = "left"
            
            proof.append({"hash": sibling_hash, "position": position})
            idx = idx // 2

        return {
            "proof": proof,
            "root_hash": root_hash,
            "event_hash": target_hash
        }

    @classmethod
    def verify_merkle_proof(cls, event_hash: str, proof: list, root_hash: str) -> bool:
        """
        Verifies a Merkle Proof for a given event hash against the root hash.
        """
        if not event_hash or not root_hash:
            return False
            
        current = hashlib.sha256(event_hash.encode("utf-8")).hexdigest()
        for step in proof:
            sibling = step.get("hash")
            position = step.get("position")
            if not sibling or not position:
                return False
                
            if position == "left":
                combined = sibling + current
            else:
                combined = current + sibling
            current = hashlib.sha256(combined.encode("utf-8")).hexdigest()
            
        return current == root_hash

    def generate_zk_proof(self, event_id: int) -> Optional[Dict[str, Any]]:
        """
        Generates a simulated ZK Proof for a specific event ID.
        """
        with self._lock:
            conn = self._get_conn()
            try:
                cursor = conn.execute("SELECT event_type, timestamp, previous_hash, current_hash, payload FROM audit_ledger WHERE id = ?", (event_id,))
                row = cursor.fetchone()
            finally:
                conn.close()

        if not row:
            return None

        event_type = row["event_type"]
        timestamp = row["timestamp"]
        previous_hash = row["previous_hash"]
        current_hash = row["current_hash"]
        payload_str = row["payload"]

        # Create a commitment of the payload (blinding it)
        import secrets
        salt = secrets.token_hex(16)
        payload_commitment = hashlib.sha256((payload_str + salt).encode("utf-8")).hexdigest()

        # Secret key for ZK proof simulation
        ZK_SECRET_KEY = b"zk_audit_chain_secret_key_findai_studio"
        message = f"{event_type}:{timestamp}:{previous_hash}:{current_hash}:{payload_commitment}"
        import hmac
        signature = hmac.new(ZK_SECRET_KEY, message.encode("utf-8"), hashlib.sha256).hexdigest()

        return {
            "proof": signature,
            "payload_commitment": payload_commitment,
            "salt": salt,
            "event_type": event_type,
            "timestamp": timestamp,
            "previous_hash": previous_hash,
            "current_hash": current_hash
        }

    @classmethod
    def verify_zk_proof(cls, event_type: str, timestamp: str, previous_hash: str, current_hash: str, proof_pkg: dict) -> bool:
        """
        Verifies a simulated ZK Proof.
        """
        payload_commitment = proof_pkg.get("payload_commitment")
        signature = proof_pkg.get("proof")
        if not payload_commitment or not signature:
            return False

        ZK_SECRET_KEY = b"zk_audit_chain_secret_key_findai_studio"
        message = f"{event_type}:{timestamp}:{previous_hash}:{current_hash}:{payload_commitment}"
        import hmac
        expected_signature = hmac.new(ZK_SECRET_KEY, message.encode("utf-8"), hashlib.sha256).hexdigest()

        return hmac.compare_digest(signature, expected_signature)


class AuditConsensusDaemon:
    """
    Background consensus daemon orchestrating cross-node audit log replication
    and self-healing state verification over Redis.
    """
    def __init__(self, ledger: AuditLedger, node_id: str, sync_interval: float = 5.0):
        self.ledger = ledger
        self.node_id = node_id
        self.sync_interval = sync_interval
        self.peer_states: Dict[str, Dict[str, Any]] = {}
        self._is_running = False
        self._broadcast_task: Optional[asyncio.Task] = None
        self._pending_requests: set[str] = set()

    async def start(self) -> None:
        if self._is_running:
            return
        self._is_running = True
        
        broker = get_broker()
        # 1. Subscribe to pub/sub channels
        await broker.subscribe("audit:sync:check", self._on_ping)
        await broker.subscribe("audit:sync:request", self._on_request)
        await broker.subscribe(f"audit:sync:response:{self.node_id}", self._on_response)
        
        # 2. Launch broadcast loop
        self._broadcast_task = asyncio.create_task(self._broadcast_loop())
        logger.info(f"AuditConsensusDaemon started for node '{self.node_id}'")

    async def stop(self) -> None:
        self._is_running = False
        if self._broadcast_task:
            self._broadcast_task.cancel()
            try:
                await self._broadcast_task
            except asyncio.CancelledError:
                pass
            self._broadcast_task = None
            
        broker = get_broker()
        await broker.unsubscribe("audit:sync:check")
        await broker.unsubscribe("audit:sync:request")
        await broker.unsubscribe(f"audit:sync:response:{self.node_id}")
        logger.info(f"AuditConsensusDaemon stopped for node '{self.node_id}'")

    async def _broadcast_loop(self) -> None:
        while self._is_running:
            try:
                await self.broadcast_status()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in consensus daemon broadcast: {e}")
            await asyncio.sleep(self.sync_interval)

    async def broadcast_status(self) -> None:
        status = self.ledger.verify_chain_integrity()
        local_root = status.get("merkle_root", "0" * 64)
        logs = self.ledger.get_logs()
        local_count = len(logs)

        msg = {
            "type": "sync_ping",
            "node_id": self.node_id,
            "merkle_root": local_root,
            "event_count": local_count
        }
        broker = get_broker()
        await broker.publish("audit:sync:check", msg)

    async def trigger_manual_sync(self) -> None:
        """Triggers a manual consensus audit by querying all peer nodes."""
        broker = get_broker()
        # 1. Ask peers to broadcast their status immediately
        await broker.publish("audit:sync:check", {"type": "sync_query", "sender_id": self.node_id})
        # 2. Broadcast own status
        await self.broadcast_status()

    async def _on_ping(self, msg: dict) -> None:
        await self.process_ping(msg)

    async def _on_request(self, msg: dict) -> None:
        await self.process_request(msg)

    async def _on_response(self, msg: dict) -> None:
        await self.process_response(msg)

    async def process_ping(self, msg: dict) -> None:
        msg_type = msg.get("type")
        if msg_type == "sync_query":
            # Immediately report status
            await self.broadcast_status()
        elif msg_type == "sync_ping":
            peer_id = msg.get("node_id")
            if not peer_id or peer_id == self.node_id:
                return

            peer_root = msg.get("merkle_root")
            peer_count = msg.get("event_count")
            
            # Determine status
            status = self.ledger.verify_chain_integrity()
            local_root = status.get("merkle_root", "0" * 64)
            local_count = len(self.ledger.get_logs())

            if peer_count == local_count and peer_root == local_root:
                peer_status = "synchronized"
            elif local_count < peer_count:
                peer_status = "peer_ahead"
            else:
                peer_status = "local_ahead"

            self.peer_states[peer_id] = {
                "last_seen": datetime.now(timezone.utc).isoformat(),
                "event_count": peer_count,
                "merkle_root": peer_root,
                "status": peer_status
            }

            # If peer is ahead, request missing logs
            if local_count < peer_count:
                # Avoid redundant concurrent requests for the same peer range
                req_key = f"{peer_id}:{local_count}"
                if req_key not in self._pending_requests:
                    self._pending_requests.add(req_key)
                    req_msg = {
                        "type": "logs_request",
                        "requester_id": self.node_id,
                        "provider_id": peer_id,
                        "after_id": local_count
                    }
                    broker = get_broker()
                    await broker.publish("audit:sync:request", req_msg)
            
            # Mismatch at same event count indicating unresolvable fork or tampering
            elif peer_count == local_count and peer_root != local_root:
                logger.error(f"[Consensus] Unresolvable fork / tampering detected between '{self.node_id}' and '{peer_id}'!")
                self.ledger.record_event(
                    event_type="SOC2_VIOLATION",
                    payload={
                        "error": "Merkle root mismatch with equal event count / unresolvable fork detected",
                        "peer_node_id": peer_id,
                        "local_root": local_root,
                        "peer_root": peer_root,
                        "event_count": local_count
                    }
                )

    async def process_request(self, msg: dict) -> None:
        if msg.get("type") != "logs_request":
            return
        
        provider_id = msg.get("provider_id")
        if provider_id != self.node_id:
            return

        requester_id = msg.get("requester_id")
        after_id = msg.get("after_id", 0)
        
        # Fetch logs after after_id
        logs = self.ledger.get_logs_after(after_id)
        
        resp = {
            "type": "logs_response",
            "provider_id": self.node_id,
            "logs": logs
        }
        broker = get_broker()
        await broker.publish(f"audit:sync:response:{requester_id}", resp)

    async def process_response(self, msg: dict) -> None:
        if msg.get("type") != "logs_response":
            return

        provider_id = msg.get("provider_id")
        incoming_logs = msg.get("logs", [])
        if not incoming_logs:
            return

        # Verification of incoming logs
        # 1. Fetch current local state
        local_logs = self.ledger.get_logs()
        local_count = len(local_logs)
        last_hash = local_logs[-1]["current_hash"] if local_logs else "0" * 64

        # Validate incoming logs link correctly to last local hash and chain internally
        expected_prev_hash = last_hash
        verification_failed = False
        
        for log in incoming_logs:
            log_id = log.get("id")
            event_type = log.get("event_type")
            stored_payload_str = log.get("payload")
            stored_prev_hash = log.get("previous_hash")
            stored_curr_hash = log.get("current_hash")
            stored_timestamp = log.get("timestamp")
            
            # Check linking
            if stored_prev_hash != expected_prev_hash:
                logger.error(f"[Consensus] Verification failure: log ID {log_id} previous_hash mismatch.")
                verification_failed = True
                break
                
            # Check content hash
            try:
                payload = json.loads(stored_payload_str)
                payload_str = json.dumps(payload, sort_keys=True)
            except Exception:
                payload_str = stored_payload_str

            hash_input = f"{stored_prev_hash}{payload_str}{stored_timestamp}"
            computed_hash = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()
            if computed_hash != stored_curr_hash:
                logger.error(f"[Consensus] Verification failure: log ID {log_id} content hash mismatch.")
                verification_failed = True
                break
                
            expected_prev_hash = stored_curr_hash

        if verification_failed:
            logger.error(f"[Consensus] Replicated logs from '{provider_id}' failed verification! Rejecting.")
            self.ledger.record_event(
                event_type="SOC2_VIOLATION",
                payload={
                    "error": "Replicated logs failed cryptographic verification",
                    "provider_node_id": provider_id,
                    "first_incoming_id": incoming_logs[0].get("id") if incoming_logs else None
                }
            )
            return

        # Self-heal replica: insert all verified logs
        for log in incoming_logs:
            self.ledger.insert_raw_event(
                id=log["id"],
                event_type=log["event_type"],
                payload_str=log["payload"],
                previous_hash=log["previous_hash"],
                current_hash=log["current_hash"],
                timestamp=log["timestamp"],
                tenant_id=log.get("tenant_id", "default_tenant")
            )

        # Clear pending request entry
        req_key = f"{provider_id}:{local_count}"
        self._pending_requests.discard(req_key)

        logger.info(f"[Consensus] Self-healed replica successfully with {len(incoming_logs)} logs from '{provider_id}'")
        # Record self-healing event
        self.ledger.record_event(
            event_type="CONSENSUS_RECOVERY",
            payload={
                "message": "Self-healing replication completed successfully",
                "logs_restored": len(incoming_logs),
                "provider_node_id": provider_id
            }
        )
