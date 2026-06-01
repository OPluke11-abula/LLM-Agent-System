import os
import sys
import tempfile
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add project root to sys.path
workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, workspace_dir)

from core.skill_loader import DynamicSkillSynthesizer


@pytest.fixture
def temp_workspace():
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


def test_ast_audit_blocks_unsafe_execution(temp_workspace):
    synthesizer = DynamicSkillSynthesizer(temp_workspace)
    
    # 1. Test eval injection
    bad_code_eval = """
from pydantic import BaseModel

class UnsafeArgs(BaseModel):
    command: str

def execute_skill(args: UnsafeArgs) -> str:
    eval("1 + 1")
    return "done"
"""
    with pytest.raises(PermissionError, match="Security violation: unsafe execution call 'eval' detected"):
        synthesizer.synthesize_and_register_skill(MagicMock(), "unsafe_skill", bad_code_eval)

    # 2. Test subprocess injection
    bad_code_sub = """
from pydantic import BaseModel
import subprocess

class UnsafeArgs(BaseModel):
    command: str

def execute_skill(args: UnsafeArgs) -> str:
    subprocess.run(["ls"])
    return "done"
"""
    with pytest.raises(PermissionError, match="Security violation: unsafe execution call 'run' detected"):
        synthesizer.synthesize_and_register_skill(MagicMock(), "unsafe_skill_sub", bad_code_sub)


def test_validation_blocks_missing_pydantic_base(temp_workspace):
    synthesizer = DynamicSkillSynthesizer(temp_workspace)
    
    # Missing BaseModel inheritance
    bad_code_no_model = """
class InvalidArgs:
    command: str

def execute_skill(args: InvalidArgs) -> str:
    return "done"
"""
    with pytest.raises(ValueError, match="Synthesized skill must define a Pydantic BaseModel argument class"):
        synthesizer.synthesize_and_register_skill(MagicMock(), "invalid_skill_no_model", bad_code_no_model)


def test_validation_blocks_missing_annotated_function(temp_workspace):
    synthesizer = DynamicSkillSynthesizer(temp_workspace)
    
    # Function exists but signature lacks typing annotation
    bad_code_no_arg_type = """
from pydantic import BaseModel

class CustomArgs(BaseModel):
    command: str

def execute_skill(args) -> str:
    return "done"
"""
    with pytest.raises(ValueError, match="Synthesized skill must define a public function whose first parameter is annotated with the Pydantic BaseModel"):
        synthesizer.synthesize_and_register_skill(MagicMock(), "invalid_skill_no_arg_type", bad_code_no_arg_type)


def test_synthesis_and_dynamic_registration_success(temp_workspace):
    synthesizer = DynamicSkillSynthesizer(temp_workspace)
    mock_engine = MagicMock()
    
    valid_code = """
from pydantic import BaseModel

class ValidArgs(BaseModel):
    task: str

def my_synthesized_tool(args: ValidArgs) -> str:
    return f"Synthesized task: {args.task}"
"""
    
    # Mock sys.modules path for the temporary skills directory
    with patch("sys.path", [temp_workspace] + sys.path):
        # We need to make sure importlib.import_module can import skills.test_valid_skill
        # Therefore, we mock the module creation and insertion
        mock_module = MagicMock()
        mock_module.my_synthesized_tool = lambda args: f"Synthesized task: {args.task}"
        
        # Patch import_module so it returns our mocked module upon compilation
        with patch("importlib.import_module") as mock_import_module:
            mock_import_module.return_value = mock_module
            
            success = synthesizer.synthesize_and_register_skill(mock_engine, "test_valid_skill", valid_code)
            
            assert success is True
            # Verify file was written
            skill_file = Path(temp_workspace) / "skills" / "test_valid_skill.py"
            assert skill_file.is_file()
            assert "my_synthesized_tool" in skill_file.read_text(encoding="utf-8")
            
            # Verify registered call
            assert mock_engine._register_functions_from_module.called
            mock_engine._register_functions_from_module.assert_called_with(mock_module)
