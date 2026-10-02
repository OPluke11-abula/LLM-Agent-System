import os
import sys
import tempfile
import pytest
from pathlib import Path
from pydantic import BaseModel
from unittest.mock import MagicMock, patch

workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)

from core.skill_loader import SkillLoader

@pytest.fixture
def temp_workspace():
    with tempfile.TemporaryDirectory() as temp_dir:
        skills_dir = os.path.join(temp_dir, "skills")
        os.makedirs(skills_dir)
        
        # Create Sample 1: Document Generation (anthropics style)
        docx_dir = os.path.join(skills_dir, "docx_generator")
        os.makedirs(docx_dir)
        with open(os.path.join(docx_dir, "SKILL.md"), "w", encoding="utf-8") as f:
            f.write("""---
name: docx-generator
description: Generate docx reports based on user requirements.
triggers:
  - generate report
  - export docx
---

# Docx Generator Skill
1. Ask for content.
2. Format as a business report.
3. Call the Python docx API.
""")

        # Create Sample 2: Data Analysis
        analysis_dir = os.path.join(skills_dir, "data_analyzer")
        os.makedirs(analysis_dir)
        with open(os.path.join(analysis_dir, "SKILL.md"), "w", encoding="utf-8") as f:
            f.write("""---
name: data-analyzer
description: Analyze raw data and return insights.
---

# Data Analyzer Skill
1. Identify the dataset.
2. Find outliers.
3. Summarize findings.
""")

        yield temp_dir


def test_skill_loader_discovery(temp_workspace):
    loader = SkillLoader(temp_workspace)
    skills = loader.discover_skills()
    
    assert len(skills) == 2
    assert "docx_generator" in skills
    assert "data_analyzer" in skills


def test_skill_loader_metadata(temp_workspace):
    loader = SkillLoader(temp_workspace)
    skills = loader.discover_skills()
    
    docx_skill = skills["docx_generator"]
    assert "Generate docx reports based on user requirements." in docx_skill["description"]
    assert "Triggers: generate report, export docx" in docx_skill["description"]
    assert docx_skill["is_markdown_skill"] is True
    
    analysis_skill = skills["data_analyzer"]
    assert "Analyze raw data and return insights." in analysis_skill["description"]


def test_skill_loader_tool_execution(temp_workspace):
    loader = SkillLoader(temp_workspace)
    skills = loader.discover_skills()
    
    docx_skill = skills["docx_generator"]
    ArgsModel = docx_skill["args_model"]
    func = docx_skill["function"]
    
    args = ArgsModel(intent="I need a weekly sales report")
    result = func(args)
    
    assert "Loaded Skill Instructions: docx_generator" in result
    assert "Intent: I need a weekly sales report" in result
    assert "1. Ask for content." in result
    assert "3. Call the Python docx API." in result


def test_skill_loader_split_frontmatter_fallback():
    # Covers fallback in split_frontmatter (handling malformed YAML/no yaml library)
    raw_md_bad_yaml = """---
name: [bad-yaml
triggers: }
---
# Body content
"""
    frontmatter, body = SkillLoader._split_frontmatter(raw_md_bad_yaml)
    # Parser should catch YAMLError and use parse_simple_frontmatter successfully
    assert frontmatter["name"] == "[bad-yaml"
    assert frontmatter["triggers"] == "}"
    assert "# Body content" in body

    # Test parse_simple_frontmatter lines
    raw_simple = """
name: simple-skill
triggers:
- trigger1
- trigger2
"""
    parsed = SkillLoader._parse_simple_frontmatter(raw_simple)
    assert parsed["name"] == "simple-skill"
    assert parsed["triggers"] == ["trigger1", "trigger2"]


def test_skill_loader_path_traversal_guards(temp_workspace):
    loader = SkillLoader(temp_workspace)
    
    # Try parsing file that is outside both workspace skills and global skills
    with pytest.raises(PermissionError, match="Directory traversal warning: Access denied outside skill directories"):
        loader._parse_and_register_skill("../../../outside_skill.md")


def test_skill_loader_file_io_errors(temp_workspace):
    loader = SkillLoader(temp_workspace)
    
    # Try parsing non-existent file path inside local skills directory (to bypass traversal checks)
    local_skill_file = os.path.join(temp_workspace, "skills", "nonexistent_skill.md")
    # Should not crash on OSError
    loader._parse_and_register_skill(local_skill_file)
    assert "nonexistent_skill" not in loader.markdown_skills


def test_skill_loader_global_scan_simulation(temp_workspace):
    loader = SkillLoader(temp_workspace)
    
    # Mock "pytest" in sys.modules to false or patch is_testing logic to test global directory scanning block
    import sys
    with pytest.MonkeyPatch.context() as mp:
        # We temporarily mock os.path.isdir to return True for the global skills dir so it executes the entry block
        global_skills_dir = os.path.join(os.path.expanduser("~"), ".gemini", "antigravity", "skills")
        
        original_isdir = os.path.isdir
        def mock_isdir(path):
            if path == global_skills_dir:
                return True
            return original_isdir(path)
            
        original_listdir = os.listdir
        def mock_listdir(path):
            if path == global_skills_dir:
                return ["global_skill_dir"]
            return original_listdir(path)
            
        mp.setattr(os.path, "isdir", mock_isdir)
        mp.setattr(os, "listdir", mock_listdir)
        
        # We also mock os.path.isfile for the global SKILL.md file
        original_isfile = os.path.isfile
        def mock_isfile(path):
            if path == os.path.join(global_skills_dir, "global_skill_dir", "SKILL.md"):
                return True
            return original_isfile(path)
            
        mp.setattr(os.path, "isfile", mock_isfile)
        
        # Mock _parse_and_register_skill to track calls
        mock_register = mp.setattr(loader, "_parse_and_register_skill", MagicMock())
        
        # Temporarily mock "pytest" not in sys.modules check
        # Since "pytest" in sys.modules is verified, we can use a patch on sys.modules
        mock_sys_modules = sys.modules.copy()
        if "pytest" in mock_sys_modules:
            del mock_sys_modules["pytest"]
            
        with patch.dict(sys.modules, mock_sys_modules, clear=True):
            loader.discover_skills()
            
        # Verify it successfully scanned and attempted to parse the global skill!
        assert loader._parse_and_register_skill.called
