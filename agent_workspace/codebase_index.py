"""Read-only local code graph indexer for LAS structural memory."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


class CodebaseIndexError(ValueError):
    """Raised when code graph indexing cannot safely proceed."""


@dataclass(frozen=True)
class CodebaseIndexResult:
    database_path: Path
    files_indexed: int
    symbols_indexed: int
    imports_indexed: int
    calls_indexed: int
    routes_indexed: int
    configs_indexed: int
    tests_indexed: int


CODE_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".jsx"}
CONFIG_SUFFIXES = {".json", ".yaml", ".yml", ".toml"}
DEFAULT_OUTPUT = ".agent/codebase-memory/code_graph.sqlite"
DEFAULT_MAX_FILE_BYTES = 512 * 1024
IGNORED_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "dist",
    "node_modules",
    "target",
}
ROUTE_METHODS = {"get", "post", "put", "patch", "delete", "options", "head", "websocket"}
TS_CALL_RE = re.compile(r"\b([A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)?)\s*\(")
TS_IMPORT_RE = re.compile(r"^\s*import(?:\s+.+?\s+from\s+)?[\"']([^\"']+)[\"']")
TS_FUNCTION_RE = re.compile(
    r"^\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)|"
    r"^\s*(?:export\s+)?const\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?\(?|"
    r"^\s*(?:export\s+)?class\s+([A-Za-z_$][\w$]*)"
)
CONFIG_KEY_RE = re.compile(r"^\s*[\"']?([A-Za-z0-9_.-]+)[\"']?\s*[:=]")


def index_repository(
    root: str | Path,
    output: str | Path = DEFAULT_OUTPUT,
    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
) -> CodebaseIndexResult:
    """Build a read-only source index into a local SQLite graph database."""

    root_path = Path(root).resolve()
    if not root_path.is_dir():
        raise CodebaseIndexError(f"root is not a directory: {root}")

    output_path = _resolve_output_path(root_path, output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    for candidate in (output_path, output_path.with_name(f"{output_path.name}-wal"), output_path.with_name(f"{output_path.name}-shm")):
        if candidate.exists():
            candidate.unlink()

    with sqlite3.connect(output_path) as conn:
        _initialize_schema(conn)
        counts = {
            "files": 0,
            "symbols": 0,
            "imports": 0,
            "calls": 0,
            "routes": 0,
            "configs": 0,
            "tests": 0,
        }
        for source_file in _iter_indexable_files(root_path, max_file_bytes):
            file_id = _insert_file(conn, root_path, source_file)
            counts["files"] += 1
            suffix = source_file.suffix.lower()
            if suffix == ".py":
                _index_python_file(conn, root_path, source_file, file_id, counts)
            elif suffix in {".ts", ".tsx", ".js", ".jsx"}:
                _index_script_file(conn, source_file, file_id, counts)
            elif suffix in CONFIG_SUFFIXES:
                _index_config_file(conn, source_file, file_id, counts)
        _write_metadata(conn, root_path)

    return CodebaseIndexResult(
        database_path=output_path,
        files_indexed=counts["files"],
        symbols_indexed=counts["symbols"],
        imports_indexed=counts["imports"],
        calls_indexed=counts["calls"],
        routes_indexed=counts["routes"],
        configs_indexed=counts["configs"],
        tests_indexed=counts["tests"],
    )


def _resolve_output_path(root: Path, output: str | Path) -> Path:
    output_path = Path(output)
    if not output_path.is_absolute():
        output_path = root / output_path
    resolved = output_path.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as error:
        raise CodebaseIndexError(f"output path escapes workspace: {output}") from error
    return resolved


def _iter_indexable_files(root: Path, max_file_bytes: int) -> Iterable[Path]:
    for current_root, dirnames, filenames in os.walk(root):
        current_path = Path(current_root)
        relative_parts = current_path.relative_to(root).parts
        dirnames[:] = sorted(
            dirname
            for dirname in dirnames
            if dirname not in IGNORED_DIRS and (*relative_parts, dirname) != (".agent", "codebase-memory")
        )
        for filename in sorted(filenames):
            path = current_path / filename
            if path.suffix.lower() not in CODE_SUFFIXES | CONFIG_SUFFIXES:
                continue
            try:
                if path.stat().st_size > max_file_bytes:
                    continue
            except OSError:
                continue
            yield path


def _initialize_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        PRAGMA journal_mode=WAL;
        CREATE TABLE metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE files (
            id INTEGER PRIMARY KEY,
            path TEXT NOT NULL UNIQUE,
            suffix TEXT NOT NULL,
            language TEXT NOT NULL,
            size_bytes INTEGER NOT NULL,
            sha256 TEXT NOT NULL,
            is_test INTEGER NOT NULL
        );
        CREATE TABLE symbols (
            id INTEGER PRIMARY KEY,
            file_id INTEGER NOT NULL REFERENCES files(id),
            name TEXT NOT NULL,
            qualname TEXT NOT NULL,
            kind TEXT NOT NULL,
            line INTEGER NOT NULL,
            column INTEGER NOT NULL
        );
        CREATE TABLE imports (
            id INTEGER PRIMARY KEY,
            file_id INTEGER NOT NULL REFERENCES files(id),
            module TEXT NOT NULL,
            name TEXT,
            line INTEGER NOT NULL
        );
        CREATE TABLE calls (
            id INTEGER PRIMARY KEY,
            file_id INTEGER NOT NULL REFERENCES files(id),
            caller_symbol_id INTEGER REFERENCES symbols(id),
            callee TEXT NOT NULL,
            line INTEGER NOT NULL
        );
        CREATE TABLE routes (
            id INTEGER PRIMARY KEY,
            file_id INTEGER NOT NULL REFERENCES files(id),
            method TEXT NOT NULL,
            route_path TEXT NOT NULL,
            handler TEXT NOT NULL,
            line INTEGER NOT NULL
        );
        CREATE TABLE configs (
            id INTEGER PRIMARY KEY,
            file_id INTEGER NOT NULL REFERENCES files(id),
            key TEXT NOT NULL,
            value_preview TEXT NOT NULL,
            line INTEGER NOT NULL
        );
        CREATE TABLE tests (
            id INTEGER PRIMARY KEY,
            file_id INTEGER NOT NULL REFERENCES files(id),
            symbol_id INTEGER REFERENCES symbols(id),
            framework TEXT NOT NULL,
            name TEXT NOT NULL,
            line INTEGER NOT NULL
        );
        CREATE INDEX idx_symbols_qualname ON symbols(qualname);
        CREATE INDEX idx_imports_module ON imports(module);
        CREATE INDEX idx_calls_callee ON calls(callee);
        CREATE INDEX idx_routes_path ON routes(route_path);
        CREATE INDEX idx_configs_key ON configs(key);
        """
    )


