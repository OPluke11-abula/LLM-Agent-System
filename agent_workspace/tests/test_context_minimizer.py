import os
import sys
import tempfile
import pytest
from pathlib import Path

# Add project root to sys.path
workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)

from core.log_compactor import ContextMinimizer


@pytest.fixture
def temp_workspace():
    """Scaffolds a mock active workspace with a mix of core code and redundant files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # 1. Create protected directories and files
        agent_dir = temp_path / ".agent"
        agent_dir.mkdir(parents=True, exist_ok=True)
        (agent_dir / "agent.md").write_text("PAP Manifest", encoding="utf-8")
        
        roles_dir = agent_dir / "prompts" / "roles"
        roles_dir.mkdir(parents=True, exist_ok=True)
        (roles_dir / "dev.md").write_text("Developer Persona", encoding="utf-8")
        
        core_dir = temp_path / "agent_workspace" / "core"
        core_dir.mkdir(parents=True, exist_ok=True)
        (core_dir / "discussion_room.py").write_text("class DiscussionRoom: pass", encoding="utf-8")
        
        tests_dir = temp_path / "agent_workspace" / "tests"
        tests_dir.mkdir(parents=True, exist_ok=True)
        (tests_dir / "test_api.py").write_text("def test_api(): pass", encoding="utf-8")
        
        # Core config files in root
        (temp_path / "accounts.json").write_text("{}", encoding="utf-8")
        (temp_path / "config.yaml").write_text("llm: flash", encoding="utf-8")
        (temp_path / "pyproject.toml").write_text("[tool.poetry]", encoding="utf-8")
        
        # 2. Create redundant/obsolete junk files to be pruned
        (temp_path / "handoff.md").write_text("Handoff text", encoding="utf-8")
        (temp_path / "transition_guide.md").write_text("Transition text", encoding="utf-8")
        (temp_path / "debug_run.tmp").write_text("Temp debug content", encoding="utf-8")
        (temp_path / "redundant_log.txt").write_text("Obsolete logs", encoding="utf-8")
        (temp_path / "test_run.log").write_text("Traceback logs", encoding="utf-8")
        (temp_path / "scratch_work.py").write_text("print('test')", encoding="utf-8")
        (temp_path / "manual_test_run.py").write_text("print('manual')", encoding="utf-8")
        (temp_path / "temp_script.py").write_text("print('temp')", encoding="utf-8")
        
        yield temp_dir


def test_context_minimizer_purges_junk_and_protects_core(temp_workspace):
    """Verify that ContextMinimizer successfully prunes obsolete files while keeping core code safe."""
    temp_path = Path(temp_workspace)
    
    # Assert initial file existence
    assert (temp_path / "handoff.md").is_file()
    assert (temp_path / "debug_run.tmp").is_file()
    assert (temp_path / "scratch_work.py").is_file()
    assert (temp_path / "accounts.json").is_file()
    assert (temp_path / ".agent" / "agent.md").is_file()
    assert (temp_path / "agent_workspace" / "core" / "discussion_room.py").is_file()
    assert (temp_path / "agent_workspace" / "tests" / "test_api.py").is_file()
    
    # Run the dejunking engine
    deleted = ContextMinimizer.dejunk_workspace(temp_workspace)
    
    # Verify pruned files
    assert not (temp_path / "handoff.md").is_file()
    assert not (temp_path / "transition_guide.md").is_file()
    assert not (temp_path / "debug_run.tmp").is_file()
    assert not (temp_path / "redundant_log.txt").is_file()
    assert not (temp_path / "test_run.log").is_file()
    assert not (temp_path / "scratch_work.py").is_file()
    assert not (temp_path / "manual_test_run.py").is_file()
    assert not (temp_path / "temp_script.py").is_file()
    
    # Verify exactly 8 files were deleted
    assert len(deleted) == 8
    
    # Verify core files are 100% protected and untouched
    assert (temp_path / "accounts.json").is_file()
    assert (temp_path / "config.yaml").is_file()
    assert (temp_path / "pyproject.toml").is_file()
    assert (temp_path / ".agent" / "agent.md").is_file()
    assert (temp_path / ".agent" / "prompts" / "roles" / "dev.md").is_file()
    assert (temp_path / "agent_workspace" / "core" / "discussion_room.py").is_file()
    assert (temp_path / "agent_workspace" / "tests" / "test_api.py").is_file()
