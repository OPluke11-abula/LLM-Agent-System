import os
import sys
import json
import pytest
import asyncio
import tempfile
import shutil
import hashlib
import inspect
from unittest.mock import AsyncMock, MagicMock, patch

# Ensure agent_workspace is in sys.path
workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)

from core.merkle import MerkleTree
from core.audit_ledger import AuditLedger, AuditConsensusDaemon
from core.broker import RedisSwarmBroker
from fastapi.testclient import TestClient
import api


# Synchronous mock broker to prevent multi-loop deadlocks in testing
class MockSyncBroker(RedisSwarmBroker):
    def __init__(self):
        self.subscribers = {}

    async def start(self):
        pass

    async def stop(self):
        pass

    async def publish(self, channel, message):
        if channel in self.subscribers:
            for cb in list(self.subscribers[channel]):
                if inspect.iscoroutinefunction(cb):
                    await cb(message)
                else:
                    cb(message)

    async def subscribe(self, channel, callback):
        if channel not in self.subscribers:
            self.subscribers[channel] = []
        self.subscribers[channel].append(callback)

    async def unsubscribe(self, channel):
        self.subscribers.pop(channel, None)


def test_merkle_tree_computation():
    """Verify Merkle Tree root calculation is deterministic, handles odd and empty inputs."""
    # 1. Empty input
    tree_empty = MerkleTree([])
    assert tree_empty.root == "0" * 64

    # 2. Single leaf
    leaf = "a" * 64
    expected_root = hashlib.sha256(leaf.encode()).hexdigest()
    tree_single = MerkleTree([leaf])
    assert tree_single.root == expected_root

    # 3. Odd leaves (e.g. 3 leaves)
    leaves_3 = ["a"*64, "b"*64, "c"*64]
    # Level 0: [H(a), H(b), H(c)]
    # Level 1: [H(H(a)+H(b)), H(H(c)+H(c))]
    # Root: H( Level1[0] + Level1[1] )
    h_a = hashlib.sha256(leaves_3[0].encode()).hexdigest()
    h_b = hashlib.sha256(leaves_3[1].encode()).hexdigest()
    h_c = hashlib.sha256(leaves_3[2].encode()).hexdigest()

    h_ab = hashlib.sha256((h_a + h_b).encode()).hexdigest()
    h_cc = hashlib.sha256((h_c + h_c).encode()).hexdigest()
    h_root = hashlib.sha256((h_ab + h_cc).encode()).hexdigest()

    tree_3 = MerkleTree(leaves_3)
    assert tree_3.root == h_root


def test_verify_chain_integrity_merkle_root():
    """Verify that verify_chain_integrity computes and includes the Merkle Root."""
    temp_dir = tempfile.mkdtemp()
    try:
        ledger = AuditLedger(temp_dir)
        # Empty chain
        res_empty = ledger.verify_chain_integrity()
        assert res_empty["valid"] is True
        assert res_empty["merkle_root"] == "0" * 64

        # Add events
        ledger.record_event("TEST_EVENT_1", {"msg": "hello"})
        ledger.record_event("TEST_EVENT_2", {"msg": "world"})

        res_2 = ledger.verify_chain_integrity()
        assert res_2["valid"] is True
        assert res_2["merkle_root"] != "0" * 64

        # Verify against manual calculation
        logs = ledger.get_logs()
        hashes = [log["current_hash"] for log in logs]
        tree = MerkleTree(hashes)
        assert res_2["merkle_root"] == tree.root
    finally:
        shutil.rmtree(temp_dir)


