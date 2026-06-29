import json
from pathlib import Path

import pytest

from agent_workspace.codebase_index import index_repository
from agent_workspace.core.engine import AgentEngine
from agent_workspace.skills.tool_codebase_memory import (
    CodeDetectChangeImpactArgs,
    CodeGetArchitectureArgs,
    CodeGetSnippetArgs,
    CodeIndexRepoArgs,
    CodeSearchSymbolArgs,
    CodeTraceCallPathArgs,
    code_detect_change_impact,
    code_get_architecture,
    code_get_snippet,
    code_index_repo,
    code_search_symbol,
    code_trace_call_path,
)


def _workspace(tmp_path: Path) -> Path:
    source = tmp_path / "agent_workspace" / "api.py"
    source.parent.mkdir(parents=True)
    source.write_text(
        """
from fastapi import FastAPI

app = FastAPI()

def helper():
    return "ok"

@app.get("/health")
def health():
    return helper()
""",
        encoding="utf-8",
    )
    tests = tmp_path / "agent_workspace" / "tests" / "test_api.py"
    tests.parent.mkdir(parents=True)
    tests.write_text(
        """
from agent_workspace.api import health

def test_health():
    assert health() == "ok"
""",
        encoding="utf-8",
    )
    component = tmp_path / "viewer" / "src" / "Panel.tsx"
    component.parent.mkdir(parents=True)
    component.write_text(
        """
import React from "react";

export function Panel() {
  return React.createElement("div");
}
""",
        encoding="utf-8",
    )
    (tmp_path / "config.yaml").write_text("api_key: redacted\nmode: test\n", encoding="utf-8")
    index_repository(tmp_path)
    return tmp_path


def _loads(payload: str) -> dict:
    return json.loads(payload)


def test_code_graph_tools_query_indexed_workspace(tmp_path):
    root = _workspace(tmp_path)
    context = {"workspace_path": str(root)}

    search = _loads(code_search_symbol(CodeSearchSymbolArgs(query="health"), context))
    assert search["results"][0]["qualname"] == "agent_workspace.api.health"

    outbound = _loads(code_trace_call_path(CodeTraceCallPathArgs(symbol="health"), context))
    assert any(edge["callee"] == "helper" for edge in outbound["edges"])

    inbound = _loads(code_trace_call_path(CodeTraceCallPathArgs(symbol="health", direction="inbound"), context))
    assert any(edge["caller"] == "agent_workspace.tests.test_api.test_health" for edge in inbound["edges"])

    impact = _loads(
        code_detect_change_impact(
            CodeDetectChangeImpactArgs(changed_files=["agent_workspace/api.py"]),
            context,
        )
    )
    assert impact["impacts"][0]["route_count"] == 1
    assert impact["impacts"][0]["importer_count"] >= 1

    architecture = _loads(code_get_architecture(CodeGetArchitectureArgs(limit=3), context))
    assert architecture["totals"]["routes"] == 1
    assert any(row["language"] == "python" for row in architecture["languages"])

    snippet = _loads(code_get_snippet(CodeGetSnippetArgs(symbol="health", context_lines=2), context))
    assert snippet["path"] == "agent_workspace/api.py"
    assert any("def health" in line["text"] for line in snippet["snippet"])


def test_code_index_repo_tool_refreshes_database(tmp_path):
    context = {"workspace_path": str(tmp_path)}
    (tmp_path / "agent_workspace").mkdir()
    (tmp_path / "agent_workspace" / "module.py").write_text("def created():\n    return 1\n", encoding="utf-8")

    result = _loads(code_index_repo(CodeIndexRepoArgs(root="."), context))

    assert result["files_indexed"] == 1
    assert result["symbols_indexed"] >= 2
    assert (tmp_path / ".agent" / "codebase-memory" / "code_graph.sqlite").is_file()


def test_code_graph_query_tools_do_not_create_missing_index(tmp_path):
    context = {"workspace_path": str(tmp_path)}
    (tmp_path / "agent_workspace").mkdir()
    (tmp_path / "agent_workspace" / "module.py").write_text("def created():\n    return 1\n", encoding="utf-8")

    with pytest.raises(FileNotFoundError, match="Run code_index_repo first"):
        code_search_symbol(CodeSearchSymbolArgs(query="created"), context)

    assert not (tmp_path / ".agent" / "codebase-memory" / "code_graph.sqlite").exists()


def test_code_graph_tools_reject_workspace_escape(tmp_path):
    root = _workspace(tmp_path)
    context = {"workspace_path": str(root)}

    with pytest.raises(PermissionError, match="escapes workspace"):
        code_detect_change_impact(CodeDetectChangeImpactArgs(changed_files=["../outside.py"]), context)


def test_agent_engine_registers_code_graph_tools_and_enforces_allowlist():
    repo_root = Path(__file__).resolve().parents[2]
    engine = AgentEngine(workspace_path=str(repo_root / "agent_workspace"))
    engine.complete_onboarding()

    tool_names = {schema["name"] for schema in engine.get_tool_schemas()}

    assert {
        "code_index_repo",
        "code_search_symbol",
        "code_trace_call_path",
        "code_detect_change_impact",
        "code_get_architecture",
        "code_get_snippet",
    }.issubset(tool_names)

    with pytest.raises(PermissionError, match="is not allowed"):
        engine.execute_tool(
            "code_get_architecture",
            {"limit": 1},
            allowed_tools=["code_search_symbol"],
        )
