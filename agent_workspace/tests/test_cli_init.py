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

from cli import handle_init


def test_cli_init_dry_run(capsys):
    """Verify that --dry-run outputs details but does not modify the filesystem."""
    with tempfile.TemporaryDirectory() as temp_dir:
        args = MagicMock()
        args.path = temp_dir
        args.dry_run = True
        
        handle_init(args)
        
        captured = capsys.readouterr()
        assert "Dry run active" in captured.out
        assert "[Directory] .agent" in captured.out
        assert "[File]      .agent\\agent.md" in captured.out or "[File]      .agent/agent.md" in captured.out
        assert "AGENTS.md" in captured.out
        assert "state.md" in captured.out
        
        # Verify no files were created
        assert not (Path(temp_dir) / ".agent").exists()


def test_cli_init_success():
    """Verify that executing full init scaffolds all subdirectories and skeletal files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        args = MagicMock()
        args.path = temp_dir
        args.dry_run = False
        
        handle_init(args)
        
        temp_path = Path(temp_dir)
        agent_dir = temp_path / ".agent"
        
        # Verify subdirectories exist
        assert (agent_dir / "evidence").is_dir()
        assert (agent_dir / "patches").is_dir()
        assert (agent_dir / "skills").is_dir()
        assert (agent_dir / "workflows").is_dir()
        
        # Verify manifest files exist
        assert (temp_path / "AGENTS.md").is_file()
        assert (agent_dir / "agent.md").is_file()
        assert (agent_dir / "state.md").is_file()
        assert (agent_dir / "ownership.md").is_file()
        assert (agent_dir / "test_policy.md").is_file()
        assert (agent_dir / "task_environment.json").is_file()
        
        # Verify file content
        agent_content = (agent_dir / "agent.md").read_text(encoding="utf-8")
        assert 'protocol_version: "3.8.0"' in agent_content
        assert 'min_runtime_version: "0.1.0"' in agent_content
        assert 'tools:' in agent_content

        state_content = (agent_dir / "state.md").read_text(encoding="utf-8")
        assert "Protocol Baseline: 3.8.0" in state_content
