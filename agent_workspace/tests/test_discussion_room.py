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


class MockLLMProvider:
    """Mock LLM Provider returning role-based responses."""
    def __init__(self, *args, **kwargs):
        pass

    async def complete(self, system_prompt, messages, tool_schemas, config):
        user_content = messages[0]["content"] if messages else ""
        
        if "moderator" in system_prompt.lower() or "synthesize" in user_content.lower():
            return ProviderResponse("text", "Consensus Summary: Consensus reached on debate room implementation.\n- Agreements: Solid design\n- Next steps: Add unit tests.")
        elif "analyst" in system_prompt.lower():
            return ProviderResponse("text", "As Analyst: Requirements look complete.")
        elif "programmer" in system_prompt.lower() or "software engineer" in system_prompt.lower():
            return ProviderResponse("text", "As Programmer: Implementation looks robust.")
        
        return ProviderResponse("text", "Generic contribution")


@pytest.fixture
def mock_debate_env():
    """Create a temporary debate environment with accounts.json."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Write standard accounts.json
        accounts_data = {
            "accounts": [
                {
                    "id": "default-account",
                    "provider": "google-genai",
                    "model": "gemini-2.5-flash",
                    "api_key": "dummy_key",
                    "is_active": True
                }
            ],
            "active_account_id": "default-account"
        }
        with open(temp_path / "accounts.json", "w", encoding="utf-8") as f:
            json.dump(accounts_data, f)
            
        yield temp_dir


@pytest.mark.anyio
async def test_discussion_room_round_robin(mock_debate_env):
    """Verify sequential round-robin debate orchestration."""
    room = DiscussionRoom(workspace_path=mock_debate_env)
    
    agents = [
        {"role": "analyst", "name": "Alice"},
        {"role": "programmer", "name": "Bob"}
    ]
    
    mock_provider = MockLLMProvider()
    
    with patch("core.discussion_room.ProviderFactory.get_provider", return_value=mock_provider):
        result = await room.run(
            topic="Should we adopt contract-first design?",
            agents=agents,
            max_rounds=1
        )
        
        # Verify result keys
        assert result["topic"] == "Should we adopt contract-first design?"
        assert result["rounds"] == 1
        
        # Verify transcript entries
        transcript = result["transcript"]
        assert len(transcript) == 2  # Alice (analyst) and Bob (programmer)
        
        assert transcript[0]["agent"] == "Alice"
        assert transcript[0]["role"] == "analyst"
        assert "Requirements look complete." in transcript[0]["content"]
        
        assert transcript[1]["agent"] == "Bob"
        assert transcript[1]["role"] == "programmer"
        assert "Implementation looks robust." in transcript[1]["content"]
        
        # Verify consensus summary synthesis
        summary = result["consensus_summary"]
        assert "Consensus Summary: Consensus reached" in summary
        assert "Agreements: Solid design" in summary


@pytest.mark.anyio
async def test_discussion_room_graceful_fallback(mock_debate_env):
    """Verify that when a provider encounters a connection issue, it fallbacks gracefully."""
    room = DiscussionRoom(workspace_path=mock_debate_env)
    
    agents = [
        {"role": "analyst", "name": "Alice"}
    ]
    
    # Mocking provider to raise an exception
    mock_provider = MagicMock()
    mock_provider.complete = AsyncMock(side_effect=RuntimeError("Connection timeout"))
    
    with patch("core.discussion_room.ProviderFactory.get_provider", return_value=mock_provider):
        result = await room.run(
            topic="Failing LLM provider test",
            agents=agents,
            max_rounds=1
        )
        
        transcript = result["transcript"]
        assert len(transcript) == 1
        assert "Connection Error: Connection timeout" in transcript[0]["content"]
        
        # Consensus should still try to synthesize (and moderator synthesis can raise too, handled gracefully)
        assert "Error synthesizing consensus" in result["consensus_summary"]
