import os
import sys
import tempfile
import pytest
import json
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

# Add project root to sys.path
workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)

from core.discussion_room import DiscussionRoom
from core.providers import ProviderResponse


@pytest.fixture
def anyio_backend():
    return "asyncio"


class CaptureConfigMockProvider:
    """Mock LLM Provider that captures the config/model passed to complete."""
    def __init__(self, *args, **kwargs):
        self.captured_configs = []

    async def complete(self, system_prompt, messages, tool_schemas, config):
        self.captured_configs.append(config)
        return ProviderResponse("text", "Mock Response")


@pytest.fixture
def mock_billing_env_pro():
    """Create a temporary debate environment with a premium Pro account."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        accounts_data = {
            "accounts": [
                {
                    "id": "pro-account",
                    "provider": "google-genai",
                    "model": "gemini-2.5-pro",
                    "api_key": "dummy_key",
                    "is_active": True
                }
            ],
            "active_account_id": "pro-account"
        }
        with open(temp_path / "accounts.json", "w", encoding="utf-8") as f:
            json.dump(accounts_data, f)
            
        yield temp_dir


@pytest.fixture
def mock_billing_env_flash():
    """Create a temporary debate environment with a standard Flash account."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        accounts_data = {
            "accounts": [
                {
                    "id": "flash-account",
                    "provider": "google-genai",
                    "model": "gemini-2.5-flash",
                    "api_key": "dummy_key",
                    "is_active": True
                }
            ],
            "active_account_id": "flash-account"
        }
        with open(temp_path / "accounts.json", "w", encoding="utf-8") as f:
            json.dump(accounts_data, f)
            
        yield temp_dir


@pytest.mark.anyio
async def test_model_tier_downscaling(mock_billing_env_pro):
    """Assert that model downscaling from pro to flash is triggered correctly for low complexity/summary tasks."""
    room = DiscussionRoom(workspace_path=mock_billing_env_pro)
    
    agents = [
        {"role": "analyst", "name": "Alice"}
    ]
    
    mock_provider = CaptureConfigMockProvider()
    
    with patch("core.discussion_room.ProviderFactory.get_provider", return_value=mock_provider):
        result = await room.run(
            topic="This is a simple summary task",
            agents=agents,
            max_rounds=1
        )
        
        # Verify captured configs used gemini-2.5-flash instead of gemini-2.5-pro
        assert len(mock_provider.captured_configs) > 0
        for cfg in mock_provider.captured_configs:
            assert cfg["model"] == "gemini-2.5-flash"


@pytest.mark.anyio
async def test_model_tier_upscaling(mock_billing_env_flash):
    """Assert that model upscaling from flash to pro is triggered correctly for large context tasks."""
    room = DiscussionRoom(workspace_path=mock_billing_env_flash)
    
    agents = [
        {"role": "analyst", "name": "Alice"}
    ]
    
    mock_provider = CaptureConfigMockProvider()
    
    # We patch _resolve_agent_provider or simulate large context length.
    # In room.run, the prompt length is calculated as len(system_prompt + user_content) // 4.
    # To force prompt_len > 8000, we can use a very long topic/system prompt or mock.
    # Let's use a very long topic to naturally trigger it!
    # A string of 35,000 characters is ~8,750 tokens, which easily exceeds the 8000 tokens threshold!
    long_topic = "federated swarm optimization" + (" " * 35000)
    
    with patch("core.discussion_room.ProviderFactory.get_provider", return_value=mock_provider):
        await room.run(
            topic=long_topic,
            agents=agents,
            max_rounds=1
        )
        
        # Verify that at least one config upscaled to pro
        assert len(mock_provider.captured_configs) > 0
        # The debate round has prompt_len > 8000 so it will upscale
        assert mock_provider.captured_configs[0]["model"] == "gemini-2.5-pro"


@pytest.mark.anyio
async def test_invoice_persistence_and_fields(mock_billing_env_flash):
    """Assert that invoice telemetry trails are written under memory/semantic/billing/ with correct schemas."""
    room = DiscussionRoom(workspace_path=mock_billing_env_flash)
    
    agents = [
        {"role": "analyst", "name": "Alice"}
    ]
    
    mock_provider = CaptureConfigMockProvider()
    
    with patch("core.discussion_room.ProviderFactory.get_provider", return_value=mock_provider):
        await room.run(
            topic="Test invoice generation",
            agents=agents,
            max_rounds=1,
            session_id="session-billing-test"
        )
        
        # Check persisted invoice file
        billing_dir = Path(mock_billing_env_flash) / "memory" / "semantic" / "billing"
        assert billing_dir.is_dir()
        
        json_files = list(billing_dir.glob("*.json"))
        assert len(json_files) == 1
        
        with open(json_files[0], "r", encoding="utf-8") as f:
            invoice = json.load(f)
            
        assert "invoice_id" in invoice
        assert invoice["session_id"] == "session-billing-test"
        assert invoice["topic"] == "Test invoice generation"
        assert "model_used" in invoice
        assert "prompt_tokens" in invoice
        assert "completion_tokens" in invoice
        assert "estimated_cost_usd" in invoice
        assert "timestamp" in invoice
        
        # Since it's flash, cost should be positive but small, verify schema types
        assert isinstance(invoice["prompt_tokens"], int)
        assert isinstance(invoice["completion_tokens"], int)
        assert isinstance(invoice["estimated_cost_usd"], float)
