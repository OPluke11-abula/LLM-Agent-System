import os
import sys
import tempfile
import pytest
import json
import yaml
from pathlib import Path
import jsonschema

# Add project root to sys.path
workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)

from core.engine import AgentEngine
from core.router import AgentRouter


@pytest.fixture
def temp_workspace():
    """Scaffolds a mock temp workspace for skill discovery."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # 1. Create a dummy config.yaml
        config_content = (
            "llm:\n"
            "  provider: google-genai\n"
            "  model: gemini-2.5-flash\n"
            "memory:\n"
            "  long_term_enabled: false\n"
        )
        (temp_path / "config.yaml").write_text(config_content, encoding="utf-8")
        
        # 2. Create agent.jinja2
        (temp_path / "agent.jinja2").write_text("Hello agent", encoding="utf-8")
        
        # 3. Create .agent directory structure
        (temp_path / ".agent").mkdir(parents=True, exist_ok=True)
        (temp_path / "memory").mkdir(parents=True, exist_ok=True)
        
        # 4. Copy spec/skill-contract.schema.json into temp workspace spec directory
        (temp_path / "spec").mkdir(parents=True, exist_ok=True)
        orig_schema = Path(workspace_dir).parent / "spec" / "skill-contract.schema.json"
        
        # Defense in depth: if workspace_dir parent is not the git root, find it
        if not orig_schema.is_file():
            orig_schema = Path(workspace_dir) / "spec" / "skill-contract.schema.json"
            
        (temp_path / "spec" / "skill-contract.schema.json").write_text(
            orig_schema.read_text(encoding="utf-8"),
            encoding="utf-8"
        )
        
        yield temp_dir


def test_dynamic_skill_discovery_and_verification(temp_workspace):
    """Assert that discovered skills validate against JSON schema, register at runtime, and execute cleanly."""
    engine = AgentEngine(temp_workspace)
    router = AgentRouter(engine, session_id="test-discovery-session")
    
    # 1. Valid Skill Contract YAML
    valid_yaml = """
    id: "add_numbers"
    name: "add_numbers"
    description: "Add two numbers together."
    version: "1.0.0"
    inputs:
      x:
        type: "number"
        required: true
        description: "The first number"
      y:
        type: "number"
        required: true
        description: "The second number"
    outputs:
      success:
        type: "string"
        description: "Plain text sum"
      error:
        type: "string"
        description: "String prefixed with Error:"
    safety_notes:
      - "No dangerous system command execution."
    author: "Decentralized Swarm Team"
    """
    
    # Discovery verification
    success = router.discover_skill(valid_yaml)
    assert success is True
    
    # 2. Verify that contract file is saved into .agent/skills/
    contract_file = Path(temp_workspace) / ".agent" / "skills" / "add_numbers.md"
    assert contract_file.is_file()
    content = contract_file.read_text(encoding="utf-8")
    assert "id: add_numbers" in content
    assert "description: Add two numbers together." in content
    
    # 3. Verify hot tool registry registration
    assert "add_numbers" in router.engine.tools_registry
    tool_entry = router.engine.tools_registry["add_numbers"]
    assert tool_entry["description"] == "Add two numbers together."
    assert "x" in tool_entry["schema"]["properties"]
    assert "y" in tool_entry["schema"]["properties"]
    
    # 4. Verify tool execution
    result = router.engine.execute_tool("add_numbers", {"x": 10.5, "y": 20.0})
    assert "Executed discovered skill add_numbers successfully" in result
    assert "Arguments" in result
    assert "10.5" in result
    assert "20.0" in result


def test_invalid_skill_contract_rejection(temp_workspace):
    """Verify that malformed or incomplete tool contracts fail the verification gateway."""
    engine = AgentEngine(temp_workspace)
    router = AgentRouter(engine, session_id="test-discovery-session")
    
    # Incomplete Contract (missing required keys: description and version)
    invalid_yaml = """
    id: "invalid_tool"
    name: "invalid_tool"
    inputs:
      param1:
        type: "string"
        required: false
        description: "A string"
    outputs:
      success:
        type: "string"
        description: "Success format"
      error:
        type: "string"
        description: "Error format"
    safety_notes:
      - "No notes"
    """
    
    # Assert validation error is raised during gateway check
    with pytest.raises(jsonschema.ValidationError):
        router.discover_skill(invalid_yaml)
        
    # Verify that the tool was NOT loaded or written to disk
    assert "invalid_tool" not in router.engine.tools_registry
    contract_file = Path(temp_workspace) / ".agent" / "skills" / "invalid_tool.md"
    assert not contract_file.exists()


def test_skill_discovery_stream_chunk_parsing(temp_workspace):
    """Verify that process_discovered_skill_stream handles stream events cleanly."""
    engine = AgentEngine(temp_workspace)
    router = AgentRouter(engine, session_id="test-discovery-session")
    
    contract_dict = {
        "id": "say_hello",
        "name": "say_hello",
        "description": "Greet a user.",
        "version": "1.0.0",
        "inputs": {
            "name": {
                "type": "string",
                "required": True,
                "description": "The name of the user"
            }
        },
        "outputs": {
            "success": {
                "type": "string",
                "description": "Greeting string"
            },
            "error": {
                "type": "string",
                "description": "Error greeting"
            }
        },
        "safety_notes": ["Always polite."],
        "author": "Stream Discovery"
    }
    
    stream_payload = {
        "type": "discover_skill",
        "contract": contract_dict
    }
    
    # Process stream chunk
    success = router.process_discovered_skill_stream(json.dumps(stream_payload))
    assert success is True
    
    # Tool must be successfully registered in the engine registry
    assert "say_hello" in router.engine.tools_registry
    res = router.engine.execute_tool("say_hello", {"name": "Alice"})
    assert "Executed discovered skill say_hello" in res
    assert "Alice" in res
