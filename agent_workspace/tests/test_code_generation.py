import os
import sys
import tempfile
import pytest
from pathlib import Path

# Add project root to sys.path
workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)

from core.engine import AgentEngine, DynamicCodeGenerator


@pytest.fixture
def temp_workspace():
    """Scaffolds a mock temp workspace for code generation."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        (temp_path / "skills").mkdir(parents=True, exist_ok=True)
        (temp_path / "tests").mkdir(parents=True, exist_ok=True)
        
        # Scaffold a minimal conftest.py to prevent pytest inside subprocess
        # from walking up and getting confused by local conftests
        (temp_path / "conftest.py").write_text("", encoding="utf-8")
        
        # Add local workspace to python path of subprocess by writing a customized pytest.ini
        ini_content = f"[pytest]\npythonpath = {temp_dir}\n"
        (temp_path / "pytest.ini").write_text(ini_content, encoding="utf-8")
        
        yield temp_dir


def test_dynamic_code_generator_success(temp_workspace):
    """Verify that DynamicCodeGenerator successfully audits, tests, and hot-loads a valid skill."""
    engine = AgentEngine(temp_workspace)
    generator = DynamicCodeGenerator(engine)
    
    valid_code = """
from pydantic import BaseModel, Field

class MultiplyArgs(BaseModel):
    x: float = Field(..., description="First value")
    y: float = Field(..., description="Second value")

def multiply(args: MultiplyArgs) -> str:
    return f"Product: {args.x * args.y}"
"""
    
    success = generator.generate_and_load_skill("multiply", valid_code)
    assert success is True
    
    # Check that file exists on disk
    skill_file = Path(temp_workspace) / "skills" / "multiply.py"
    assert skill_file.is_file()
    
    # Check hot-loaded registry entry
    assert "multiply" in engine.tools_registry
    tool = engine.tools_registry["multiply"]
    assert tool["description"] is None or tool["description"] == ""
    assert "x" in tool["schema"]["properties"]
    
    # Check tool execution
    result = engine.execute_tool("multiply", {"x": 3.0, "y": 4.0})
    assert result == "Product: 12.0"


def test_dynamic_code_generator_security_violations(temp_workspace):
    """Verify that DynamicCodeGenerator blocks unsafe dynamic calls (eval, exec, compile)."""
    engine = AgentEngine(temp_workspace)
    generator = DynamicCodeGenerator(engine)
    
    unsafe_code = """
from pydantic import BaseModel

class ExploitArgs(BaseModel):
    command: str

def exploit(args: ExploitArgs) -> str:
    eval("import os; os.system(args.command)")
    return "executed"
"""
    
    with pytest.raises(PermissionError) as exc_info:
        generator.generate_and_load_skill("exploit", unsafe_code)
    
    assert "Security violation" in str(exc_info.value)
    assert "eval" in str(exc_info.value)
    
    # Ensure no files were left on disk and registry is clean
    skill_file = Path(temp_workspace) / "skills" / "exploit.py"
    assert not skill_file.exists()
    assert "exploit" not in engine.tools_registry


def test_dynamic_code_generator_contract_violations(temp_workspace):
    """Verify that DynamicCodeGenerator blocks generated code violating the Pydantic BaseModel structure."""
    engine = AgentEngine(temp_workspace)
    generator = DynamicCodeGenerator(engine)
    
    # 1. Missing BaseModel class
    invalid_code_1 = """
def simple_add(x: float, y: float) -> str:
    return str(x + y)
"""
    with pytest.raises(ValueError) as exc_1:
        generator.generate_and_load_skill("simple_add", invalid_code_1)
    assert "Pydantic BaseModel" in str(exc_1.value)
    
    # 2. Missing function annotated with that model
    invalid_code_2 = """
from pydantic import BaseModel

class DummyArgs(BaseModel):
    name: str

def different_function(args: str) -> str:
    return args
"""
    with pytest.raises(ValueError) as exc_2:
        generator.generate_and_load_skill("different_function", invalid_code_2)
    assert "public function whose first parameter is annotated" in str(exc_2.value)


def test_dynamic_code_generator_pytest_failure(temp_workspace):
    """Verify that a tool failing verification triggers cleanup and raises ValueError."""
    engine = AgentEngine(temp_workspace)
    generator = DynamicCodeGenerator(engine)
    
    # Code compiles, but defines something that will fail on import (e.g. invalid import)
    failing_code = """
from pydantic import BaseModel
import non_existent_dependency_xyz

class FailureArgs(BaseModel):
    pass

def failure(args: FailureArgs) -> str:
    return "fail"
"""
    
    with pytest.raises(ValueError) as exc_info:
        generator.generate_and_load_skill("failure", failing_code)
        
    assert "pytest verification gate failed" in str(exc_info.value)
    
    # Verify cleanup occurred
    skill_file = Path(temp_workspace) / "skills" / "failure.py"
    assert not skill_file.exists()
    assert "failure" not in engine.tools_registry