@pytest.mark.asyncio
async def test_daemon_consensus_and_self_healing():
    """Verify that a lagging peer node correctly requests, verifies, and self-heals its chain."""
    dir_node1 = tempfile.mkdtemp()
    dir_node2 = tempfile.mkdtemp()
    
    broker = MockSyncBroker()
    
    # Inject our mock broker inside sys.modules to avoid double import path issues
    import sys
    old_brokers = {}
    for name, module in list(sys.modules.items()):
        if name.endswith("core.broker"):
            old_brokers[name] = getattr(module, "_global_broker", None)
            module._global_broker = broker

    try:
        ledger1 = AuditLedger(dir_node1)
        ledger2 = AuditLedger(dir_node2)

        # 1. Populate Node 1 with 3 events
        ev1 = ledger1.record_event("EVENT_A", {"data": 1})
        ev2 = ledger1.record_event("EVENT_B", {"data": 2})
        ev3 = ledger1.record_event("EVENT_C", {"data": 3})

        # 2. Populate Node 2 with ONLY the first event (perfect match to Node 1's first event)
        logs1 = ledger1.get_logs()
        first_log = logs1[0]
        ledger2.insert_raw_event(
            id=first_log["id"],
            event_type=first_log["event_type"],
            payload_str=json.dumps(first_log["payload"]),
            previous_hash=first_log["previous_hash"],
            current_hash=first_log["current_hash"],
            timestamp=first_log["timestamp"],
            tenant_id=first_log.get("tenant_id", "default_tenant")
        )

        daemon1 = AuditConsensusDaemon(ledger1, node_id="node-1", sync_interval=100.0)
        daemon2 = AuditConsensusDaemon(ledger2, node_id="node-2", sync_interval=100.0)

        await daemon1.start()
        await daemon2.start()

        # 3. Node 1 broadcasts its status.
        # This will trigger Node 2 to request missing logs, Node 1 to reply, and Node 2 to self-heal
        await daemon1.broadcast_status()

        # Node 2 should have replicated the missing events + recorded the CONSENSUS_RECOVERY event
        logs2 = ledger2.get_logs()
        assert len(logs2) == 4 # EVENT_A + EVENT_B + EVENT_C + CONSENSUS_RECOVERY
        
        # Verify Node 2's chain integrity
        res_integrity = ledger2.verify_chain_integrity()
        assert res_integrity["valid"] is True

        await daemon1.stop()
        await daemon2.stop()

    finally:
        for name, val in old_brokers.items():
            if sys.modules.get(name):
                sys.modules[name]._global_broker = val
        shutil.rmtree(dir_node1)
        shutil.rmtree(dir_node2)


@pytest.mark.asyncio
async def test_daemon_tampering_and_fork_detection():
    """Verify that an unresolvable Merkle Root mismatch (same count, diff root) logs a SOC2_VIOLATION."""
    dir_node1 = tempfile.mkdtemp()
    dir_node2 = tempfile.mkdtemp()
    
    broker = MockSyncBroker()
    
    import sys
    old_brokers = {}
    for name, module in list(sys.modules.items()):
        if name.endswith("core.broker"):
            old_brokers[name] = getattr(module, "_global_broker", None)
            module._global_broker = broker

    try:
        ledger1 = AuditLedger(dir_node1)
        ledger2 = AuditLedger(dir_node2)

        # Node 1 and Node 2 both record 1 event, but with DIFFERENT payloads (Fork / Tamper)
        ledger1.record_event("EVENT_X", {"payload": "Legitimate Node 1 Payload"})
        ledger2.record_event("EVENT_X", {"payload": "Tampered Node 2 Payload"})

        daemon1 = AuditConsensusDaemon(ledger1, node_id="node-1", sync_interval=100.0)
        daemon2 = AuditConsensusDaemon(ledger2, node_id="node-2", sync_interval=100.0)

        await daemon1.start()
        await daemon2.start()

        # Node 1 broadcasts status
        await daemon1.broadcast_status()

        # Node 2 should detect equal count (1) but mismatching Merkle Root, and log a SOC2_VIOLATION
        logs2 = ledger2.get_logs()
        # EVENT_X + SOC2_VIOLATION
        assert len(logs2) == 2
        assert logs2[1]["event_type"] == "SOC2_VIOLATION"
        assert "unresolvable fork detected" in logs2[1]["payload"]["error"]

        await daemon1.stop()
        await daemon2.stop()

    finally:
        for name, val in old_brokers.items():
            if sys.modules.get(name):
                sys.modules[name]._global_broker = val
        shutil.rmtree(dir_node1)
        shutil.rmtree(dir_node2)


