import os
import sys
import tempfile
import pytest
from pathlib import Path
from pydantic import BaseModel, Field

# Add project root to sys.path
workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, workspace_dir)

from core.engine import AgentEngine
from core.workflow_engine import WorkflowEngine, WorkflowRunState, StepState


# Define mock models and functions for workflow engine tests
class MockAddArgs(BaseModel):
    a: float
    b: float

def mock_add(args: MockAddArgs):
    return {"result": args.a + args.b}


class MockMultiplyArgs(BaseModel):
    a: float
    b: float

def mock_multiply(args: MockMultiplyArgs):
    return {"result": args.a * args.b}


class MockDivideArgs(BaseModel):
    a: float
    b: float

def mock_divide(args: MockDivideArgs):
    if args.b == 0:
        return "Error: Division by zero is not allowed."
    return {"result": args.a / args.b}


def register_mock_tools(engine: AgentEngine):
    engine.tools_registry["mock_add"] = {
        "function": mock_add,
        "args_model": MockAddArgs,
        "description": "mock add",
        "schema": MockAddArgs.model_json_schema(),
        "wants_context": False,
        "is_markdown_skill": False,
    }
    engine.tools_registry["mock_multiply"] = {
        "function": mock_multiply,
        "args_model": MockMultiplyArgs,
        "description": "mock multiply",
        "schema": MockMultiplyArgs.model_json_schema(),
        "wants_context": False,
        "is_markdown_skill": False,
    }
    engine.tools_registry["mock_divide"] = {
        "function": mock_divide,
        "args_model": MockDivideArgs,
        "description": "mock divide",
        "schema": MockDivideArgs.model_json_schema(),
        "wants_context": False,
        "is_markdown_skill": False,
    }


@pytest.fixture
def mock_workflow_env():
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        pap_dir = temp_path / ".agent"
        workflows_dir = pap_dir / "workflows"
        workflows_dir.mkdir(parents=True, exist_ok=True)
        
        with open(temp_path / "config.yaml", "w", encoding="utf-8") as f:
            f.write("llm:\n  provider: google-genai\n  model: gemini-2.5-flash\n")
            
        yield temp_dir


@pytest.mark.asyncio
async def test_workflow_engine_happy_path(mock_workflow_env):
    temp_path = Path(mock_workflow_env)
    
    workflow_md = """---
id: calc_workflow
name: Calculate Workflow
description: A mock workflow that runs calculations
version: 1.0.0
steps:
  - step_id: step_1
    skill_id: mock_add
    params:
      a: 10
      b: 20
    next_step: step_2
  - step_id: step_2
    skill_id: mock_multiply
    params:
      a: "{{steps.step_1.output.result}}"
      b: 2
    next_step: null
---
# Calculate Workflow Markdown Body
"""
    workflow_file = temp_path / ".agent" / "workflows" / "calc_workflow.md"
    workflow_file.parent.mkdir(parents=True, exist_ok=True)
    workflow_file.write_text(workflow_md, encoding="utf-8")
    
    real_engine = AgentEngine(workspace_path=workspace_dir)
    register_mock_tools(real_engine)
    
    workflow_engine = WorkflowEngine(real_engine)
    workflow_engine.workflows_dir = temp_path / ".agent" / "workflows"
    workflow_engine.runs_dir = workflow_engine.workflows_dir / "runs"
    workflow_engine.runs_dir.mkdir(parents=True, exist_ok=True)
    
    results = await workflow_engine.execute(
        workflow_id="calc_workflow",
        session_id="session-happy-1",
        payload={}
    )
    
    assert "step_1" in results
    assert "step_2" in results
    
    assert results["step_1"]["result"] == 30.0
    assert results["step_2"]["result"] == 60.0
    
    state = workflow_engine.load_state("session-happy-1")
    assert state is not None
    assert state.status == "success"
    assert state.steps["step_1"].status == "success"
    assert state.steps["step_2"].status == "success"


@pytest.mark.asyncio
async def test_workflow_engine_branching_and_skip(mock_workflow_env):
    temp_path = Path(mock_workflow_env)
    
    workflow_md = """---
id: branch_workflow
name: Branching Workflow
description: A mock workflow that branches and skips
version: 1.0.0
steps:
  - step_id: check_step
    skill_id: mock_add
    params:
      a: 5
      b: 5
    next_step: "{{ 'branch_a' if steps.check_step.output.result > 5 else 'branch_b' }}"
  - step_id: branch_a
    skill_id: mock_multiply
    params:
      a: 10
      b: 10
    next_step: null
  - step_id: branch_b
    skill_id: mock_add
    params:
      a: 1
      b: 1
    next_step: null
---
"""
    workflow_file = temp_path / ".agent" / "workflows" / "branch_workflow.md"
    workflow_file.write_text(workflow_md, encoding="utf-8")
    
    real_engine = AgentEngine(workspace_path=workspace_dir)
    register_mock_tools(real_engine)
    
    workflow_engine = WorkflowEngine(real_engine)
    workflow_engine.workflows_dir = temp_path / ".agent" / "workflows"
    workflow_engine.runs_dir = workflow_engine.workflows_dir / "runs"
    workflow_engine.runs_dir.mkdir(parents=True, exist_ok=True)
    
    results = await workflow_engine.execute("branch_workflow", "session-branch-1")
    
    assert results["check_step"]["result"] == 10.0
    assert results["branch_a"]["result"] == 100.0
    assert "branch_b" not in results
    
    state = workflow_engine.load_state("session-branch-1")
    assert state.steps["check_step"].status == "success"
    assert state.steps["branch_a"].status == "success"
    assert state.steps["branch_b"].status == "pending"


