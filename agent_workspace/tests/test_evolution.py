import os
import sys
import json
import shutil
import pytest
import asyncio
from unittest.mock import MagicMock
from pathlib import Path

# Add project root parent to sys.path to support agent_workspace.* imports
test_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(test_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# Also add agent_workspace directory for direct core.* imports
workspace_dir = os.path.dirname(test_dir)
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)

from agent_workspace.core.log_compactor import LogCompactor
from agent_workspace.core.prompt_composer import PromptComposer
from agent_workspace.skills.tool_workspace import TaskNode, WorkspaceManager
from agent_workspace.core.workflow_engine import WorkflowEngine, WorkflowRunState, StepState
from agent_workspace.core.engine import AgentEngine

@pytest.fixture
def temp_project_dir(tmp_path):
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()
    (project_dir / ".agent").mkdir()
    (project_dir / ".agent" / "knowledge_base").mkdir()
    (project_dir / ".agent" / "prompts").mkdir()
    (project_dir / ".agent" / "workflows").mkdir()
    (project_dir / "workspace").mkdir()
    return project_dir

def test_log_compaction(temp_project_dir):
    # Setup completed task node with verbose logs
    task = TaskNode("TASK-100", "Implement feature X")
    task.status = "completed"
    task.logs = [
        "- `2026-05-28` Step 1: initial scaffold created.",
        "- `2026-05-28` Step 2: unit tests written.",
        "- `2026-05-28` Step 3: API endpoints exposed.",
        "- `2026-05-28` Step 4: final sweep and clean."
    ]

    tasks_dict = {"TASK-100": task}

    # Run LogCompactor
    res = LogCompactor.compact_milestone(tasks_dict, str(temp_project_dir), "PH12")

    # Verify compaction metrics
    assert res["compacted_count"] == 1
    assert res["reduction_ratio"] >= 0.75

    # Verify archive exists and contains original logs
    archive_file = Path(res["archive_path"])
    assert archive_file.is_file()

    with open(archive_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "TASK-100" in data
    assert len(data["TASK-100"]["original_logs"]) == 4

    # Verify active logs are semantically compressed to 1 summary token
    assert len(task.logs) == 1
    assert "Compacted Milestone PH12" in task.logs[0]


def test_lessons_learned_prompt_composer(temp_project_dir):
    # Write mock lessons learned
    lessons_file = temp_project_dir / ".agent" / "knowledge_base" / "lessons_learned.md"
    lessons_content = """# Lessons Learned Registry
### Lesson ID: L-001
- **Mistake Encountered**: Thread hanging.
- **Best Practice Policy**: Always mock approval checks in pytest.
"""
    lessons_file.write_text(lessons_content, encoding="utf-8")

    # Create a mock prompt template
    prompt_file = temp_project_dir / ".agent" / "prompts" / "hello.md"
    prompt_content = """---
id: hello
template: "Hello, {{ name }}!"
variables:
  - name
version: "1.0.0"
---
Template body
"""
    prompt_file.write_text(prompt_content, encoding="utf-8")

    # Initialize PromptComposer
    composer = PromptComposer(workspace_path=str(temp_project_dir / "workspace"))
    composer.project_root = temp_project_dir
    composer.prompts_dir = temp_project_dir / ".agent" / "prompts"

    # Build prompt
    res = composer.build("hello", {"name": "LAS Dev Team"})

    # Verify dynamic lessons learned directives injection
    assert "Hello, LAS Dev Team!" in res
    assert "SYSTEM SELF-LEARNING DIRECTIVES" in res
    assert "Always mock approval checks in pytest." in res


@pytest.mark.asyncio
async def test_parallel_workflow_concurrency(temp_project_dir):
    # Define a workflow with parallel branching (step_2 and step_3 depend on step_1)
    workflow_file = temp_project_dir / ".agent" / "workflows" / "swarm_flow.md"
    workflow_content = """---
id: swarm_flow
name: Parallel Swarm Workflow
description: Executes parallel tasks concurrently
version: "1.0.0"
steps:
  - step_id: step_1
    skill_id: system_verification
    params: {}
  - step_id: step_2
    skill_id: system_verification
    params: {}
    dependencies: [step_1]
  - step_id: step_3
    skill_id: system_verification
    params: {}
    dependencies: [step_1]
---
"""
    workflow_file.write_text(workflow_content, encoding="utf-8")

    # Mock AgentEngine and execution calls
    engine_mock = MagicMock(spec=AgentEngine)
    engine_mock.workspace_path = str(temp_project_dir / "workspace")
    engine_mock.execute_tool.return_value = '{"status": "ok"}'

    # Initialize WorkflowEngine
    wf_engine = WorkflowEngine(engine_mock)
    wf_engine.workflows_dir = temp_project_dir / ".agent" / "workflows"
    wf_engine.runs_dir = temp_project_dir / ".agent" / "workflows" / "runs"

    # Run the workflow
    res = await wf_engine.execute("swarm_flow", "session-999")

    # Verify outputs
    assert "step_1" in res
    assert "step_2" in res
    assert "step_3" in res
    assert res["step_1"]["status"] == "ok"
    assert res["step_2"]["status"] == "ok"
    assert res["step_3"]["status"] == "ok"


def test_dynamic_log_compaction_threshold(temp_project_dir):
    # Create a task node with logs below threshold
    task_small = TaskNode("TASK-small", "Small task")
    task_small.status = "completed"
    task_small.logs = ["Short log line"]

    tasks_dict = {"TASK-small": task_small}

    # Assert compaction is skipped (threshold = 100 estimated tokens)
    res_skipped = LogCompactor.compact_if_large(tasks_dict, str(temp_project_dir), "session_small", threshold=100)
    assert res_skipped is None

    # Create task node with large logs exceeding threshold
    task_large = TaskNode("TASK-large", "Large task")
    task_large.status = "completed"
    task_large.logs = ["a" * 1000, "b" * 1000]

    tasks_dict_large = {"TASK-large": task_large}

    # Assert compaction triggers
    res_triggered = LogCompactor.compact_if_large(tasks_dict_large, str(temp_project_dir), "session_large", threshold=100)
    assert res_triggered is not None
    assert res_triggered["compacted_count"] == 1


def test_multilanguage_prompt_composer(temp_project_dir):
    # Write lessons learned with French, Japanese and Traditional Chinese policies
    lessons_file = temp_project_dir / ".agent" / "knowledge_base" / "lessons_learned.md"
    lessons_content = """# Lessons Learned Registry
    - **Best Practice Policy**: Policy in English.
    - **最佳實踐**: Policy in Traditional Chinese.
    - **Best Practice**: Policy in Japanese or French.
    """
    lessons_file.write_text(lessons_content, encoding="utf-8")

    prompt_file = temp_project_dir / ".agent" / "prompts" / "translate_test.md"
    prompt_content = """---
id: translate_test
template: "Language Test"
variables: []
version: "1.0.0"
---
Body
"""
    prompt_file.write_text(prompt_content, encoding="utf-8")

    # Initialize PromptComposer
    composer = PromptComposer(workspace_path=str(temp_project_dir / "workspace"))
    composer.project_root = temp_project_dir
    composer.prompts_dir = temp_project_dir / ".agent" / "prompts"

    res = composer.build("translate_test", {})

    # Assert all policy languages are correctly scanned and injected into prompt
    assert "Policy in English." in res
    assert "Policy in Traditional Chinese." in res
    assert "Policy in Japanese or French." in res

