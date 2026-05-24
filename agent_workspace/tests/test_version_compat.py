import os
import sys
import tempfile
import pytest
import warnings
from pathlib import Path

# Add project root to sys.path
workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)

from core.engine import AgentEngine


def test_parse_version():
    """Verify version tuple parsing works for standard, pre-release and leading-v strings."""
    assert AgentEngine._parse_version("1.0.0") == (1, 0, 0)
    assert AgentEngine._parse_version("v2.5.12-alpha") == (2, 5, 12)
    assert AgentEngine._parse_version("0.1") == (0, 1)
    assert AgentEngine._parse_version("invalid") == (0,)


def test_version_compat_happy_path():
    """Verify standard compatible version manifest emits no warnings."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        pap_dir = temp_path / ".agent"
        pap_dir.mkdir(parents=True, exist_ok=True)
        
        # Valid and compatible metadata
        agent_md_content = """---
protocol_version: "1.0.0"
min_runtime_version: "0.1.0"
name: compatible-agent
version: "0.1.0"
---
Compatible Agent Body
"""
        (pap_dir / "agent.md").write_text(agent_md_content, encoding="utf-8")
        
        # Instantiate engine and assert no UserWarnings are emitted
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            engine = AgentEngine(workspace_path=temp_dir)
            # Filter for UserWarning
            user_warnings = [warning for warning in w if issubclass(warning.category, UserWarning)]
            assert len(user_warnings) == 0


def test_min_runtime_version_warning():
    """Verify that a manifest requiring higher min_runtime_version raises a UserWarning."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        pap_dir = temp_path / ".agent"
        pap_dir.mkdir(parents=True, exist_ok=True)
        
        # Requires runtime version 10.0.0 (which exceeds current 0.5.0)
        agent_md_content = """---
protocol_version: "1.0.0"
min_runtime_version: "10.0.0"
name: futuristic-agent
version: "1.0.0"
---
Futuristic Agent Body
"""
        (pap_dir / "agent.md").write_text(agent_md_content, encoding="utf-8")
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            engine = AgentEngine(workspace_path=temp_dir)
            user_warnings = [warning for warning in w if issubclass(warning.category, UserWarning)]
            
            # Check warning triggers and has the expected text
            assert len(user_warnings) >= 1
            assert any("requires min_runtime_version '10.0.0'" in str(warn.message) for warn in user_warnings)


def test_protocol_version_major_warning():
    """Verify that a manifest requiring incompatible major protocol version raises a UserWarning."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        pap_dir = temp_path / ".agent"
        pap_dir.mkdir(parents=True, exist_ok=True)
        
        # Requires protocol version 2.0.0 (current is 1.0.0)
        agent_md_content = """---
protocol_version: "2.0.0"
min_runtime_version: "0.1.0"
name: breaking-protocol-agent
version: "1.0.0"
---
Breaking Protocol Agent Body
"""
        (pap_dir / "agent.md").write_text(agent_md_content, encoding="utf-8")
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            engine = AgentEngine(workspace_path=temp_dir)
            user_warnings = [warning for warning in w if issubclass(warning.category, UserWarning)]
            
            assert len(user_warnings) >= 1
            assert any("protocol version '2.0.0' is incompatible" in str(warn.message) for warn in user_warnings)
