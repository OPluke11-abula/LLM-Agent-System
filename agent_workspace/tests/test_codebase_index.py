import sqlite3
from pathlib import Path

import pytest

from agent_workspace.codebase_index import CodebaseIndexError, index_repository


def _fetch_values(db_path: Path, query: str) -> list[tuple]:
    with sqlite3.connect(db_path) as conn:
        return list(conn.execute(query))


def test_codebase_index_records_python_symbols_routes_calls_and_tests(tmp_path):
    api_file = tmp_path / "agent_workspace" / "api.py"
    api_file.parent.mkdir(parents=True)
    api_file.write_text(
        """
from fastapi import FastAPI
from .core import helper

app = FastAPI()

class Service:
    def run(self):
        return helper()

@app.get("/health")
def health():
    service = Service()
    return service.run()
""",
        encoding="utf-8",
    )
    test_file = tmp_path / "agent_workspace" / "tests" / "test_api.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text(
        """
def test_health():
    assert True
""",
        encoding="utf-8",
    )

    result = index_repository(tmp_path)

    assert result.files_indexed == 2
    assert result.symbols_indexed >= 5
    assert result.imports_indexed >= 2
    assert result.calls_indexed >= 3
    assert result.routes_indexed == 1
    assert result.tests_indexed == 1

    routes = _fetch_values(result.database_path, "SELECT method, route_path, handler FROM routes")
    tests = _fetch_values(result.database_path, "SELECT framework, name FROM tests")
    calls = _fetch_values(result.database_path, "SELECT callee FROM calls WHERE callee = 'Service'")

    assert routes == [("GET", "/health", "agent_workspace.api.health")]
    assert tests == [("pytest", "test_health")]
    assert calls == [("Service",)]


def test_codebase_index_records_script_symbols_imports_and_config_keys_without_values(tmp_path):
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
    config = tmp_path / "config.yaml"
    config.write_text("api_key: secret-value\nmode: local\n", encoding="utf-8")

    result = index_repository(tmp_path)

    symbols = _fetch_values(result.database_path, "SELECT name, kind FROM symbols WHERE name = 'Panel'")
    imports = _fetch_values(result.database_path, "SELECT module FROM imports")
    configs = _fetch_values(result.database_path, "SELECT key, value_preview FROM configs ORDER BY key")

    assert symbols == [("Panel", "function")]
    assert imports == [("react",)]
    assert configs == [("api_key", "<present>"), ("mode", "<present>")]


def test_codebase_index_ignores_generated_dependency_dirs(tmp_path):
    ignored_file = tmp_path / "viewer" / "node_modules" / "pkg" / "index.js"
    ignored_file.parent.mkdir(parents=True)
    ignored_file.write_text("export function ignored() {}", encoding="utf-8")
    source_file = tmp_path / "viewer" / "src" / "index.ts"
    source_file.parent.mkdir(parents=True)
    source_file.write_text("export function kept() { return 1; }", encoding="utf-8")

    result = index_repository(tmp_path)
    files = _fetch_values(result.database_path, "SELECT path FROM files")

    assert files == [("viewer/src/index.ts",)]


def test_codebase_index_rejects_output_path_escape(tmp_path):
    with pytest.raises(CodebaseIndexError, match="output path escapes workspace"):
        index_repository(tmp_path, tmp_path.parent / "outside.sqlite")
