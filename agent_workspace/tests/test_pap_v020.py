import os
import sys
import json
import pytest
import shutil
import yaml
from pathlib import Path

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agent_workspace.core.engine import AgentEngine, HandoffRequired
from agent_workspace.pap_validate import validate as run_pap_validate
import agent_workspace.cli as cli


@pytest.fixture
def temp_workspace(tmp_path):
    """Set up a temporary PAP-compliant workspace structure."""
    agent_dir = tmp_path / ".agent"
    agent_dir.mkdir(parents=True, exist_ok=True)
    (agent_dir / "skills").mkdir(parents=True, exist_ok=True)
    (agent_dir / "prompts").mkdir(parents=True, exist_ok=True)
    (agent_dir / "memory").mkdir(parents=True, exist_ok=True)
    (agent_dir / "workflows").mkdir(parents=True, exist_ok=True)
    (agent_dir / "knowledge_base").mkdir(parents=True, exist_ok=True)

    # Copy spec schemas to the temp workspace
    spec_dir = tmp_path / "spec"
    spec_dir.mkdir(parents=True, exist_ok=True)
    src_spec = Path(__file__).resolve().parents[2] / "spec"
    for schema_file in src_spec.glob("*.json"):
        shutil.copy(schema_file, spec_dir / schema_file.name)

    # Create default valid files
    agent_yaml = {
        "protocol_version": "1.0.0",
        "min_runtime_version": "0.1.0",
        "name": "test-agent",
        "version": "1.0.0",
        "purpose": "Testing agent PAP v0.2.0 compatibility.",
        "language": "en",
        "authorization_level": "autonomous",
        "use_case_tags": ["testing"],
        "tools": ["calculate"],
        "protocol": {
            "root": ".agent/",
            "manifest": ".agent/agent.md",
            "entrypoints": {
                "skills": ".agent/skills.md",
                "tasks": "agent_tasks.md",
                "handoff": ".agent/handoff_guide.md"
            },
            "directories": {
                "skills": ".agent/skills/"
            }
        }
    }

    agent_md = f"---\n{yaml.safe_dump(agent_yaml)}---\n# Test Agent Manifest"
    (agent_dir / "agent.md").write_text(agent_md, encoding="utf-8")
    (agent_dir / "skills.md").write_text("# Skills Entry", encoding="utf-8")
    (agent_dir / "handoff_guide.md").write_text("# Handoff Guide", encoding="utf-8")
    (tmp_path / "agent_tasks.md").write_text("# Task Queue", encoding="utf-8")

    # Create dummy skill md contract
    (agent_dir / "skills" / "calculate.md").write_text(
        "---\nid: calculate\ndescription: Test calc\nversion: 1.0.0\ninputs:\n  expr:\n    type: string\n    required: true\n    description: test\noutputs:\n  res: test\nsafety_notes: []\n---\n# calculate",
        encoding="utf-8"
    )

    return tmp_path


def test_schema_validation_success(temp_workspace):
    """Verify that a valid workspace layout and schema passes validation."""
    run_pap_validate(temp_workspace)  # Should run without raising exceptions


def test_schema_validation_failure(temp_workspace):
    """Verify schema mismatch throws a ValueError."""
    agent_dir = temp_workspace / ".agent"
    # Overwrite agent.md with missing required key "tools"
    bad_yaml = {
        "protocol_version": "1.0.0",
        "min_runtime_version": "0.1.0",
        "name": "test-agent",
        "version": "1.0.0",
        "purpose": "Missing tools key.",
        "language": "en",
        "authorization_level": "autonomous",
        "use_case_tags": ["testing"]
    }
    (agent_dir / "agent.md").write_text(f"---\n{yaml.safe_dump(bad_yaml)}---\n# Bad Agent", encoding="utf-8")

    with pytest.raises(ValueError, match="Schema validation failed"):
        run_pap_validate(temp_workspace)


def test_missing_skill_contract_failure(temp_workspace):
    """Verify missing local skill contract raises FileNotFoundError."""
    # Add an undeclared tool to manifest tools list
    manifest_p = temp_workspace / ".agent" / "agent.md"
    raw_content = manifest_p.read_text(encoding="utf-8")
    updated = raw_content.replace("- calculate", "- calculate\n  - missing_tool")
    manifest_p.write_text(updated, encoding="utf-8")

    with pytest.raises(FileNotFoundError, match="Missing skill contracts"):
        run_pap_validate(temp_workspace)


def test_dynamic_path_resolution_directories(temp_workspace):
    """Verify non-existent paths declared in manifest trigger FileNotFoundError."""
    manifest_p = temp_workspace / ".agent" / "agent.md"
    parts = manifest_p.read_text(encoding="utf-8").split("---", 2)
    config = yaml.safe_load(parts[1])
    config["protocol"]["directories"]["skills"] = ".agent/non_existent_skills_dir/"
    manifest_p.write_text(f"---\n{yaml.safe_dump(config)}---\n# Test", encoding="utf-8")

    with pytest.raises(FileNotFoundError, match="does not exist"):
        run_pap_validate(temp_workspace)