def _insert_file(conn: sqlite3.Connection, root: Path, path: Path) -> int:
    data = path.read_bytes()
    language = _language_for_suffix(path.suffix.lower())
    relative = path.relative_to(root).as_posix()
    is_test = int(_is_test_path(relative))
    cursor = conn.execute(
        """
        INSERT INTO files(path, suffix, language, size_bytes, sha256, is_test)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (relative, path.suffix.lower(), language, len(data), hashlib.sha256(data).hexdigest(), is_test),
    )
    return int(cursor.lastrowid)


def _language_for_suffix(suffix: str) -> str:
    return {
        ".py": "python",
        ".ts": "typescript",
        ".tsx": "typescript-react",
        ".js": "javascript",
        ".jsx": "javascript-react",
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".toml": "toml",
    }.get(suffix, "unknown")


def _is_test_path(relative_path: str) -> bool:
    normalized = relative_path.lower()
    name = Path(relative_path).name.lower()
    return "/tests/" in f"/{normalized}" or name.startswith("test_") or name.endswith(".test.tsx")


def _index_python_file(
    conn: sqlite3.Connection,
    root: Path,
    path: Path,
    file_id: int,
    counts: dict[str, int],
) -> None:
    try:
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text)
    except (OSError, SyntaxError, UnicodeDecodeError):
        return

    module_name = path.relative_to(root).with_suffix("").as_posix().replace("/", ".")
    symbol_ids: dict[str, int] = {}
    module_id = _insert_symbol(conn, file_id, module_name, module_name, "module", 1, 0)
    symbol_ids[module_name] = module_id
    counts["symbols"] += 1

    symbol_nodes = list(_walk_python_symbols(tree))
    function_ranges: list[tuple[int, int, int]] = []
    for parent_stack, node in symbol_nodes:
        name = getattr(node, "name", "")
        qualname = ".".join([module_name, *parent_stack, name])
        kind = "class" if isinstance(node, ast.ClassDef) else "function"
        symbol_id = _insert_symbol(conn, file_id, name, qualname, kind, node.lineno, node.col_offset)
        symbol_ids[qualname] = symbol_id
        counts["symbols"] += 1
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            function_ranges.append((node.lineno, getattr(node, "end_lineno", node.lineno), symbol_id))
        if _is_python_test(path, name, kind):
            _insert_test(conn, file_id, symbol_id, "pytest", name, node.lineno)
            counts["tests"] += 1
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            counts["routes"] += _index_python_routes(conn, file_id, qualname, node)

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                _insert_import(conn, file_id, alias.name, alias.asname, node.lineno)
                counts["imports"] += 1
        elif isinstance(node, ast.ImportFrom):
            module = "." * node.level + (node.module or "")
            for alias in node.names:
                _insert_import(conn, file_id, module, alias.name, node.lineno)
                counts["imports"] += 1
        elif isinstance(node, ast.Call):
            callee = _python_callee_name(node.func)
            if callee:
                caller_id = _find_python_caller_symbol(function_ranges, module_id, node.lineno)
                _insert_call(conn, file_id, caller_id, callee, node.lineno)
                counts["calls"] += 1


def _walk_python_symbols(tree: ast.AST) -> Iterable[tuple[list[str], ast.AST]]:
    def visit(node: ast.AST, stack: list[str]) -> Iterable[tuple[list[str], ast.AST]]:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                yield stack, child
                yield from visit(child, [*stack, child.name])
            else:
                yield from visit(child, stack)

    yield from visit(tree, [])


def _python_callee_name(func: ast.AST) -> str | None:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        parent = _python_callee_name(func.value)
        return f"{parent}.{func.attr}" if parent else func.attr
    return None


def _find_python_caller_symbol(function_ranges: list[tuple[int, int, int]], module_id: int, line: int) -> int:
    best: tuple[int, int] | None = None
    best_symbol_id = module_id
    for start, end, symbol_id in function_ranges:
        if start <= line <= end:
            span = end - start
            if best is None or span < best[0]:
                best = (span, start)
                best_symbol_id = symbol_id
    return best_symbol_id


def _index_python_routes(conn: sqlite3.Connection, file_id: int, qualname: str, node: ast.AST) -> int:
    count = 0
    decorators = getattr(node, "decorator_list", [])
    for decorator in decorators:
        if not isinstance(decorator, ast.Call):
            continue
        method = _python_route_method(decorator.func)
        if not method or not decorator.args:
            continue
        route_arg = decorator.args[0]
        if isinstance(route_arg, ast.Constant) and isinstance(route_arg.value, str):
            _insert_route(conn, file_id, method, route_arg.value, qualname, node.lineno)
            count += 1
    return count


def _python_route_method(func: ast.AST) -> str | None:
    if isinstance(func, ast.Attribute) and func.attr.lower() in ROUTE_METHODS:
        return func.attr.upper()
    return None


def _is_python_test(path: Path, name: str, kind: str) -> bool:
    return _is_test_path(path.as_posix()) and (name.startswith("test_") or (kind == "class" and name.startswith("Test")))


def _index_script_file(conn: sqlite3.Connection, path: Path, file_id: int, counts: dict[str, int]) -> None:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return

    current_symbol_id: int | None = None
    for line_number, line in enumerate(lines, start=1):
        import_match = TS_IMPORT_RE.search(line)
        if import_match:
            _insert_import(conn, file_id, import_match.group(1), None, line_number)
            counts["imports"] += 1

        symbol_match = TS_FUNCTION_RE.search(line)
        if symbol_match:
            name = next(group for group in symbol_match.groups() if group)
            kind = "class" if line.lstrip().startswith(("class", "export class")) else "function"
            current_symbol_id = _insert_symbol(conn, file_id, name, name, kind, line_number, 0)
            counts["symbols"] += 1
            if _is_test_path(path.as_posix()) or name.endswith("Test") or name.startswith("test"):
                _insert_test(conn, file_id, current_symbol_id, "frontend", name, line_number)
                counts["tests"] += 1

        for call_match in TS_CALL_RE.finditer(line):
            callee = call_match.group(1)
            if callee in {"if", "for", "while", "switch", "return", "function"}:
                continue
            _insert_call(conn, file_id, current_symbol_id, callee, line_number)
            counts["calls"] += 1

        route_match = re.search(r"\b(?:app|router)\.(get|post|put|patch|delete)\(\s*[\"']([^\"']+)[\"']", line)
        if route_match:
            _insert_route(conn, file_id, route_match.group(1).upper(), route_match.group(2), "script-route", line_number)
            counts["routes"] += 1


def _index_config_file(conn: sqlite3.Connection, path: Path, file_id: int, counts: dict[str, int]) -> None:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return
    for line_number, line in enumerate(lines, start=1):
        match = CONFIG_KEY_RE.search(line)
        if not match:
            continue
        _insert_config(conn, file_id, match.group(1), "<present>", line_number)
        counts["configs"] += 1


def _insert_symbol(
    conn: sqlite3.Connection,
    file_id: int,
    name: str,
    qualname: str,
    kind: str,
    line: int,
    column: int,
) -> int:
    cursor = conn.execute(
        "INSERT INTO symbols(file_id, name, qualname, kind, line, column) VALUES (?, ?, ?, ?, ?, ?)",
        (file_id, name, qualname, kind, line, column),
    )
    return int(cursor.lastrowid)


def _insert_import(conn: sqlite3.Connection, file_id: int, module: str, name: str | None, line: int) -> None:
    conn.execute("INSERT INTO imports(file_id, module, name, line) VALUES (?, ?, ?, ?)", (file_id, module, name, line))


def _insert_call(conn: sqlite3.Connection, file_id: int, caller_symbol_id: int | None, callee: str, line: int) -> None:
    conn.execute(
        "INSERT INTO calls(file_id, caller_symbol_id, callee, line) VALUES (?, ?, ?, ?)",
        (file_id, caller_symbol_id, callee, line),
    )


def _insert_route(conn: sqlite3.Connection, file_id: int, method: str, route_path: str, handler: str, line: int) -> None:
    conn.execute(
        "INSERT INTO routes(file_id, method, route_path, handler, line) VALUES (?, ?, ?, ?, ?)",
        (file_id, method, route_path, handler, line),
    )


def _insert_config(conn: sqlite3.Connection, file_id: int, key: str, value_preview: str, line: int) -> None:
    conn.execute(
        "INSERT INTO configs(file_id, key, value_preview, line) VALUES (?, ?, ?, ?)",
        (file_id, key, value_preview, line),
    )


def _insert_test(
    conn: sqlite3.Connection,
    file_id: int,
    symbol_id: int | None,
    framework: str,
    name: str,
    line: int,
) -> None:
    conn.execute(
        "INSERT INTO tests(file_id, symbol_id, framework, name, line) VALUES (?, ?, ?, ?, ?)",
        (file_id, symbol_id, framework, name, line),
    )


def _write_metadata(conn: sqlite3.Connection, root: Path) -> None:
    metadata = {
        "schema_version": "0.1.0",
        "root": str(root),
        "mode": "read_only_index",
    }
    conn.executemany("INSERT INTO metadata(key, value) VALUES (?, ?)", metadata.items())


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build the LAS local code graph SQLite index.")
    parser.add_argument("--root", default=".", help="Workspace root. Defaults to current directory.")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help=f"SQLite output path. Defaults to {DEFAULT_OUTPUT}.")
    parser.add_argument("--max-file-bytes", type=int, default=DEFAULT_MAX_FILE_BYTES)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        result = index_repository(args.root, args.output, args.max_file_bytes)
    except CodebaseIndexError as error:
        parser.exit(1, f"Codebase index failed: {error}\n")

    print(
        "Code graph indexed: "
        f"{result.files_indexed} file(s), "
        f"{result.symbols_indexed} symbol(s), "
        f"{result.imports_indexed} import(s), "
        f"{result.calls_indexed} call(s), "
        f"{result.routes_indexed} route(s), "
        f"{result.configs_indexed} config key(s), "
        f"{result.tests_indexed} test(s) -> {result.database_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
