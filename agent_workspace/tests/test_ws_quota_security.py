import os
import sys
from unittest.mock import AsyncMock, patch

import pytest

workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)

from api import generate_jwt
from core.rate_limit import TenantRequestRateLimiter
from routes.dependencies import API_KEYS, verify_websocket_tenant


class FakeWebSocket:
    def __init__(self, *, headers=None, query=None):
        self.headers = headers or {}
        self.query_params = query or {}
        self.accept = AsyncMock()
        self.close = AsyncMock()


@pytest.mark.asyncio
async def test_websocket_rejects_query_string_credentials(monkeypatch):
    monkeypatch.setenv("LAS_JWT_SECRET", "test-only-secret-for-phase-72-auth")
    token = generate_jwt({"tenant_id": "tenant-a"})
    websocket = FakeWebSocket(query={"token": token})

    assert await verify_websocket_tenant(websocket) is None
    websocket.close.assert_awaited_once()
    assert websocket.close.await_args.kwargs["code"] == 4001


@pytest.mark.asyncio
async def test_websocket_header_jwt_binds_verified_tenant(monkeypatch, tmp_path):
    monkeypatch.setenv("LAS_JWT_SECRET", "test-only-secret-for-phase-72-auth")
    token = generate_jwt({"tenant_id": "tenant-a"})
    websocket = FakeWebSocket(headers={"authorization": f"Bearer {token}"})

    with patch("routes.dependencies.get_workspace", return_value=str(tmp_path)):
        assert await verify_websocket_tenant(websocket) == "tenant-a"
    websocket.accept.assert_awaited_once()


@pytest.mark.asyncio
async def test_websocket_does_not_trust_forged_session_mapping(tmp_path):
    websocket = FakeWebSocket(query={"session_id": "session-a"})
    with patch("routes.dependencies.get_account_manager") as manager:
        manager.return_value.get_session_tenant.return_value = "tenant-a"
        assert await verify_websocket_tenant(websocket, "session-a") is None
    websocket.close.assert_awaited_once()
    assert websocket.close.await_args.kwargs["code"] == 4001


@pytest.mark.asyncio
async def test_websocket_rejects_unsafe_session_id_before_authentication():
    websocket = FakeWebSocket(headers={"authorization": "Bearer unused"})

    assert await verify_websocket_tenant(websocket, "../escape") is None
    websocket.close.assert_awaited_once_with(code=1008, reason="Invalid session ID")


@pytest.mark.asyncio
async def test_tenant_request_limiter_is_shared_by_db(tmp_path):
    db_path = tmp_path / "rate-limit.db"
    first = TenantRequestRateLimiter(db_path, limit=1, window_seconds=60)
    second = TenantRequestRateLimiter(db_path, limit=1, window_seconds=60)

    assert await first.is_rate_limited("tenant-a") is False
    assert await second.is_rate_limited("tenant-a") is True
    assert await second.is_rate_limited("tenant-b") is False
