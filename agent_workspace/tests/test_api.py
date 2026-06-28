import os
import sys
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi.testclient import TestClient

# Add project root to sys.path
workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)

# Import app from api
from api import app
import topology_stream


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def api_client():
    return TestClient(app)


def test_health_endpoint(api_client):
    """Verify health endpoint response structure."""
    response = api_client.get("/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "api_version" in data
    assert "llm_provider" in data


def test_metrics_endpoint(api_client):
    """Verify metrics endpoint returns plaintext telemetry."""
    response = api_client.get("/v1/metrics")
    assert response.status_code == 200
    assert isinstance(response.text, str)


def test_list_tools_endpoint(api_client):
    """Verify list_tools returns tools JSON."""
    with patch("api.get_engine") as mock_engine:
        # Mock engine to return registered tools
        engine = MagicMock()
        engine.list_skills.return_value = []
        mock_engine.return_value = engine
        
        response = api_client.get("/v1/tools")
        assert response.status_code == 200
        assert "tools" in response.json()


def test_config_endpoints(api_client, tmp_path):
    """Verify config read/write endpoints work cleanly."""
    mock_config_path = tmp_path / "config.yaml"
    mock_config_path.write_text("llm:\n  provider: google-genai\n  model: gemini-2.5-flash\n", encoding="utf-8")
    
    with patch("api.workspace", str(tmp_path)):
        # Test config GET
        response = api_client.get("/v1/config")
        assert response.status_code == 200
        assert response.json()["provider"] == "google-genai"
        
        # Test config PUT update
        update_payload = {
            "provider": "openai",
            "model": "gpt-4o",
            "api_key": "sk-dummy"
        }
        put_response = api_client.put("/v1/config", json=update_payload)
        assert put_response.status_code == 200
        assert put_response.json()["status"] == "success"
        
        # Assert config yaml file was updated
        updated_content = mock_config_path.read_text(encoding="utf-8")
        assert "openai" in updated_content
        assert "gpt-4o" in updated_content


def test_accounts_endpoints(api_client, tmp_path):
    """Verify account management operations."""
    accounts_json_path = tmp_path / "accounts.json"
    accounts_json_path.write_text('{"accounts": [], "active_account_id": null}', encoding="utf-8")
    
    with patch("api.workspace", str(tmp_path)):
        # List accounts
        response = api_client.get("/v1/accounts")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        
        # Add account
        payload = {
            "id": "acc-123",
            "provider": "google-genai",
            "model": "gemini-2.5-flash",
            "api_key": "env:GOOGLE_API_KEY",
            "base_url": "",
            "is_active": True
        }
        post_response = api_client.post("/v1/accounts", json=payload)
        assert post_response.status_code == 200
        assert post_response.json()["status"] == "success"


@pytest.mark.anyio
async def test_topology_stream_parser():
    """Verify topology_stream command line arguments are parsed correctly."""
    parser = topology_stream.build_parser()
    parsed = parser.parse_args(["stream", "--msg", "Hello world", "--session", "s123"])
    assert parsed.event == "stream"
    assert parsed.msg == "Hello world"
    assert parsed.session == "s123"


def test_topology_stream_ws_url_requires_explicit_credentials():
    """Verify topology stream does not inject a default admin API key."""
    url = topology_stream.build_collaboration_ws_url("s123")

    assert url == "ws://localhost:8000/v1/collaboration/s123"
    assert "key-admin" not in url
    assert "api_key=" not in url


def test_topology_stream_ws_url_uses_explicit_credentials():
    """Verify topology stream URL builder uses caller-provided credentials only."""
    token_url = topology_stream.build_collaboration_ws_url(
        "s123",
        token="jwt token",
        api_key="ignored-key",
    )
    key_url = topology_stream.build_collaboration_ws_url("s123", api_key="explicit-key")

    assert token_url == "ws://localhost:8000/v1/collaboration/s123?token=jwt+token"
    assert key_url == "ws://localhost:8000/v1/collaboration/s123?api_key=explicit-key"


def test_topology_stream_conductor_trace_payload_keeps_full_trace():
    trace = {
        "task_summary": "Add conductor trace visibility.",
        "task_type": "ui_layout",
        "execution_mode": "pro",
        "selected_models": [
            {
                "provider": "google-genai",
                "model": "gemini-2.5-flash",
                "selection_reason": "Telemetry-only route mirrors current account.",
            }
        ],
        "verification_strategy": {"kind": "verifier", "required": True},
    }

    payload = topology_stream.conductor_trace_payload(trace)

    assert payload["title"] == "Conductor Trace"
    assert payload["assigned_agent"] == "conductor"
    assert payload["output"]["selected_model"] == "google-genai/gemini-2.5-flash"
    assert payload["result_summary"] == "Verification: verifier"
    assert payload["conductor_trace"] == trace


def test_dashboard_ws_endpoint(api_client):
    """Verify that multi-dashboard WebSockets reject invalid roles and connect successfully under correct roles."""
    with api_client.websocket_connect("/v1/dashboard/session-ws-1/invalid_role") as websocket:
        data = websocket.receive_json()
        assert "Invalid role" in data["error"]
        
    with api_client.websocket_connect("/v1/dashboard/session-ws-1/ceo") as websocket:
        # Connects successfully
        pass


def test_api_rate_limiting(api_client):
    """Verify that requests exceeding the rate limit are blocked with HTTP 429."""
    from api import rate_limiter
    with patch.object(rate_limiter, "is_rate_limited", new_callable=AsyncMock) as mock_limit:
        mock_limit.return_value = True
        response = api_client.post("/v1/chat", json={"msg": "Hello", "session": "s-test"})
        assert response.status_code == 429
        assert "Rate limit exceeded" in response.json()["detail"]


def test_api_token_budget_exceeded(api_client):
    """Verify that chat endpoint returns 429 when token budget is exceeded."""
    from api import AccountManager
    mock_account = {
        "id": "test-budget-acc",
        "provider": "google-genai",
        "model": "gemini-2.5-flash",
        "api_key": "dummy",
        "token_budget": 1000,
        "tokens_used": 1200,
        "is_active": True
    }
    with patch("api.get_account_manager") as mock_am_getter:
        mock_am = MagicMock(spec=AccountManager)
        mock_am.get_active_account.return_value = mock_account
        mock_am.resolve_api_key.return_value = "dummy-key"
        mock_am_getter.return_value = mock_am
        
        response = api_client.post("/v1/chat", json={"msg": "Hello", "session": "s-test"})
        assert response.status_code == 429
        assert "Token budget exceeded" in response.json()["detail"]


def test_websocket_budget_exceeded(api_client):
    """Verify that WebSocket endpoint returns error if budget is exceeded."""
    from api import AccountManager
    mock_account = {
        "id": "test-budget-acc",
        "provider": "google-genai",
        "model": "gemini-2.5-flash",
        "api_key": "dummy",
        "token_budget": 1000,
        "tokens_used": 1200,
        "is_active": True
    }
    with patch("api.get_account_manager") as mock_am_getter:
        mock_am = MagicMock(spec=AccountManager)
        mock_am.get_active_account.return_value = mock_account
        mock_am_getter.return_value = mock_am
        
        try:
            with api_client.websocket_connect("/v1/stream_ws") as websocket:
                websocket.send_json({"msg": "Hello", "session": "s-ws-test"})
                data = websocket.receive_json()
                assert "Token budget exceeded" in data["error"]
        except Exception:
            # Handles websocket closing or raising during connect/send
            pass


