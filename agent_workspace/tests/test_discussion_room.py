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


@pytest.mark.anyio
async def test_run_corporate_audit_async(mock_debate_env):
    """Verify that run_corporate_audit executes the pytest suite using non-blocking subprocess."""
    room = DiscussionRoom(workspace_path=mock_debate_env)
    
    # Mock create_subprocess_exec
    mock_proc = AsyncMock()
    mock_proc.stdout = AsyncMock()
    mock_proc.stderr = AsyncMock()
    
    # stdout readline yields mock lines and then empty string
    mock_proc.stdout.readline = AsyncMock()
    mock_proc.stdout.readline.side_effect = [
        b"mock output line 1\n",
        b"mock output line 2\n",
        b""
    ]
    
    mock_proc.stderr.readline = AsyncMock()
    mock_proc.stderr.readline.side_effect = [
        b""
    ]
    
    mock_proc.wait = AsyncMock(return_value=0)
    
    with patch("asyncio.create_subprocess_exec", return_value=mock_proc) as mock_exec:
        result = await room.run_corporate_audit(
            task_id="T-1001",
            proposed_code="def test_sample(): pass"
        )
        
        # Verify subprocess exec was called correctly
        mock_exec.assert_called_once()
        assert "T-1001" in result["task_id"]
        assert result["qa_status"] == "PASS"
        assert result["passed"] is True
        assert "mock output line 1" in result["qa_feedback"]
        assert "mock output line 2" in result["qa_feedback"]


@pytest.mark.anyio
async def test_dynamic_role_guide_injection(mock_debate_env):
    """Verify that when dev and qa participate in a debate, their respective

    learning guides are correctly resolved, read, and injected.
    """
    temp_path = Path(mock_debate_env)
    
    # 1. Create directory structures
    roles_dir = temp_path / ".agent" / "prompts" / "roles"
    roles_dir.mkdir(parents=True, exist_ok=True)
    
    prog_dir = temp_path / ".agent" / "programmer"
    prog_dir.mkdir(parents=True, exist_ok=True)
    
    qa_dir = temp_path / ".agent" / "qa"
    qa_dir.mkdir(parents=True, exist_ok=True)
    
    # 2. Write role configuration files
    (roles_dir / "dev.md").write_text(
        "---\nid: dev\nrole: dev\npersona: \"Dynamic Dev Persona\"\nversion: \"1.0.0\"\n---\nSome body\n",
        encoding="utf-8"
    )
    (roles_dir / "qa.md").write_text(
        "---\nid: qa\nrole: qa\npersona: \"Dynamic QA Persona\"\nversion: \"1.0.0\"\n---\nSome body\n",
        encoding="utf-8"
    )
    
    # 3. Write learning guides
    (prog_dir / "programmer_learning_guide.md").write_text("Elite Programmer Guide Rules", encoding="utf-8")
    (qa_dir / "qa_learning_guide.md").write_text("Strict QA Guide Rules", encoding="utf-8")
    
    # 4. Instantiate DiscussionRoom
    room = DiscussionRoom(workspace_path=mock_debate_env)
    
    # 5. Setup captured prompts list
    captured_prompts = []
    
    class CaptureSystemPromptLLMProvider:
        async def complete(self, system_prompt, messages, tool_schemas, config):
            captured_prompts.append(system_prompt)
            return ProviderResponse("text", "Mock Response")
            
    mock_provider = CaptureSystemPromptLLMProvider()
    
    agents = [
        {"role": "dev", "name": "Alice"},
        {"role": "qa", "name": "Bob"}
    ]
    
    with patch("core.discussion_room.ProviderFactory.get_provider", return_value=mock_provider):
        await room.run(
            topic="Testing Dynamic Role Injection",
            agents=agents,
            max_rounds=1
        )
        
        # Verify both agents had their system prompts captured
        assert len(captured_prompts) >= 1
        
        # Alice (dev) should have Dynamic Dev Persona and Elite Programmer Guide Rules
        dev_prompt = captured_prompts[0]
        assert "Dynamic Dev Persona" in dev_prompt
        assert "SYSTEM SELF-LEARNING DIRECTIVES" in dev_prompt
        assert "Elite Programmer Guide Rules" in dev_prompt
        
        # Bob (qa) should have Dynamic QA Persona and Strict QA Guide Rules
        qa_prompt = captured_prompts[1]
        assert "Dynamic QA Persona" in qa_prompt
        assert "SYSTEM SELF-LEARNING DIRECTIVES" in qa_prompt
        assert "Strict QA Guide Rules" in qa_prompt


@pytest.mark.anyio
async def test_dynamic_role_fallback_and_scaffolding(mock_debate_env):
    """Verify fallback to DEFAULT_PERSONAS and automatic scaffolding of QA learning guide."""
    # Instantiate DiscussionRoom
    room = DiscussionRoom(workspace_path=mock_debate_env)
    
    captured_prompts = []
    
    class CaptureSystemPromptLLMProvider:
        async def complete(self, system_prompt, messages, tool_schemas, config):
            captured_prompts.append(system_prompt)
            return ProviderResponse("text", "Mock Response")
            
    mock_provider = CaptureSystemPromptLLMProvider()
    
    agents = [
        {"role": "qa", "name": "Bob"}
    ]
    
    with patch("core.discussion_room.ProviderFactory.get_provider", return_value=mock_provider):
        await room.run(
            topic="Testing Fallback and Scaffolding",
            agents=agents,
            max_rounds=1
        )
        
        assert len(captured_prompts) >= 1
        qa_prompt = captured_prompts[0]
        
        # Should fallback to default QA persona
        assert "You are a strict QA Auditor Agent" in qa_prompt
        
        # Should automatically scaffold and append QA guide
        assert "SYSTEM SELF-LEARNING DIRECTIVES" in qa_prompt
        assert "Strict QA Auditor Learning Guide" in qa_prompt
        assert "automated validation gates" in qa_prompt


