import os
import sys
import tempfile
import pytest
import warnings
from unittest.mock import MagicMock, patch
from pathlib import Path

# Add project root to sys.path
workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)

from core.engine import AgentEngine

def test_agent_engine_pap_loading():
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a .agent directory
        pap_dir = os.path.join(temp_dir, ".agent")
        os.makedirs(pap_dir)
        
        # Create agent.md
        agent_md = os.path.join(pap_dir, "agent.md")
        with open(agent_md, "w", encoding="utf-8") as f:
            f.write("""---
name: programmer-agent
description: A developer agent.
---
# Programmer Persona Details
- Coding skills: Python, JavaScript.
""")

        # Create agent_tasks.md
        tasks_md = os.path.join(pap_dir, "agent_tasks.md")
        with open(tasks_md, "w", encoding="utf-8") as f:
            f.write("""---
name: test-tasks
description: Tasks queue.
---
# Task Queue
- [ ] Task 1
- [x] Task 2
""")

        # Instantiate engine
        engine = AgentEngine(workspace_path=temp_dir)
        
        # Verify knowledge contexts
        contexts = engine.knowledge_contexts
        
        # Find programmer-agent
        agent_ctx = next((c for c in contexts if c["name"] == "programmer-agent"), None)
        assert agent_ctx is not None
        assert "A developer agent." in agent_ctx["description"]
        assert "Programmer Persona Details" in agent_ctx["content"]
        
        # Find test-tasks
        tasks_ctx = next((c for c in contexts if c["name"] == "test-tasks"), None)
        assert tasks_ctx is not None
        assert "Tasks queue." in tasks_ctx["description"]
        assert "Task Queue" in tasks_ctx["content"]


def test_agent_engine_version_mismatches():
    with tempfile.TemporaryDirectory() as temp_dir:
        pap_dir = os.path.join(temp_dir, ".agent")
        os.makedirs(pap_dir)
        
        # 1. Test protocol version mismatch warning
        agent_md = os.path.join(pap_dir, "agent.md")
        with open(agent_md, "w", encoding="utf-8") as f:
            f.write("""---
name: incompat-proto
description: Test incompat protocol
protocol_version: 9.0.0
---
# Incompatible Protocol content
""")
            
        with pytest.warns(UserWarning, match="Protocol version mismatch"):
            engine = AgentEngine(workspace_path=temp_dir)
            
        # 2. Test min_runtime_version mismatch warning
        with open(agent_md, "w", encoding="utf-8") as f:
            f.write("""---
name: incompat-runtime
description: Test incompat runtime
min_runtime_version: 9.9.9
---
# Incompatible Runtime content
""")
            
        with pytest.warns(UserWarning, match="Runtime version mismatch"):
            engine = AgentEngine(workspace_path=temp_dir)


def test_agent_engine_parse_version_corners():
    # Covers fallback in version parser exception paths
    assert AgentEngine._parse_version("v1.2.3") == (1, 2, 3)
    assert AgentEngine._parse_version("invalid-version") == (0,)
    assert AgentEngine._parse_version("1.2a.3") == (1, 0, 3)


def test_agent_engine_prompt_render_failures():
    with tempfile.TemporaryDirectory() as temp_dir:
        engine = AgentEngine(workspace_path=temp_dir)
        
        # When template agent.jinja2 is missing, get_template throws TemplateNotFound,
        # which our engine catches and re-raises as FileNotFoundError
        with pytest.raises(FileNotFoundError, match="Required prompt template agent.jinja2 was not found"):
            engine.render_prompt({"user_input": "Hello"})
            
        # Create template with undefined variable
        with open(os.path.join(temp_dir, "agent.jinja2"), "w", encoding="utf-8") as f:
            f.write("Hello {{ undefined_var }}")
            
        # Clear environment cache or re-instantiate
        engine = AgentEngine(workspace_path=temp_dir)
        
        # Mock template render to raise UndefinedError
        from jinja2 import UndefinedError
        with patch.object(engine.jinja_env.get_template("agent.jinja2"), "render", side_effect=UndefinedError("mock undefined error")):
            # Should raise ValueError due to UndefinedError
            with pytest.raises(ValueError, match="Prompt rendering failed because the template referenced an undefined variable"):
                engine.render_prompt({"user_input": "Hello"})