@pytest.mark.asyncio
async def test_workflow_engine_on_failure_policies(mock_workflow_env):
    temp_path = Path(mock_workflow_env)
    
    workflow_md = """---
id: fail_workflow
name: Fail Policy Workflow
description: Tests error strategies
version: 1.0.0
steps:
  - step_id: fail_skip_step
    skill_id: mock_divide
    params:
      a: 10
      b: 0
    on_failure: skip
    next_step: fail_fallback_step
  - step_id: fail_fallback_step
    skill_id: mock_divide
    params:
      a: 1
      b: 0
    on_failure: fallback
    fallback_step: recover_step
    next_step: null
  - step_id: recover_step
    skill_id: mock_add
    params:
      a: 1
      b: 1
    next_step: null
---
"""
    workflow_file = temp_path / ".agent" / "workflows" / "fail_workflow.md"
    workflow_file.write_text(workflow_md, encoding="utf-8")
    
    real_engine = AgentEngine(workspace_path=workspace_dir)
    register_mock_tools(real_engine)
    
    workflow_engine = WorkflowEngine(real_engine)
    workflow_engine.workflows_dir = temp_path / ".agent" / "workflows"
    workflow_engine.runs_dir = workflow_engine.workflows_dir / "runs"
    workflow_engine.runs_dir.mkdir(parents=True, exist_ok=True)
    
    results = await workflow_engine.execute("fail_workflow", "session-fail-1")
    
    state = workflow_engine.load_state("session-fail-1")
    assert state.status == "success"
    assert state.steps["fail_skip_step"].status == "skipped"
    assert state.steps["fail_fallback_step"].status == "failed"
    assert state.steps["recover_step"].status == "success"
    assert results["recover_step"]["result"] == 2.0


@pytest.mark.asyncio
async def test_workflow_engine_checkpoint_resume(mock_workflow_env):
    temp_path = Path(mock_workflow_env)
    
    # Setup workflow where step 2 fails first time (division by zero), but will be fixed and resumed!
    workflow_md_failed = """---
id: resume_workflow
name: Checkpoint Resume Workflow
description: Tests resuming after fix
version: 1.0.0
steps:
  - step_id: step_1
    skill_id: mock_add
    params:
      a: 5
      b: 5
    next_step: step_2
  - step_id: step_2
    skill_id: mock_divide
    params:
      a: 10
      b: 0
    on_failure: fail
    next_step: step_3
  - step_id: step_3
    skill_id: mock_multiply
    params:
      a: "{{steps.step_2.output.result}}"
      b: 10
    next_step: null
---
"""
    workflow_file = temp_path / ".agent" / "workflows" / "resume_workflow.md"
    workflow_file.write_text(workflow_md_failed, encoding="utf-8")
    
    real_engine = AgentEngine(workspace_path=workspace_dir)
    register_mock_tools(real_engine)
    
    workflow_engine = WorkflowEngine(real_engine)
    workflow_engine.workflows_dir = temp_path / ".agent" / "workflows"
    workflow_engine.runs_dir = workflow_engine.workflows_dir / "runs"
    workflow_engine.runs_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Run and expect failure on step_2
    with pytest.raises(RuntimeError) as excinfo:
        await workflow_engine.execute("resume_workflow", "session-resume-1")
    assert "Division by zero" in str(excinfo.value) or "step failed" in str(excinfo.value)
    
    # Verify state shows failed
    state = workflow_engine.load_state("session-resume-1")
    assert state.status == "failed"
    assert state.steps["step_1"].status == "success"
    assert state.steps["step_2"].status == "failed"
    assert state.steps["step_3"].status == "pending"
    
    # 2. "Fix" the workflow file (change division by zero to division by 2)
    workflow_md_fixed = """---
id: resume_workflow
name: Checkpoint Resume Workflow
description: Tests resuming after fix
version: 1.0.0
steps:
  - step_id: step_1
    skill_id: mock_add
    params:
      a: 5
      b: 5
    next_step: step_2
  - step_id: step_2
    skill_id: mock_divide
    params:
      a: 10
      b: 2
    on_failure: fail
    next_step: step_3
  - step_id: step_3
    skill_id: mock_multiply
    params:
      a: "{{steps.step_2.output.result}}"
      b: 10
    next_step: null
---
"""
    workflow_file.write_text(workflow_md_fixed, encoding="utf-8")
    
    # 3. Resume the execution!
    results = await workflow_engine.execute("resume_workflow", "session-resume-1", resume=True)
    
    # Should continue from step_2, not rerun step_1 (step_1 results are carried over)
    state = workflow_engine.load_state("session-resume-1")
    assert state.status == "success"
    assert state.steps["step_1"].status == "success"
    assert state.steps["step_2"].status == "success"
    assert state.steps["step_3"].status == "success"
    
    assert results["step_2"]["result"] == 5.0
    assert results["step_3"]["result"] == 50.0
