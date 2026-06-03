import os
import sys
import json
import tempfile
import time
import pytest
import threading
from pathlib import Path
from fastapi.testclient import TestClient

# Add project root to sys.path
workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)

from api import app, collab_manager
from core.memory import CRDTState, DeltaStateReconciler


@pytest.fixture
def temp_workspace():
    """Scaffolds a mock temp workspace for delta state reconciliation."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


def test_crdt_element_set_reconciliation():
    """Assert that CRDTState handles LWW elements, deletions, delta generation, and merging properly."""
    state1 = CRDTState(replica_id="replica-1")
    state2 = CRDTState(replica_id="replica-2")

    t1 = time.time()
    t2 = t1 + 10.0
    t3 = t2 + 10.0

    # 1. Update and Delta generation
    delta1 = state1.update("key1", "val1_initial", timestamp=t1)
    assert delta1["values"]["key1"] == "val1_initial"
    assert delta1["timestamps"]["key1"] == t1

    # 2. Merge delta
    state2.merge_delta(delta1)
    assert state2.values["key1"] == "val1_initial"

    # 3. LWW Conflict Resolution (Higher timestamp wins)
    delta2 = state2.update("key1", "val1_updated_newer", timestamp=t3)
    delta3 = state1.update("key1", "val1_stale_older", timestamp=t2)

    # Merge stale first then new
    state1.merge_delta(delta2)
    assert state1.values["key1"] == "val1_updated_newer"

    state1.merge_delta(delta3)
    # Newest value should still persist (LWW logic)
    assert state1.values["key1"] == "val1_updated_newer"

    # 4. Tombstone check
    delta_del = state1.delete("key1", timestamp=t3 + 5.0)
    state2.merge_delta(delta_del)
    assert "key1" not in state2.values
    assert state2.tombstones["key1"] == t3 + 5.0


def test_delta_state_reconciler_thread_safety(temp_workspace):
    """Verify DeltaStateReconciler handles concurrent merges and persists accurately."""
    reconciler = DeltaStateReconciler(temp_workspace)
    
    # Assert initial state
    assert reconciler.get_state() == {}

    # Update state
    reconciler.apply_update("x", 100)
    assert reconciler.get_state()["x"] == 100

    # Run concurrent threads updating the state reconciler
    def worker(key, val):
        reconciler.apply_update(key, val)

    threads = []
    for i in range(10):
        t = threading.Thread(target=worker, args=(f"thread_{i}", i))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    # Reconciled state should contain all entries
    final_state = reconciler.get_state()
    for i in range(10):
        assert final_state[f"thread_{i}"] == i


def test_websocket_pubsub_collaboration():
    """Test that collab_manager handles multiple subscriptions and broadcasts correct channel updates."""
    client = TestClient(app)
    session_id = "test-collab-session"

    with client.websocket_connect(f"/v1/collaboration/{session_id}") as ws1:
        # Subscribe to logs
        ws1.send_json({"action": "subscribe", "channel": "logs"})
        resp1 = ws1.receive_json()
        assert resp1["status"] == "subscribed"
        assert resp1["channel"] == "logs"

        # Subscribe to topology
        ws1.send_json({"action": "subscribe", "channel": "topology"})
        resp2 = ws1.receive_json()
        assert resp2["status"] == "subscribed"
        assert resp2["channel"] == "topology"

        with client.websocket_connect(f"/v1/collaboration/{session_id}") as ws2:
            # Subscribe to logs too
            ws2.send_json({"action": "subscribe", "channel": "logs"})
            resp3 = ws2.receive_json()
            assert resp3["status"] == "subscribed"

            # Publish log event from ws2
            payload = {"event": "CTO_joined", "agent": "CTO"}
            ws2.send_json({
                "action": "publish",
                "channel": "logs",
                "payload": payload
            })
            # ws2 expects two incoming messages:
            # 1. The broadcast message it sent to the channel it is subscribed to.
            # 2. The publish response confirmation {"status": "published"}
            # Since order depends on scheduling, we read both and assert based on keys.
            msg_a = ws2.receive_json()
            msg_b = ws2.receive_json()
            if "status" in msg_a:
                resp4 = msg_a
                incoming2 = msg_b
            else:
                resp4 = msg_b
                incoming2 = msg_a

            assert resp4["status"] == "published"
            assert resp4["channel"] == "logs"

            assert incoming2["channel"] == "logs"
            assert incoming2["payload"]["event"] == "CTO_joined"

            # Check that ws1 received the published log event
            incoming1 = ws1.receive_json()
            assert incoming1["channel"] == "logs"
            assert incoming1["payload"]["event"] == "CTO_joined"