def test_agent_engine_render_subagent_fallback():
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create agent.jinja2 but not agents/programmer.jinja2
        with open(os.path.join(temp_dir, "agent.jinja2"), "w", encoding="utf-8") as f:
            f.write("Default template: {{ user_input }}")
            
        engine = AgentEngine(workspace_path=temp_dir)
        
        # Rendering non-existent subagent falls back to agent.jinja2 and logs warning
        rendered = engine.render_prompt({"user_input": "Subagent Test"}, agent_name="programmer")
        assert "Default template: Subagent Test" in rendered


def test_agent_engine_tool_execution_scenarios():
    with tempfile.TemporaryDirectory() as temp_dir:
        engine = AgentEngine(workspace_path=temp_dir)
        
        # Mock some tools in tools_registry
        from pydantic import BaseModel, Field
        
        class MockArgs1(BaseModel):
            x: int = Field(description="mock parameter x")
            
        def mock_tool_func1(args: MockArgs1):
            return f"Result: {args.x * 2}"
            
        class MockArgs2(BaseModel):
            msg: str = Field(description="mock msg")
            
        def mock_tool_func2(args: MockArgs2, context: dict):
            session_id = context.get("session_id", "none")
            return f"Context: {session_id}, msg: {args.msg}"
            
        engine.tools_registry["mock1"] = {
            "function": mock_tool_func1,
            "args_model": MockArgs1,
            "description": "A simple mock tool",
            "schema": MockArgs1.model_json_schema(),
            "wants_context": False,
            "is_markdown_skill": False,
        }
        
        engine.tools_registry["mock2"] = {
            "function": mock_tool_func2,
            "args_model": MockArgs2,
            "description": "A mock tool that wants context",
            "schema": MockArgs2.model_json_schema(),
            "wants_context": True,
            "is_markdown_skill": False,
        }
        
        # 1. Successful execution
        res1 = engine.execute_tool("mock1", {"x": 5})
        assert res1 == "Result: 10"
        
        # 2. Execution with context
        res2 = engine.execute_tool("mock2", {"msg": "hello"}, context={"session_id": "test-session"})
        assert res2 == "Context: test-session, msg: hello"
        
        # 3. Unknown tool
        with pytest.raises(KeyError, match="Unknown tool 'unknown_tool'"):
            engine.execute_tool("unknown_tool", {})
            
        # 4. Unauthorized tool (not in allowed list)
        with pytest.raises(PermissionError, match="is not allowed for this request"):
            engine.execute_tool("mock1", {"x": 5}, allowed_tools=["mock2"])
            
        # 5. Tool throws exception
        def failing_tool(args: MockArgs1):
            raise ZeroDivisionError("division by zero in tool")
            
        engine.tools_registry["mock_fail"] = {
            "function": failing_tool,
            "args_model": MockArgs1,
            "description": "Failing mock tool",
            "schema": MockArgs1.model_json_schema(),
            "wants_context": False,
            "is_markdown_skill": False,
        }
        
        with pytest.raises(ZeroDivisionError, match="division by zero"):
            engine.execute_tool("mock_fail", {"x": 5})
            
        # 6. Test schemas filter
        schemas = engine.get_tool_schemas(allowed_tools=["mock1"])
        assert len(schemas) == 1
        assert schemas[0]["name"] == "mock1"
        assert schemas[0]["description"] == "A simple mock tool"


def test_agent_engine_summary():
    with tempfile.TemporaryDirectory() as temp_dir:
        engine = AgentEngine(workspace_path=temp_dir)
        summary_str = engine.summary()
        assert "AgentEngine Runtime Summary" in summary_str
        assert f"Workspace: {engine.workspace_path}" in summary_str


