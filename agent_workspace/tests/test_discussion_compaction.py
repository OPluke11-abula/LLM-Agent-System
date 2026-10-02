import os
import json
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from pathlib import Path
from agent_workspace.core.discussion_room import DiscussionRoom


@pytest.fixture
def temp_workspace(tmp_path):
    """Set up temporary workspace structure."""
    agent_dir = tmp_path / ".agent"
    agent_dir.mkdir(parents=True, exist_ok=True)
    (agent_dir / "memory" / "archive").mkdir(parents=True, exist_ok=True)

    # Write minimum configs
    (tmp_path / "accounts.json").write_text(json.dumps({
        "active_account": "test-account",
        "accounts": [
            {
                "id": "test-account",
                "provider": "google-genai",
                "model": "gemini-2.5-flash",
                "api_key": "dummy-key",
                "tokens_used": 0,
                "token_budget": 100000
            }
        ]
    }))
    (tmp_path / "config.yaml").write_text("agent:\n  max_iterations: 5\n")
    return tmp_path


@pytest.mark.asyncio
async def test_discussion_room_participant_ceiling(temp_workspace):
    room = DiscussionRoom(workspace_path=str(temp_workspace))

    # 6 agents exceeds standard max_participants limit (5)
    agents = [
        {"role": "ceo", "name": "Agent 1"},
        {"role": "cto", "name": "Agent 2"},
        {"role": "dev", "name": "Agent 3"},
        {"role": "qa", "name": "Agent 4"},
        {"role": "cfo", "name": "Agent 5"},
        {"role": "analyst", "name": "Agent 6"},
    ]

    with pytest.raises(ValueError) as exc_info:
        await room.run("Test Topic", agents)
    assert "exceeds max_participants ceiling" in str(exc_info.value)


@pytest.mark.asyncio
async def test_discussion_room_nested_swarm_ceiling(temp_workspace):
    room = DiscussionRoom(workspace_path=str(temp_workspace))

    agents = [{"role": "ceo", "name": "Agent 1"}]

    # More than 3 sub-problems (max_sub_swarms=3)
    sub_problems = [
        {"topic": "SP 1", "agents": agents},
        {"topic": "SP 2", "agents": agents},
        {"topic": "SP 3", "agents": agents},
        {"topic": "SP 4", "agents": agents},
    ]

    with pytest.raises(ValueError) as exc_info:
        await room.run("Test Topic", agents, sub_problems=sub_problems)
    assert "exceeds max_sub_swarms ceiling" in str(exc_info.value)


@pytest.mark.asyncio
async def test_discussion_room_nested_participant_ceiling(temp_workspace):
    room = DiscussionRoom(workspace_path=str(temp_workspace))

    agents = [{"role": "ceo", "name": "Agent 1"}]

    # Sub-problem has 6 agents (exceeds max_participants=5)
    sub_problems = [
        {
            "topic": "SP 1",
            "agents": [
                {"role": "ceo"}, {"role": "cto"}, {"role": "dev"},
                {"role": "qa"}, {"role": "cfo"}, {"role": "analyst"}
            ]
        }
    ]

    with pytest.raises(ValueError) as exc_info:
        await room.run("Test Topic", agents, sub_problems=sub_problems)
    assert "exceeds max_participants ceiling" in str(exc_info.value)


def test_discussion_room_is_line_protected():
    room = DiscussionRoom(workspace_path=".")

    assert room._is_line_protected("Let's look at file://workspace/test.py") is True
    assert room._is_line_protected("Please fix the Error in the log") is True
    assert room._is_line_protected("The consensus Decision was approved") is True
    assert room._is_line_protected("Active Disagreement exists on this PR") is True
    assert room._is_line_protected("hash: a90ef23812a67e98d249f32148283a0022a10bf9828d172e90e29b1284a1e0fb") is True

    assert room._is_line_protected("This is a normal line with no secrets.") is False


def test_discussion_room_compact_transcript():
    room = DiscussionRoom(workspace_path=".")

    # Small max_tokens so it triggers compaction
    transcript = [
        {"agent": "Alice", "role": "dev", "content": "This is a very long line that should be compacted because it does not have any protected keywords." * 5},
        {"agent": "Bob", "role": "qa", "content": "Decision: We will use local sqlite.\nLet's check file://db.py and fix the Exception.\nHere is hash: 1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"},
    ]

    compacted = room._compact_transcript(transcript, max_tokens=100)

    # Compacted should contain protected strings intact
    assert "Decision: We will use local sqlite" in compacted
    assert "file://db.py" in compacted
    assert "Exception" in compacted
    assert "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef" in compacted
    # The long line without keywords should be truncated
    assert "[compacted]" in compacted


@pytest.mark.asyncio
async def test_discussion_room_run_capping_and_archiving(temp_workspace):
    # Setup mock provider complete method
    mock_provider = MagicMock()
    mock_provider.complete = AsyncMock(return_value=("success", "Synthesized consensus content."))

    room = DiscussionRoom(workspace_path=str(temp_workspace))

    agents = [
        {"role": "ceo", "name": "CEO Agent"},
        {"role": "cto", "name": "CTO Agent"}
    ]

    with patch.object(room, "_resolve_agent_provider") as mock_resolve:
        # Resolve to our mock provider
        # Config has large max_tokens (e.g. 8192) to see if it gets capped
        mock_resolve.return_value = (mock_provider, {"model": "gemini-2.5-flash", "max_tokens": 8192}, "test-account")

        res = await room.run("Test topic", agents, max_rounds=1)

        # Verify provider complete config was capped
        for call in mock_provider.complete.call_args_list:
            config = call.kwargs["config"]
            assert config["max_tokens"] <= 1024

    # Verify archiving
    archive_dir = temp_workspace / ".agent" / "memory" / "archive"
    archive_files = list(archive_dir.glob("*.json"))
    assert len(archive_files) > 0

    # Read archived file
    archived_data = json.loads(archive_files[0].read_text(encoding="utf-8"))
    assert archived_data["topic"] == "Test topic"
    assert "transcript" in archived_data
    assert "consensus_summary" in archived_data
