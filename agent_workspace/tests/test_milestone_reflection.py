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
from core.log_compactor import LogCompactor
from core.providers import ProviderResponse


@pytest.fixture
def anyio_backend():
    return "asyncio"


class MockLLMProvider:
    """Mock LLM Provider returning role-based responses for reflection debate."""
    async def complete(self, system_prompt, messages, tool_schemas, config):
        user_content = messages[0]["content"] if messages else ""
        system_lower = system_prompt.lower()
        
        if "moderator" in system_lower or "synthesize" in user_content.lower():
            return ProviderResponse("text", (
                "# Milestone Learning Report\n\n"
                "## 1. Performance Gaps / 效能差距分析\n"
                "- High latency observed in external tool execution.\n\n"
                "## 2. Budget Consumption Audits / 預算消費審計\n"
                "- Token usage is within normal limits. Cumulative cost: $0.15.\n\n"
                "## 3. Prompt Refactoring Suggestions / 提示詞重構建議\n"
                "- Add latency alerts to Developer system prompt."
            ))
        elif "ceo" in system_lower:
            return ProviderResponse("text", "CEO: Strategic alignment was successful.")
        elif "cto" in system_lower:
            return ProviderResponse("text", "CTO: Architectural decoupling was effective.")
        elif "dev" in system_lower:
            return ProviderResponse("text", "Dev: AST checking prevented critical security breaches.")
        elif "qa" in system_lower:
            return ProviderResponse("text", "QA: Automated test gates prevented regression leaks.")
        elif "cfo" in system_lower:
            return ProviderResponse("text", "CFO: Dynamic budget enforcement kept execution under cost caps.")
            
        return ProviderResponse("text", "Generic reflection contribution")


@pytest.fixture
def mock_reflection_env():
    """Create a temporary environment with accounts.json and .agent directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Scaffold .agent/knowledge_base/ directories
        kb_dir = temp_path / ".agent" / "knowledge_base"
        kb_dir.mkdir(parents=True, exist_ok=True)
        
        # Scaffold accounts.json
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


class MockTask:
    def __init__(self, task_id: str, title: str, status: str, description: str, logs: list[str]):
        self.task_id = task_id
        self.title = title
        self.status = status
        self.description = description
        self.logs = logs

    def to_dict(self) -> dict:
        return {
            "id": self.task_id,
            "title": self.title,
            "status": self.status,
            "description": self.description,
            "logs": self.logs
        }


@pytest.mark.anyio
async def test_run_milestone_reflection_explicit(mock_reflection_env):
    """Verify that run_milestone_reflection triggers the multi-role debate and registers the report."""
    room = DiscussionRoom(workspace_path=mock_reflection_env)
    
    tasks_dict = {
        "TASK-001": MockTask(
            task_id="TASK-001",
            title="Implement code generation",
            status="completed",
            description="Autonomous AST-audited tools code generation",
            logs=["Step 1 started", "AST validation passed", "Pytest gate passed"]
        )
    }
    
    mock_provider = MockLLMProvider()
    with patch("core.discussion_room.ProviderFactory.get_provider", return_value=mock_provider):
        report = await room.run_milestone_reflection(
            milestone_id="PH21",
            tasks_dict=tasks_dict
        )
        
        # Assert debate was executed and consensus report generated
        assert report is not None
        assert "# Milestone Learning Report" in report
        assert "Performance Gaps" in report
        assert "Budget Consumption" in report
        assert "Prompt Refactoring" in report
        
        # Assert file was written to .agent/knowledge_base/milestone_learning_report.md
        temp_path = Path(mock_reflection_env)
        report_file = temp_path / ".agent" / "knowledge_base" / "milestone_learning_report.md"
        assert report_file.is_file()
        report_content = report_file.read_text(encoding="utf-8")
        assert "latency alerts to Developer" in report_content
        
        # Assert index.json registration
        index_file = temp_path / ".agent" / "knowledge_base" / "index.json"
        assert index_file.is_file()
        index_data = json.loads(index_file.read_text(encoding="utf-8"))
        assert index_data["schema_version"] == "1.0.0"
        
        docs = index_data["documents"]
        assert len(docs) >= 1
        reflection_doc = next(d for d in docs if d["id"] == "milestone_learning_report")
        assert reflection_doc["title"] == "Milestone Learning Report"
        assert reflection_doc["file_path"] == ".agent/knowledge_base/milestone_learning_report.md"
        assert "reflection" in reflection_doc["tags"]


@pytest.mark.anyio
async def test_compaction_auto_triggers_reflection(mock_reflection_env):
    """Verify that compact_milestone automatically schedules and triggers milestone reflection."""
    tasks_dict = {
        "TASK-002": MockTask(
            task_id="TASK-002",
            title="Auto-Healing Swarms",
            status="completed",
            description="Self-healing exception catching mechanisms",
            logs=["Executed task", "Compaction scheduled"]
        )
    }
    
    import asyncio
    mock_provider = MockLLMProvider()
    with patch("core.discussion_room.ProviderFactory.get_provider", return_value=mock_provider), \
         patch("core.discussion_room.DiscussionRoom._delegate_turn_to_microservice", return_value=None):
        # Trigger compaction, which should automatically schedule and run the reflection debate synchronously in test
        compaction_res = LogCompactor.compact_milestone(
            tasks_dict=tasks_dict,
            project_root=mock_reflection_env,
            milestone_id="PH21-AUTO"
        )
        
        assert compaction_res is not None
        assert compaction_res["compacted_count"] == 1
        
        # Yield control to allow background task to run while patch is active
        # Wait dynamically up to 15 seconds for the report file to be written
        temp_path = Path(mock_reflection_env)
        report_file = temp_path / ".agent" / "knowledge_base" / "milestone_learning_report.md"
        for _ in range(150):
            if report_file.is_file():
                break
            await asyncio.sleep(0.1)
        assert report_file.is_file()
        
        index_file = temp_path / ".agent" / "knowledge_base" / "index.json"
        assert index_file.is_file()
        index_data = json.loads(index_file.read_text(encoding="utf-8"))
        assert any(d["id"] == "milestone_learning_report" for d in index_data["documents"])
