import sys
from pathlib import Path

# Add project root and workspace to sys.path
root_dir = Path(__file__).resolve().parents[2]
workspace_dir = root_dir / "agent_workspace"
for p in (str(root_dir), str(workspace_dir)):
    if p not in sys.path:
        sys.path.insert(0, p)

import pytest
from unittest.mock import AsyncMock
from agent_workspace.core.ws_manager import CrewSyncManager


class MockWebSocket:
    def __init__(self):
        self.send_json = AsyncMock()
        self.close = AsyncMock()


@pytest.mark.asyncio
async def test_crew_sync_manager_connect_disconnect():
    manager = CrewSyncManager()
    ws1 = MockWebSocket()
    session_id = "test-session-1"
    key = b"12345678901234567890123456789012"

    manager.connect(session_id, ws1, key)
    assert session_id in manager.sessions
    assert len(manager.sessions[session_id]) == 1

    ws2 = MockWebSocket()
    manager.connect(session_id, ws2, key)
    assert len(manager.sessions[session_id]) == 2

    manager.disconnect(session_id, ws1)
    assert len(manager.sessions[session_id]) == 1
    assert manager.sessions[session_id][0][0] == ws2

    manager.disconnect(session_id, ws2)
    assert session_id not in manager.sessions


@pytest.mark.asyncio
async def test_crew_sync_manager_broadcast():
    manager = CrewSyncManager()
    session_id = "test-session-broadcast"
    key = b"12345678901234567890123456789012"

    ws_sender = MockWebSocket()
    ws_receiver1 = MockWebSocket()
    ws_receiver2 = MockWebSocket()

    manager.connect(session_id, ws_sender, key)
    manager.connect(session_id, ws_receiver1, key)
    manager.connect(session_id, ws_receiver2, key)

    message = '{"type": "task_progress", "data": "50%"}'
    await manager.broadcast(session_id, ws_sender, message)

    ws_sender.send_json.assert_not_called()
    assert ws_receiver1.send_json.call_count == 1
    assert ws_receiver2.send_json.call_count == 1
    sent_payload = ws_receiver1.send_json.call_args[0][0]
    assert "ciphertext" in sent_payload
    assert "nonce" in sent_payload


@pytest.mark.asyncio
async def test_crew_sync_manager_disconnect_nonexistent():
    manager = CrewSyncManager()
    ws = MockWebSocket()
    manager.disconnect("non-existent", ws)