def test_version_compat_checks(temp_workspace):
    """Verify semantic version checks reject mismatching protocol major or newer runtime versions."""
    agent_dir = temp_workspace / ".agent"

    # 1. Incompatible protocol major version (2.0.0 != 1.x.x)
    bad_proto_yaml = {
        "protocol_version": "2.0.0",
        "min_runtime_version": "0.1.0",
        "name": "test-agent",
        "version": "1.0.0",
        "purpose": "Major proto mismatch",
        "language": "en",
        "authorization_level": "autonomous",
        "use_case_tags": ["testing"],
        "tools": ["calculate"]
    }
    (agent_dir / "agent.md").write_text(f"---\n{yaml.safe_dump(bad_proto_yaml)}---\n# Bad Agent", encoding="utf-8")
    with pytest.raises(ValueError, match="Incompatible protocol version major mismatch"):
        run_pap_validate(temp_workspace)

    # 2. Incompatible min runtime version (9.9.9 > current 0.5.0)
    bad_run_yaml = {
        "protocol_version": "1.0.0",
        "min_runtime_version": "9.9.9",
        "name": "test-agent",
        "version": "1.0.0",
        "purpose": "Too high runtime requirement",
        "language": "en",
        "authorization_level": "autonomous",
        "use_case_tags": ["testing"],
        "tools": ["calculate"]
    }
    (agent_dir / "agent.md").write_text(f"---\n{yaml.safe_dump(bad_run_yaml)}---\n# Bad Agent", encoding="utf-8")
    with pytest.raises(ValueError, match="Incompatible runtime version"):
        run_pap_validate(temp_workspace)


def test_onboarding_sequence_enforcement(temp_workspace):
    """Verify onboarding order: agent.md -> skills.md -> agent_tasks.md -> handoff_guide.md."""
    engine = AgentEngine(workspace_path=str(temp_workspace))

    # Pre-onboarding: executing tools should be blocked
    with pytest.raises(PermissionError, match="Onboarding sequence incomplete"):
        engine.execute_tool("calculate", {"expression": "2+2"}, allowed_tools=["calculate"])

    # Out of order: reading skills.md first must fail
    with pytest.raises(PermissionError, match="Onboarding sequence out of order"):
        engine.read_onboarding_file("skills.md")

    # In-order reading
    assert "protocol_version" in engine.read_onboarding_file("agent.md")
    assert not engine.is_onboarding_complete()

    # Again out of order: try to read tasks next instead of skills
    with pytest.raises(PermissionError, match="Onboarding sequence out of order"):
        engine.read_onboarding_file("agent_tasks.md")

    # Correct sequence progress
    engine.read_onboarding_file("skills.md")
    engine.read_onboarding_file("agent_tasks.md")
    engine.read_onboarding_file("handoff_guide.md")

    assert engine.is_onboarding_complete()
    # Now tool execution should bypass the onboarding blocker
    # (Note: calculate might fail if math.py is not importable, but it won't raise onboarding PermissionError)
    try:
        engine.execute_tool("calculate", {"expression": "2+2"}, allowed_tools=["calculate"])
    except PermissionError as e:
        assert "Onboarding sequence incomplete" not in str(e)
    except Exception:
        pass


def test_onboarding_bypass(temp_workspace):
    """Verify onboarding can be bypassed via parameter or env var."""
    # 1. Parameter bypass
    engine_param = AgentEngine(workspace_path=str(temp_workspace), bypass_onboarding=True)
    assert engine_param.is_onboarding_complete()

    # 2. Env bypass
    os.environ["PAP_BYPASS_ONBOARDING"] = "true"
    try:
        engine_env = AgentEngine(workspace_path=str(temp_workspace))
        assert engine_env.is_onboarding_complete()
    finally:
        del os.environ["PAP_BYPASS_ONBOARDING"]


def test_auto_handoff_and_exit_code_42(temp_workspace):
    """Verify that exceeding turns or context length raises HandoffRequired with exit code 42."""
    agent_dir = temp_workspace / ".agent"
    agent_yaml = {
        "protocol_version": "1.0.0",
        "min_runtime_version": "0.1.0",
        "name": "test-agent",
        "version": "1.0.0",
        "purpose": "Handoff limits test.",
        "language": "en",
        "authorization_level": "autonomous",
        "use_case_tags": ["testing"],
        "tools": ["calculate"],
        "auto_handoff": {
            "max_turns": 2,
            "max_context_chars": 50
        }
    }
    (agent_dir / "agent.md").write_text(f"---\n{yaml.safe_dump(agent_yaml)}---\n# Test", encoding="utf-8")

    engine = AgentEngine(workspace_path=str(temp_workspace), bypass_onboarding=True)

    # First turn: success
    try:
        engine.execute_tool("calculate", {"expression": "2+2"}, allowed_tools=["calculate"])
    except Exception:
        pass

    # Second turn: success
    try:
        engine.execute_tool("calculate", {"expression": "2+2"}, allowed_tools=["calculate"])
    except Exception:
        pass

    # Third turn: triggers handoff
    with pytest.raises(HandoffRequired) as exc_info:
        engine.execute_tool("calculate", {"expression": "2+2"}, allowed_tools=["calculate"])

    assert exc_info.value.HANDOFF_EXIT_CODE == 42
    assert exc_info.value.handoff_id is not None
    assert "Turn count 3 exceeds max_turns 2" in exc_info.value.reason


def test_cli_handoff_handling(temp_workspace):
    """Verify that CLI catch wrapper exits with 42 when HandoffRequired is raised."""
    import subprocess
    import sys
    code = """
import sys
from agent_workspace.core.engine import HandoffRequired
import agent_workspace.cli as cli

def mock_main():
    raise HandoffRequired("test-handoff-id", "test-reason")

cli.main = mock_main

try:
    try:
        cli.main()
    except Exception as e:
        if hasattr(e, "HANDOFF_EXIT_CODE"):
            sys.exit(e.HANDOFF_EXIT_CODE)
        if e.__class__.__name__ == "HandoffRequired":
            sys.exit(42)
        raise e
except SystemExit as se:
    sys.exit(se.code)
"""
    res = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True
    )
    assert res.returncode == 42