@pytest.mark.asyncio
async def test_daemon_tampered_recovery_logs():
    """Verify that incoming replication logs with invalid content hashes trigger SOC2_VIOLATION."""
    dir_node1 = tempfile.mkdtemp()
    dir_node2 = tempfile.mkdtemp()
    
    broker = MockSyncBroker()
    
    import sys
    old_brokers = {}
    for name, module in list(sys.modules.items()):
        if name.endswith("core.broker"):
            old_brokers[name] = getattr(module, "_global_broker", None)
            module._global_broker = broker

    try:
        ledger1 = AuditLedger(dir_node1)
        ledger2 = AuditLedger(dir_node2)

        # Node 1 records 2 events
        ledger1.record_event("EVENT_A", {"data": 10})
        ledger1.record_event("EVENT_B", {"data": 20})

        # Node 2 is empty (lagging behind)
        daemon1 = AuditConsensusDaemon(ledger1, node_id="node-1", sync_interval=100.0)
        daemon2 = AuditConsensusDaemon(ledger2, node_id="node-2", sync_interval=100.0)

        await daemon1.start()
        await daemon2.start()

        # Intercept Node 1's logs_request handler to return tampered logs (content hash mismatch)
        original_process_request = daemon1.process_request
        async def mock_on_request(msg):
            # Capture the original response, modify it, and publish
            if msg.get("type") == "logs_request" and msg.get("provider_id") == "node-1":
                logs = ledger1.get_logs_after(msg.get("after_id", 0))
                # Tamper with the content
                if logs:
                    logs[0]["payload"] = '{"tampered": "true"}' # Hash won't match stored current_hash!
                resp = {
                    "type": "logs_response",
                    "provider_id": "node-1",
                    "logs": logs
                }
                await broker.publish(f"audit:sync:response:{msg.get('requester_id')}", resp)
        
        daemon1.process_request = mock_on_request

        # Node 1 broadcasts status, triggering Node 2 request
        await daemon1.broadcast_status()

        # Node 2 should reject the logs due to verification failure, and log a SOC2_VIOLATION
        logs2 = ledger2.get_logs()
        # Should contain ONLY the SOC2_VIOLATION event, no EVENT_A/B appended!
        assert len(logs2) == 1
        assert logs2[0]["event_type"] == "SOC2_VIOLATION"
        assert "cryptographic verification" in logs2[0]["payload"]["error"]

        await daemon1.stop()
        await daemon2.stop()

    finally:
        for name, val in old_brokers.items():
            if sys.modules.get(name):
                sys.modules[name]._global_broker = val
        shutil.rmtree(dir_node1)
        shutil.rmtree(dir_node2)


def test_api_endpoints():
    """Verify audit status and manual sync trigger REST endpoints."""
    client = TestClient(api.app)
    
    # 1. Mock the consensus daemon
    mock_daemon = MagicMock()
    mock_daemon.peer_states = {
        "peer-node-abc": {
            "last_seen": "2026-06-05T08:00:00Z",
            "event_count": 5,
            "merkle_root": "a" * 64,
            "status": "synchronized"
        }
    }
    mock_daemon.trigger_manual_sync = AsyncMock()
    
    # Set the global daemon in API module
    with patch("api._audit_daemon", mock_daemon):
        # 2. Test GET /v1/audit/status
        resp_status = client.get("/v1/audit/status")
        assert resp_status.status_code == 200
        data_status = resp_status.json()
        assert data_status["status"] == "success"
        assert "merkle_root" in data_status
        assert "peers" in data_status
        assert "peer-node-abc" in data_status["peers"]

        # 3. Test POST /v1/audit/sync
        resp_sync = client.post("/v1/audit/sync")
        assert resp_sync.status_code == 200
        data_sync = resp_sync.json()
        assert data_sync["status"] == "success"
        assert "Consensus audit triggered" in data_sync["message"]
        mock_daemon.trigger_manual_sync.assert_called_once()
