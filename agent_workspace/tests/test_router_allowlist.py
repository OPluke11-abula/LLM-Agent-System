import os
import yaml
import pytest
from unittest.mock import MagicMock
from agent_workspace.core.engine import AgentEngine
from agent_workspace.core.router import AgentRouter


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
    return tmp_path


def test_router_allowlist_intersection(temp_workspace):
    # Setup standard config
    config_path = temp_workspace / "config.yaml"
    config_path.write_text("agent:\n  max_iterations: 5\n", encoding="utf-8")

    agent_md = temp_workspace / ".agent" / "agent.md"
    agent_md.write_text(
        "---\nauthorization_level: standard\ntools:\n  - tool_a\n  - tool_b\n  - tool_c\n---\n",
        encoding="utf-8"
    )

    engine = AgentEngine(workspace_path=str(temp_workspace), bypass_onboarding=True)
    router = AgentRouter(engine, session_id="test-allowlist-session", agent_name="tester")

    # 1. Caller allowed tools is None -> returns all PAP tools
    res = router._resolve_allowed_tools(None)
    assert sorted(res) == ["tool_a", "tool_b", "tool_c"]

    # 2. Caller allowed tools intersects with PAP tools
    res = router._resolve_allowed_tools(["tool_a", "tool_c", "tool_d"])
    assert sorted(res) == ["tool_a", "tool_c"]

    # 3. Caller allowed tools has no intersection
    res = router._resolve_allowed_tools(["tool_d"])
    assert res == []


def test_router_allowlist_missing_agent_md(temp_workspace):
    # Setup standard config without agent.md
    config_path = temp_workspace / "config.yaml"
    config_path.write_text("agent:\n  max_iterations: 5\n", encoding="utf-8")

    engine = AgentEngine(workspace_path=str(temp_workspace), bypass_onboarding=True)
    router = AgentRouter(engine, session_id="test-allowlist-session", agent_name="tester")

    # Expect fail-closed (returns empty list)
    res = router._resolve_allowed_tools(None)
    assert res == []


def test_router_allowlist_invalid_yaml(temp_workspace):
    config_path = temp_workspace / "config.yaml"
    config_path.write_text("agent:\n  max_iterations: 5\n", encoding="utf-8")

    agent_md = temp_workspace / ".agent" / "agent.md"
    # Invalid YAML syntax (e.g. missing colon or unindented mapping)
    agent_md.write_text(
        "---\nauthorization_level: standard\ntools\n  - tool_a\n---\n",
        encoding="utf-8"
    )

    engine = AgentEngine(workspace_path=str(temp_workspace), bypass_onboarding=True)
    router = AgentRouter(engine, session_id="test-allowlist-session", agent_name="tester")

    # Expect fail-closed (returns empty list)
    res = router._resolve_allowed_tools(None)
    assert res == []


def test_router_allowlist_not_a_dict(temp_workspace):
    config_path = temp_workspace / "config.yaml"
    config_path.write_text("agent:\n  max_iterations: 5\n", encoding="utf-8")

    agent_md = temp_workspace / ".agent" / "agent.md"
    # Frontmatter is a list instead of a dict
    agent_md.write_text(
        "---\n- standard\n- tools\n---\n",
        encoding="utf-8"
    )

    engine = AgentEngine(workspace_path=str(temp_workspace), bypass_onboarding=True)
    router = AgentRouter(engine, session_id="test-allowlist-session", agent_name="tester")

    # Expect fail-closed (returns empty list)
    res = router._resolve_allowed_tools(None)
    assert res == []


def test_router_allowlist_tools_not_a_list(temp_workspace):
    config_path = temp_workspace / "config.yaml"
    config_path.write_text("agent:\n  max_iterations: 5\n", encoding="utf-8")

    agent_md = temp_workspace / ".agent" / "agent.md"
    # 'tools' key is a string instead of a list
    agent_md.write_text(
        "---\ntools: not_a_list_string\n---\n",
        encoding="utf-8"
    )

    engine = AgentEngine(workspace_path=str(temp_workspace), bypass_onboarding=True)
    router = AgentRouter(engine, session_id="test-allowlist-session", agent_name="tester")

    # Expect fail-closed (returns empty list)
    res = router._resolve_allowed_tools(None)
    assert res == []
