import os
import sys
import tempfile
import pytest
import json
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

# Add project root to sys.path
workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, workspace_dir)

from core.account_manager import AccountManager
from core.discussion_room import DiscussionRoom

@pytest.fixture
def mock_accounts_env():
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Write accounts.json
        accounts_data = {
            "accounts": [
                {
                    "id": "primary-acc",
                    "provider": "google-genai",
                    "model": "gemini-2.5-flash",
                    "api_key": "some-key",
                    "token_budget": 1000,
                    "tokens_used": 1000, # Already exhausted!
                    "is_active": True
                },
                {
                    "id": "fallback-acc",
                    "provider": "google-genai",
                    "model": "gemini-2.5-flash",
                    "api_key": "fallback-key",
                    "token_budget": 5000,
                    "tokens_used": 0,
                    "is_active": False
                }
            ],
            "active_account_id": "primary-acc"
        }
        
        accounts_file = temp_path / "accounts.json"
        accounts_file.write_text(json.dumps(accounts_data, indent=2), encoding="utf-8")
        
        yield temp_dir

@pytest.mark.asyncio
async def test_account_failover_budget_exhaustion(mock_accounts_env):
    workspace = mock_accounts_env
    am = AccountManager(workspace)
    
    # Assert initial state
    active = am.get_active_account()
    assert active["id"] == "primary-acc"
    
    # Run swap
    swapped = am.swap_to_fallback()
    assert swapped is True
    
    new_active = am.get_active_account()
    assert new_active["id"] == "fallback-acc"

@pytest.mark.asyncio
async def test_discussion_room_failover_rate_limit(mock_accounts_env):
    workspace = mock_accounts_env
    
    room = DiscussionRoom(workspace_path=workspace)
    # Configure two accounts: primary (gets 429) and fallback (succeeds)
    # Reset primary budget so it gets selected
    room.account_manager.record_usage("primary-acc", -1000, 0)
    
    mock_provider = AsyncMock()
    # Mocking complete to return error (429 Rate Limit) for primary, but success for fallback
    call_count = 0
    async def mock_complete(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return ("error", "HTTP 429 Rate Limit Exceeded")
        return ("success", "Mocked response contribution")
        
    mock_provider.complete = mock_complete
    
    # Patch ProviderFactory
    from agent_workspace.core.providers import ProviderFactory
    original_get_provider = ProviderFactory.get_provider
    ProviderFactory.get_provider = MagicMock(return_value=mock_provider)
    
    try:
        # Run discussion debate loop
        topic = "Architectural boundary separation"
        agents = [
            {"role": "dev", "name": "DeveloperAgent"}
        ]
        
        results = await room.run(topic, agents, max_rounds=1)
        
        # Verify active account swapped to fallback-acc due to 429
        active_acc = room.account_manager.get_active_account()
        assert active_acc["id"] == "fallback-acc"
        
        # Verify debate completed successfully and got synthesis
        assert len(results["transcript"]) == 1
        assert "Mocked response contribution" in results["transcript"][0]["content"]
    finally:
        ProviderFactory.get_provider = original_get_provider
