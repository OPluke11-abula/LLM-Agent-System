import os
import json
import yaml
import pytest
from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, ValidationError

# Set project root and directories
TEST_DIR = Path(__file__).parent
WORKSPACE_DIR = TEST_DIR.parent
PROJECT_ROOT = WORKSPACE_DIR.parent
SKILLS_DIR = PROJECT_ROOT / ".agent" / "skills"
SCHEMA_FILE = PROJECT_ROOT / "spec" / "skill-contract.schema.json"

# Define Pydantic validation models matching spec/skill-contract.schema.json
class InputParam(BaseModel):
    type: str
    required: bool
    description: str

class OutputParam(BaseModel):
    type: str
    description: str

class Outputs(BaseModel):
    success: OutputParam
    error: OutputParam

class SkillContractFrontMatter(BaseModel):
    id: str
    name: str
    description: str
    version: str
    inputs: Dict[str, InputParam]
    outputs: Outputs
    safety_notes: List[str]
    author: Optional[str] = None


def get_skill_contracts() -> List[Path]:
    """Discover all skill contract markdown files."""
    if not SKILLS_DIR.exists():
        return []
    return sorted([
        p for p in SKILLS_DIR.glob("*.md")
        if not p.name.startswith("_")
    ])


def test_schema_file_exists():
    """Verify that the skill contract schema file exists."""
    assert SCHEMA_FILE.exists(), f"Schema file not found at {SCHEMA_FILE}"


def test_skills_directory_not_empty():
    """Verify that skill contracts exist in the .agent/skills directory."""
    contracts = get_skill_contracts()
    assert len(contracts) > 0, "No skill contracts found in .agent/skills/"
    # We expect 19 standardized skill contracts
    assert len(contracts) == 19, f"Expected 19 skill contracts, found {len(contracts)}"


@pytest.mark.parametrize("contract_path", get_skill_contracts(), ids=lambda p: p.stem)
def test_skill_contract_validation(contract_path: Path):
    """Validate each skill contract against the YAML front matter spec."""
    content = contract_path.read_text(encoding="utf-8")
    
    # 1. Basic format validation (must start/end front matter with ---)
    assert content.startswith("---"), f"Contract {contract_path.name} must start with '---'"
    parts = content.split("---", 2)
    assert len(parts) >= 3, f"Contract {contract_path.name} is missing front matter closing delimiter '---'"
    
    # 2. Parse YAML front matter
    fm_raw = parts[1]
    try:
        fm = yaml.safe_load(fm_raw)
    except yaml.YAMLError as exc:
        pytest.fail(f"Failed to parse YAML front matter in {contract_path.name}: {exc}")
        
    assert isinstance(fm, dict), f"Front matter in {contract_path.name} must be a dictionary/object"

    # 3. Pydantic-based schema validation
    try:
        validated_fm = SkillContractFrontMatter(**fm)
    except ValidationError as exc:
        pytest.fail(f"Schema validation failed for {contract_path.name}:\n{exc}")

    # 4. Assert contract ID matches the filename stem
    assert validated_fm.id == contract_path.stem, (
        f"Contract ID '{validated_fm.id}' does not match filename '{contract_path.name}'"
    )

    # 5. Assert fields are not empty
    assert validated_fm.description.strip(), f"Description in {contract_path.name} must not be empty"
    assert validated_fm.version.strip(), f"Version in {contract_path.name} must not be empty"

    # 6. Optional: JSON Schema library verification if available
    try:
        import jsonschema
        with open(SCHEMA_FILE, "r", encoding="utf-8") as sf:
            schema_data = json.load(sf)
        jsonschema.validate(instance=fm, schema=schema_data)
    except ImportError:
        # jsonschema is optional, we fall back to Pydantic which is authoritative
        pass
    except Exception as exc:
        pytest.fail(f"JSON Schema validation failed for {contract_path.name} against schema file: {exc}")


def test_skills_registry_format():
    """Verify that .agent/skills.md starts with valid front matter."""
    registry_path = PROJECT_ROOT / ".agent" / "skills.md"
    assert registry_path.exists(), "skills.md registry does not exist"
    
    content = registry_path.read_text(encoding="utf-8")
    assert content.startswith("---"), "skills.md must start with YAML front matter"
    
    parts = content.split("---", 2)
    assert len(parts) >= 3, "skills.md is missing ending '---' delimiter"
    
    fm_raw = parts[1]
    fm = yaml.safe_load(fm_raw)
    
    assert isinstance(fm, dict), "skills.md front matter is not a valid YAML dictionary"
    assert "schema_version" in fm, "skills.md front matter is missing 'schema_version'"
    assert fm["schema_version"] == "1.0.0", f"skills.md 'schema_version' should be '1.0.0', got '{fm['schema_version']}'"
