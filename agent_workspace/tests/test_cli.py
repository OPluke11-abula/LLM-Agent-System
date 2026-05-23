import os
import sys
import tempfile
import json
import pytest
from pathlib import Path
import subprocess

# Add project root to sys.path
workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, workspace_dir)

from cli import main as cli_main


@pytest.fixture
def mock_cli_env():
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        # Create standard PAP structure for validation
        pap_dir = temp_path / ".agent"
        pap_dir.mkdir(parents=True, exist_ok=True)
        (pap_dir / "skills").mkdir(parents=True, exist_ok=True)
        
        # Create dummy agent.md
        with open(pap_dir / "agent.md", "w", encoding="utf-8") as f:
            f.write("""---
protocol_version: "1.0.0"
min_runtime_version: "0.1.0"
name: test-agent
version: "0.1.0"
purpose: "test"
language: "en"
authorization_level: "interactive-approval"
use_case_tags:
  - test
tools:
  - calculate
---
""")
            
        # Create dummy skills.md and other required files
        (pap_dir / "README.md").write_text("README", encoding="utf-8")
        (pap_dir / "skills.md").write_text("skills", encoding="utf-8")
        (pap_dir / "prompts.md").write_text("prompts", encoding="utf-8")
        (pap_dir / "memory.md").write_text("memory", encoding="utf-8")
        (pap_dir / "workflows.md").write_text("workflows", encoding="utf-8")
        
        # Create dummy calculate.md contract
        with open(pap_dir / "skills" / "calculate.md", "w", encoding="utf-8") as f:
            f.write("""---
id: calculate
description: calculate
version: 1.0.0
inputs:
  operation:
    type: string
    required: true
    description: op
outputs:
  result: res
safety_notes: []
version: 1.0.0
---
""")
            
        yield temp_dir


def test_cli_list_skills(capsys, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["cli.py", "--list-skills"])
    cli_main()
    captured = capsys.readouterr()
    assert "Skill ID" in captured.out
    assert "calculate" in captured.out


def test_cli_describe_skill(capsys, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["cli.py", "--describe-skill", "calculate"])
    cli_main()
    captured = capsys.readouterr()
    assert "id: calculate" in captured.out or "description" in captured.out


def test_cli_validate(capsys, monkeypatch, mock_cli_env):
    # For validate, it uses Path(workspace).parent
    # We patch project_root resolution inside handle_validate
    import cli
    monkeypatch.setattr(cli, "workspace", os.path.join(mock_cli_env, "agent_workspace"))
    monkeypatch.setattr(sys, "argv", ["cli.py", "--validate"])
    
    # Make sure agent_workspace dir exists inside temp folder
    os.makedirs(os.path.join(mock_cli_env, "agent_workspace"), exist_ok=True)
    
    cli_main()
    captured = capsys.readouterr()
    assert "PAP workspace valid" in captured.out


def test_cli_memory_operations(capsys, monkeypatch, tmp_path):
    # Set custom memory dir
    mem_dir = str(tmp_path / "memory")
    
    # 1. Write memory
    monkeypatch.setattr(sys, "argv", [
        "cli.py", 
        "--memory-dir", mem_dir, 
        "--session", "cli-test-session", 
        "--memory-write", "sem-test-1", "This is a CLI memory test"
    ])
    cli_main()
    captured = capsys.readouterr()
    assert "Successfully wrote memory record 'sem-test-1'" in captured.out
    
    # 2. Read memory
    monkeypatch.setattr(sys, "argv", [
        "cli.py", 
        "--memory-dir", mem_dir, 
        "--session", "cli-test-session", 
        "--memory-read", "sem-test-1"
    ])
    cli_main()
    captured = capsys.readouterr()
    
    # Check that record JSON is printed
    assert "sem-test-1" in captured.out
    assert "This is a CLI memory test" in captured.out


def test_cli_run_workflow(capsys, monkeypatch, tmp_path):
    # Setup temp workflow
    workflow_md = """---
id: cli_wf
name: CLI Workflow
description: A mock workflow for CLI testing
version: 1.0.0
steps:
  - step_id: step_1
    skill_id: calculate
    params:
      operation: add
      a: 10
      b: 10
    next_step: null
---
"""
    # Override workspace and workflows dir
    import cli
    monkeypatch.setattr(cli, "workspace", workspace_dir)
    
    # We create the workflow in our temporary workflow dir
    wf_dir = tmp_path / ".agent" / "workflows"
    wf_dir.mkdir(parents=True, exist_ok=True)
    (wf_dir / "cli_wf.md").write_text(workflow_md, encoding="utf-8")
    
    # Patch WorkflowEngine workflows_dir and runs_dir
    from core.workflow_engine import WorkflowEngine
    old_init = WorkflowEngine.__init__
    
    def mock_init(self, engine):
        old_init(self, engine)
        self.workflows_dir = wf_dir
        self.runs_dir = wf_dir / "runs"
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        
    monkeypatch.setattr(WorkflowEngine, "__init__", mock_init)
    
    monkeypatch.setattr(sys, "argv", [
        "cli.py", 
        "--session", "cli-wf-session", 
        "--run-workflow", "cli_wf"
    ])
    
    cli_main()
    captured = capsys.readouterr()
    assert "Executing workflow 'cli_wf'" in captured.out
    assert "Workflow executed successfully!" in captured.out
    assert "step_1" in captured.out
