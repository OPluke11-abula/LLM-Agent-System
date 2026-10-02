import os
import sys
import tempfile
import shutil
import pytest

workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, workspace_dir)

from core.engine import AgentEngine
from core.router import AgentRouter, ToolValidationError


def test_router_validation_loading():
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a mock .agent directory structure
        pap_dir = os.path.join(temp_dir, ".agent")
        skills_dir = os.path.join(pap_dir, "skills")
        os.makedirs(skills_dir)
        
        # Create config.yaml
        with open(os.path.join(temp_dir, "config.yaml"), "w", encoding="utf-8") as f:
            f.write("llm:\n  provider: google-genai\n  model: gemini-2.5-flash\n")
            
        # Create a mock skill contract
        mock_skill_md = os.path.join(skills_dir, "mock_skill.md")
        with open(mock_skill_md, "w", encoding="utf-8") as f:
            f.write("""---
id: mock_skill
description: A mock skill for testing.
version: 1.0.0
inputs:
  name:
    type: string
    required: true
    description: User name
  age:
    type: integer
    required: false
    description: User age
outputs:
  result: A string.
---
# mock_skill
""")

        engine = AgentEngine(workspace_path=temp_dir)
        router = AgentRouter(engine=engine, session_id="test-session")
        try:
            # Test list_skills
            skills = router.list_skills()
            assert len(skills) == 1
            assert skills[0]["id"] == "mock_skill"
            
            # Test describe_skill
            desc = router.describe_skill("mock_skill")
            assert desc["id"] == "mock_skill"
            assert desc["inputs"]["name"]["required"] is True
            
            # Test describe_skill not found
            with pytest.raises(FileNotFoundError):
                router.describe_skill("non_existent")
                
            # Test validate_call success
            router.validate_call("mock_skill", {"name": "Alice", "age": 30})
            router.validate_call("mock_skill", {"name": "Bob"})
            
            # Test validate_call missing required parameter
            with pytest.raises(ToolValidationError) as excinfo:
                router.validate_call("mock_skill", {"age": 25})
            assert "name" in str(excinfo.value)
            
            # Test validate_call type mismatch
            with pytest.raises(ToolValidationError) as excinfo:
                router.validate_call("mock_skill", {"name": 123})
            assert "name" in str(excinfo.value)
        finally:
            router.close()


def test_router_validation_with_real_skills():
    # Use the real repository structure for this test
    # Find the repository root
    repo_root = os.path.dirname(workspace_dir)
    engine = AgentEngine(workspace_path=workspace_dir)
    router = AgentRouter(engine=engine, session_id="test-session")
    
    # Check that calculate skill exists and describes properly
    desc = router.describe_skill("calculate")
    assert desc["id"] == "calculate"
    assert desc["inputs"]["operation"]["required"] is True
    
    # Valid call parameters
    router.validate_call("calculate", {"operation": "add", "a": 10.5, "b": 20})
    
    # Missing operation
    with pytest.raises(ToolValidationError) as excinfo:
        router.validate_call("calculate", {"a": 1, "b": 2})
    assert "operation" in str(excinfo.value)
    
    # Type mismatch for a (should be number)
    with pytest.raises(ToolValidationError) as excinfo:
        router.validate_call("calculate", {"operation": "add", "a": "not-a-number", "b": 2})
    assert "a" in str(excinfo.value)
