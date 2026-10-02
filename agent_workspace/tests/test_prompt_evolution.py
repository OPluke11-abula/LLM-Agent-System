import os
import sys
import tempfile
import pytest
from pathlib import Path

# Add project root to sys.path
workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)

from core.prompt_composer import PromptComposer


@pytest.fixture
def temp_workspace():
    """Scaffolds a mock temp workspace with role prompts."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        roles_dir = temp_path / ".agent" / "prompts" / "roles"
        roles_dir.mkdir(parents=True, exist_ok=True)
        
        # Scaffold dev role prompt
        dev_content = (
            "---\n"
            "id: dev\n"
            "role: dev\n"
            "persona: \"You are a highly efficient Dev Agent. You write robust, clean, modular Python.\"\n"
            "version: \"1.0.0\"\n"
            "---\n"
            "Elite Developer Persona.\n"
        )
        (roles_dir / "dev.md").write_text(dev_content, encoding="utf-8")
        yield temp_dir


def test_prompt_optimization_failure(temp_workspace):
    """Verify that PromptComposer correctly appends FailSafe constraints on execution failure."""
    composer = PromptComposer(temp_workspace)
    
    # Run optimization on failure
    success = composer.optimize_role_prompt("dev", execution_efficiency=10.0, token_usage=500, outcome="failure")
    assert success is True
    
    # Reload and verify version incremented
    role_file = Path(composer.prompts_dir) / "roles" / "dev.md"
    content = role_file.read_text(encoding="utf-8")
    assert "version: 1.0.1" in content
    assert "FailSafe constraint" in content
    
    # Verify we can load the persona cleanly
    persona = composer.load_role_persona("dev")
    assert "highly efficient Dev Agent" in persona


def test_prompt_optimization_high_token_usage(temp_workspace):
    """Verify that PromptComposer appends TokenBudget constraints on success with high token consumption."""
    composer = PromptComposer(temp_workspace)
    
    # Run optimization on success with high tokens
    success = composer.optimize_role_prompt("dev", execution_efficiency=10.0, token_usage=60000, outcome="success")
    assert success is True
    
    role_file = Path(composer.prompts_dir) / "roles" / "dev.md"
    content = role_file.read_text(encoding="utf-8")
    assert "version: 1.0.1" in content
    assert "TokenBudget constraint" in content


def test_prompt_optimization_low_efficiency(temp_workspace):
    """Verify that PromptComposer appends Latency constraints on success with low execution efficiency."""
    composer = PromptComposer(temp_workspace)
    
    # Run optimization on success with low efficiency (high latency)
    success = composer.optimize_role_prompt("dev", execution_efficiency=150.0, token_usage=500, outcome="success")
    assert success is True
    
    role_file = Path(composer.prompts_dir) / "roles" / "dev.md"
    content = role_file.read_text(encoding="utf-8")
    assert "version: 1.0.1" in content
    assert "Latency constraint" in content


def test_multiple_optimizations_cumulative(temp_workspace):
    """Verify that multiple optimization rounds result in cumulative constraint updates and version increments."""
    composer = PromptComposer(temp_workspace)
    
    # Round 1: Failure
    composer.optimize_role_prompt("dev", 10.0, 500, "failure")
    
    # Round 2: Success with high tokens
    composer.optimize_role_prompt("dev", 10.0, 60000, "success")
    
    role_file = Path(composer.prompts_dir) / "roles" / "dev.md"
    content = role_file.read_text(encoding="utf-8")
    assert "version: 1.0.2" in content
    assert "FailSafe constraint" in content
    assert "TokenBudget constraint" in content