def test_agent_engine_split_frontmatter_yaml_fallback():
    # Covers split_frontmatter fallbacks when yaml safe_load fails
    raw_md_yaml_error = """---
name: incomplete-yaml
invalid_yaml_field: : :
---
# Content body
"""
    # Should fall back to simple frontmatter parser
    frontmatter, body = AgentEngine._split_frontmatter(raw_md_yaml_error)
    assert frontmatter == {}
    assert "# Content body" in body

    # Simple frontmatter parser covers multiple list items, quotes stripping
    raw_simple = """
name: "simple-name"
description: 'simple-desc'
tags:
- tag1
- tag2
"""
    parsed = AgentEngine._parse_simple_frontmatter(raw_simple)
    assert parsed["name"] == "simple-name"
    assert parsed["description"] == "simple-desc"
    assert parsed["tags"] == ["tag1", "tag2"]


def test_agent_engine_discover_markdown_nonexistent_files():
    with tempfile.TemporaryDirectory() as temp_dir:
        engine = AgentEngine(workspace_path=temp_dir)
        # Verify no error thrown when loading non-readable/nonexistent file
        engine._parse_skill_md(os.path.join(temp_dir, "nonexistent.md"))
        engine._parse_pap_doc(os.path.join(temp_dir, "nonexistent.md"), "test", "test")


def test_agent_engine_discover_errors():
    with tempfile.TemporaryDirectory() as temp_dir:
        # Malformed check
        engine = AgentEngine(workspace_path=temp_dir)
        # Should not crash on invalid frontmatter structure
        _, body = engine._split_frontmatter("---invalid---\ncontent")
        assert "content" in body


def test_agent_engine_path_traversal_guards():
    with tempfile.TemporaryDirectory() as temp_dir:
        engine = AgentEngine(workspace_path=temp_dir)
        
        # Test traversal guard in export_handoff
        with pytest.raises(PermissionError, match="Directory traversal warning: Access denied outside memory boundary"):
            engine.export_handoff("../traversal", "summary")
            
        # Test traversal guard in import_handoff
        with pytest.raises(PermissionError, match="Directory traversal warning: Access denied outside handoff boundary"):
            engine.import_handoff("../traversal")
            
        # Test traversal guard in _parse_skill_md
        with pytest.raises(PermissionError, match="Directory traversal warning: Access denied outside project boundary"):
            engine._parse_skill_md("../../outside.md")
            
        # Test traversal guard in _parse_pap_doc
        with pytest.raises(PermissionError, match="Directory traversal warning: Access denied outside project boundary"):
            engine._parse_pap_doc("../../outside.md", "name", "desc")


def test_agent_engine_handoff_failure_cases():
    with tempfile.TemporaryDirectory() as temp_dir:
        engine = AgentEngine(workspace_path=temp_dir)
        
        # 1. Handoff file not found
        with pytest.raises(FileNotFoundError, match="Handoff packet file 'nonexistent-id' not found"):
            engine.import_handoff("nonexistent-id")
            
        # 2. Handoff file is malformed JSON
        project_root = Path(temp_dir).parent
        handoff_dir = project_root / ".agent" / "memory" / "handoff"
        handoff_dir.mkdir(parents=True, exist_ok=True)
        
        malformed_file = handoff_dir / "handoff-malformed.json"
        malformed_file.write_text("invalid json", encoding="utf-8")
        
        with pytest.raises(ValueError, match="Malformed handoff packet JSON"):
            engine.import_handoff("handoff-malformed")
            
        # 3. Missing required fields in handoff
        missing_file = handoff_dir / "handoff-missing.json"
        import json
        missing_file.write_text(json.dumps({"protocol": "PAP-Handoff"}), encoding="utf-8")
        
        with pytest.raises(ValueError, match="is missing required fields"):
            engine.import_handoff("handoff-missing")
            
        # 4. Checksum mismatch
        bad_checksum_file = handoff_dir / "handoff-badchecksum.json"
        packet = {
            "protocol": "PAP-Handoff",
            "version": "1.0.0",
            "handoff_id": "handoff-badchecksum",
            "created_at": "2026-05-16",
            "task_state": {},
            "context_summary": "test",
            "memory_snapshot": {},
            "checksum": "wrong-checksum"
        }
        bad_checksum_file.write_text(json.dumps(packet), encoding="utf-8")
        
        with pytest.raises(ValueError, match="integrity verification failed"):
            engine.import_handoff("handoff-badchecksum")
