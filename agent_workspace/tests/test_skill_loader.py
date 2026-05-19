import os
import sys
import tempfile
import pytest
from pydantic import BaseModel

workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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
    
    # Create arguments using the dynamic model
    args = ArgsModel(intent="I need a weekly sales report")
    result = func(args)
    
    assert "Loaded Skill Instructions: docx_generator" in result
    assert "Intent: I need a weekly sales report" in result
    assert "1. Ask for content." in result
    assert "3. Call the Python docx API." in result
