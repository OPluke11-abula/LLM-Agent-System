import os
import sys
import tempfile
import pytest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

# Add project root to sys.path
workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, workspace_dir)

from core.engine import AgentEngine
from core.workflow_engine import WorkflowEngine
from pydantic import BaseModel

# Mock tools
class MockDivideArgs(BaseModel):
    a: float
    b: float

def mock_divide(args: MockDivideArgs):
    if args.b == 0:
        raise ValueError("Division by zero is forbidden.")
    return {"result": args.a / args.b}

@pytest.fixture
def mock_workflow_env():
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        pap_dir = temp_path / ".agent"
        workflows_dir = pap_dir / "workflows"
        workflows_dir.mkdir(parents=True, exist_ok=True)
        
        # Write config.yaml
        with open(temp_path / "config.yaml", "w", encoding="utf-8") as f:
            f.write("llm:\n  provider: google-genai\n  model: gemini-2.5-flash\n")
            
        yield temp_dir

@pytest.mark.asyncio
async def test_self_healing_success(mock_workflow_env):
    temp_path = Path(mock_workflow_env)
    
    # Define a workflow with an initially failing step (division by zero)
    workflow_md = """---
id: healing_workflow
name: Healing Workflow
description: Test self healing
version: 1.0.0
steps:
  - step_id: step_1
    skill_id: mock_divide
    params:
      a: 10
      b: 0
    on_failure: fail
    next_step: null
---
"""
    workflow_file = temp_path / ".agent" / "workflows" / "healing_workflow.md"
    workflow_file.write_text(workflow_md, encoding="utf-8")
    
    # Initialize real engine and register tool
    real_engine = AgentEngine(workspace_path=workspace_dir)
    real_engine.tools_registry["mock_divide"] = {
        "function": mock_divide,
        "args_model": MockDivideArgs,
        "description": "mock divide",
        "schema": MockDivideArgs.model_json_schema(),
        "wants_context": False,
        "is_markdown_skill": False,
    }
    
    workflow_engine = WorkflowEngine(real_engine)
    workflow_engine.workflows_dir = temp_path / ".agent" / "workflows"
    workflow_engine.runs_dir = workflow_engine.workflows_dir / "runs"
    workflow_engine.runs_dir.mkdir(parents=True, exist_ok=True)
    
    # Mock LLM provider for self-healing correction call
    mock_provider = AsyncMock()
    # Self-healing call returns patched params: {"a": 10, "b": 2}
    mock_provider.complete.return_value = ("success", '{"a": 10, "b": 2}')
    
    # Patch ProviderFactory
    from core.providers import ProviderFactory
    original_get_provider = ProviderFactory.get_provider
    ProviderFactory.get_provider = MagicMock(return_value=mock_provider)
    
    try:
        results = await workflow_engine.execute(
            workflow_id="healing_workflow",
            session_id="session-healing-1",
            payload={}
        )
        
        # Verify the division succeeded on retry using patched parameters!
        assert "step_1" in results
        assert results["step_1"]["result"] == 5.0
        
        state = workflow_engine.load_state("session-healing-1")
        assert state is not None
        assert state.status == "success"
        assert state.steps["step_1"].status == "success"
        
        # Assert provider complete was called for the healing diagnostic
        mock_provider.complete.assert_called()
    finally:
        ProviderFactory.get_provider = original_get_provider
