import os
import sys
import tempfile
import pytest
import json
from pathlib import Path

# Add project root to sys.path
workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)

from long_term_memory import LongTermMemoryStore, EpisodicSummarizer


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def temp_workspace():
    """Scaffolds a mock temp workspace with an agent folder structure."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        agent_dir = temp_path / ".agent" / "knowledge_base"
        agent_dir.mkdir(parents=True, exist_ok=True)
        
        # Scaffold an initial lessons_learned.md registry
        lessons_content = (
            "# 🎓 FindAi Studio LAS Self-Learning Experience & Lessons Learned Registry\n\n"
            "This database catalogs engineering resolutions, compile-time errors, and dynamic swarms refactoring choices.\n\n"
            "---\n\n"
            "## ⚡ 1. Active Resolution Directory (Lessons Database)\n\n"
            "### Lesson ID: L-20260528-001 (Task Mocking Deadlocks)\n"
            "- **Mistake Encountered**: Async pytest suites hanging indefinitely.\n"
            "- **Root Cause**: The router was requesting approval blocking standard CLI.\n"
            "- **Resolution Code**:\n"
            "  ```python\n"
            "  router._get_authorization_level = MagicMock(return_value=\"standard\")\n"
            "  ```\n"
            "- **Best Practice Policy**: Always mock approval checks.\n"
        )
        (agent_dir / "lessons_learned.md").write_text(lessons_content, encoding="utf-8")
        
        yield temp_dir


def test_episodic_summarizer_error_compilation_and_duplicate_free_merge(temp_workspace):
    """Verify that EpisodicSummarizer correctly compiles raw traceback logs, filters clean records, and merges duplicates safely."""
    temp_path = Path(temp_workspace)
    
    # 1. Create a successful memory record (should compile to None)
    clean_record = {
        "id": "ltm-clean123",
        "session_id": "session-success-1",
        "created_at": "2026-05-31T21:51:28",
        "summary": "Step finished successfully. Scaled model parameters and executed validation gate.",
        "payload": {"messages": [{"user": "hello", "assistant": "hi"}]},
        "domain": "episodic"
    }
    lesson_clean = EpisodicSummarizer.compile_lesson(clean_record)
    assert lesson_clean is None
    
    # 2. Create a failed memory record with an SQLite locked traceback (should compile)
    fail_record = {
        "id": "ltm-fail567",
        "session_id": "session-fail-2",
        "created_at": "2026-05-31T21:51:28",
        "summary": "Exception raised during task execution: sqlite3.OperationalError: database is locked",
        "payload": {
            "error": "sqlite3.OperationalError: database is locked",
            "messages": []
        },
        "domain": "episodic"
    }
    lesson_fail = EpisodicSummarizer.compile_lesson(fail_record)
    assert lesson_fail is not None
    assert lesson_fail["lesson_id"] == "L-20260531-FAIL567"
    assert "sqlite3.OperationalError: database is locked" in lesson_fail["mistake"]
    assert "SQLite database lock concurrent write race condition" in lesson_fail["root_cause"]
    assert "MemoryBackend" in lesson_fail["resolution_code"]
    assert "serial execution" in lesson_fail["best_practice"]
    
    # 3. Merge compiled lesson into the registry
    merged_count = EpisodicSummarizer.merge_lessons(temp_workspace, [lesson_fail])
    assert merged_count == 1
    
    # Read modified file and assert the lesson block exists
    lessons_file = temp_path / ".agent" / "knowledge_base" / "lessons_learned.md"
    content = lessons_file.read_text(encoding="utf-8")
    assert "Lesson ID: L-20260531-FAIL567" in content
    assert "sqlite3.OperationalError: database is locked" in content
    
    # 4. Try merging the same lesson again (duplicate check must trigger and skip)
    second_merge = EpisodicSummarizer.merge_lessons(temp_workspace, [lesson_fail])
    assert second_merge == 0
    
    # Verify that the lesson ID only appears once in the file to guarantee duplicate-free sync
    occurrences = len(content.split("Lesson ID: L-20260531-FAIL567")) - 1
    assert occurrences == 1
