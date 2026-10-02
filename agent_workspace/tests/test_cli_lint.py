import os
import sys
import tempfile
import pytest
from pathlib import Path
from unittest.mock import MagicMock

# Add project root to sys.path
workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)

from cli import handle_init, handle_lint


@pytest.fixture
def clean_skeletal_env():
    """Scaffold a valid clean skeletal environment."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # 1. Bootstrap skeletal structure
        args_init = MagicMock()
        args_init.path = temp_dir
        args_init.dry_run = False
        handle_init(args_init)
        
        yield temp_dir


def test_cli_lint_happy_path(clean_skeletal_env):
    """Verify that a compliant bootstrapped workspace outputs zero errors."""
    args_lint = MagicMock()
    args_lint.path = clean_skeletal_env
    args_lint.fix = False
    
    # Executing lint should print success and exit normally
    handle_lint(args_lint)


def test_cli_lint_missing_keys(clean_skeletal_env):
    """Verify that missing required keys in agent.md are caught."""
    agent_md_path = Path(clean_skeletal_env) / ".agent" / "agent.md"
    
    # Write a manifest missing 'tools' and 'purpose'
    bad_manifest = """---
protocol_version: "1.0.0"
min_runtime_version: "0.1.0"
name: skeletal-agent
version: "1.0.0"
language: en
authorization_level: interactive-approval
use_case_tags:
  - template
---
Missing details
"""
    agent_md_path.write_text(bad_manifest, encoding="utf-8")
    
    args_lint = MagicMock()
    args_lint.path = clean_skeletal_env
    args_lint.fix = False
    
    with pytest.raises(SystemExit) as excinfo:
        handle_lint(args_lint)
        
    assert excinfo.value.code == 1


def test_cli_lint_invalid_semver(clean_skeletal_env):
    """Verify that malformed semver strings raise lint errors."""
    agent_md_path = Path(clean_skeletal_env) / ".agent" / "agent.md"
    
    # Write version as "1.0" (invalid, missing patch version)
    bad_manifest = """---
protocol_version: "1.0.0"
min_runtime_version: "0.1"
name: skeletal-agent
version: "1.0"
purpose: skeletal
description: template
language: en
authorization_level: interactive-approval
use_case_tags:
  - template
tools:
  - calculate
---
"""
    agent_md_path.write_text(bad_manifest, encoding="utf-8")
    
    args_lint = MagicMock()
    args_lint.path = clean_skeletal_env
    args_lint.fix = False
    
    with pytest.raises(SystemExit) as excinfo:
        handle_lint(args_lint)
        
    assert excinfo.value.code == 1


def test_cli_lint_workflow_broken_references(clean_skeletal_env):
    """Verify that workflows containing undeclared tools or invalid next_steps are caught."""
    agent_path = Path(clean_skeletal_env) / ".agent"
    
    # Create workflow file with undeclared skill reference and broken next_step
    bad_workflow = """---
id: test_workflow
name: Broken Workflow
description: Testing validation
version: 1.0.0
steps:
  - step_id: start_step
    skill_id: nonexistent_skill
    params: {}
    next_step: broken_next
  - step_id: finish_step
    skill_id: calculate
    params: {}
---
"""
    (agent_path / "workflows" / "test_workflow.md").write_text(bad_workflow, encoding="utf-8")
    
    args_lint = MagicMock()
    args_lint.path = clean_skeletal_env
    args_lint.fix = False
    
    with pytest.raises(SystemExit) as excinfo:
        handle_lint(args_lint)
        
    assert excinfo.value.code == 1


def test_cli_lint_orphan_contract_warning(clean_skeletal_env, capsys):
    """Verify that orphan skill contracts display warnings but do not force exit."""
    agent_path = Path(clean_skeletal_env) / ".agent"
    
    # Create an orphan contract under skills/ (not in tools)
    orphan_content = """---
id: orphan_skill
description: Orphan
version: 1.0.0
inputs: {}
outputs:
  success: OK
  error: ERR
safety_notes:
  - Safe
---
"""
    (agent_path / "skills" / "orphan_skill.md").write_text(orphan_content, encoding="utf-8")
    
    args_lint = MagicMock()
    args_lint.path = clean_skeletal_env
    args_lint.fix = False
    
    # Run lint, should output a WARNING and succeed since orphan is a warning, not an exit-blocking error
    handle_lint(args_lint)
    captured = capsys.readouterr()
    assert "WARNING: Orphan contract" in captured.out
