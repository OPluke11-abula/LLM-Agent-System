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


class MockMultiSwarmProvider:
    """Mock LLM Provider returning specific sub-swarm and parent debate responses."""
    def __init__(self, *args, **kwargs):
        pass

    async def complete(self, system_prompt, messages, tool_schemas, config):
        user_content = messages[0]["content"] if messages else ""
        sys_prompt_lower = system_prompt.lower()
        user_content_lower = user_content.lower()

        # Check for sub-problems using highly precise topic boundaries
        is_sub1 = (
            "topic for discussion: resolve sub-problem 1" in user_content_lower or
            "topic discussed: resolve sub-problem 1" in user_content_lower
        )
        is_sub2 = (
            "topic for discussion: resolve sub-problem 2" in user_content_lower or
            "topic discussed: resolve sub-problem 2" in user_content_lower
        )

        if is_sub1:
            if "moderator" in sys_prompt_lower or "consensus_synthesis" in config.get("model", ""):
                return ProviderResponse("text", "Consensus Summary: Sub-problem 1 consensus reached.")
            return ProviderResponse("text", "Sub-swarm 1 analyst contribution")
        elif is_sub2:
            if "moderator" in sys_prompt_lower or "consensus_synthesis" in config.get("model", ""):
                return ProviderResponse("text", "Consensus Summary: Sub-problem 2 consensus reached.")
            return ProviderResponse("text", "Sub-swarm 2 programmer contribution")

        # Main parent debate response
        if "moderator" in sys_prompt_lower or "consensus_synthesis" in config.get("model", "") or "synthesize" in user_content_lower:
            return ProviderResponse("text", "Consensus Summary: Parent debate room completed synthesis.")
        
        return ProviderResponse("text", "Parent room analyst contribution")


@pytest.fixture
def mock_debate_env():
    """Create a temporary debate environment with accounts.json."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
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
async def test_hierarchical_multi_swarm_delegation(mock_debate_env):
    """Verify hierarchical multi-swarm delegation, parallel execution, and consensus synthesis."""
    room = DiscussionRoom(workspace_path=mock_debate_env)
    
    # Define main agents
    main_agents = [
        {"role": "analyst", "name": "Alice"}
    ]
    
    # Define parallel sub-swarms
    sub_problems = [
        {
            "topic": "Resolve sub-problem 1: database migration",
            "agents": [{"role": "analyst", "name": "Alice-Sub1"}],
            "session_id": "session-sub-1"
        },
        {
            "topic": "Resolve sub-problem 2: security auditing",
            "agents": [{"role": "programmer", "name": "Bob-Sub2"}],
            "session_id": "session-sub-2"
        }
    ]
    
    mock_provider = MockMultiSwarmProvider()
    
    with patch("core.discussion_room.ProviderFactory.get_provider", return_value=mock_provider):
        result = await room.run(
            topic="Adopt federated optimization?",
            agents=main_agents,
            max_rounds=1,
            sub_problems=sub_problems,
            session_id="parent-session"
        )
        
        assert result["topic"] == "Adopt federated optimization?"
        assert result["rounds"] == 1
        
        # Verify that parent synthesized consensus summary contains the merged sub-swarm reports
        summary = result["consensus_summary"]
        assert "Parent debate room completed synthesis" in summary
        assert "Integrated Sub-Swarm Consensus Reports" in summary
        assert "Resolve sub-problem 1: database migration" in summary
        assert "Resolve sub-problem 2: security auditing" in summary
        assert "Sub-problem 1 consensus reached" in summary
        assert "Sub-problem 2 consensus reached" in summary
