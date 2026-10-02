import json
import sqlite3
from pathlib import Path
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from agent_workspace.codebase_index import DEFAULT_OUTPUT, index_repository


MAX_LIMIT = 50


def _workspace_root(context: Optional[dict[str, Any]] = None) -> Path:
    raw = context.get("workspace_path") if context else None
    candidate = Path(raw or ".").resolve()
    if candidate.name == "agent_workspace" and (candidate.parent / ".agent").is_dir():
        return candidate.parent
    return candidate


def _resolve_workspace_path(root: Path, value: str | Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = root / path
    resolved = path.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as error:
        raise PermissionError(f"path escapes workspace: {value}") from error
    return resolved


def _db_path(root: Path, value: str | Path = DEFAULT_OUTPUT) -> Path:
    path = _resolve_workspace_path(root, value)
    if not path.is_file():
        raise FileNotFoundError(f"code graph index not found: {path}. Run code_index_repo first.")
    return path


def _bounded_limit(value: int) -> int:
    return max(1, min(MAX_LIMIT, value))


def _rows(db: Path, query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        return [dict(row) for row in conn.execute(query, params)]


def _json(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


class CodeIndexRepoArgs(BaseModel):
    root: str = Field(default=".", description="Workspace root to index.")
    output: str = Field(default=DEFAULT_OUTPUT, description="Workspace-relative SQLite output path.")
    max_file_bytes: int = Field(default=512 * 1024, description="Maximum file size to index.")


def code_index_repo(args: CodeIndexRepoArgs, context: Optional[dict[str, Any]] = None) -> str:
    """Build or refresh the local read-only code graph SQLite index."""

    root = _resolve_workspace_path(_workspace_root(context), args.root)
    output = _resolve_workspace_path(root, args.output)
    result = index_repository(root, output, args.max_file_bytes)
    return _json(
        {
            "database_path": str(result.database_path),
            "files_indexed": result.files_indexed,
            "symbols_indexed": result.symbols_indexed,
            "imports_indexed": result.imports_indexed,
            "calls_indexed": result.calls_indexed,
            "routes_indexed": result.routes_indexed,
            "configs_indexed": result.configs_indexed,
            "tests_indexed": result.tests_indexed,
        }
    )


class CodeSearchSymbolArgs(BaseModel):
    query: str = Field(description="Symbol name or qualified-name substring.")
    kind: Optional[str] = Field(default=None, description="Optional symbol kind filter.")
    limit: int = Field(default=10, description="Maximum result count.")


def code_search_symbol(args: CodeSearchSymbolArgs, context: Optional[dict[str, Any]] = None) -> str:
    """Search symbols in the local code graph index."""

    root = _workspace_root(context)
    db = _db_path(root)
    limit = _bounded_limit(args.limit)
    pattern = f"%{args.query}%"
    params: tuple[Any, ...]
    if args.kind:
        query = """
            SELECT symbols.name, symbols.qualname, symbols.kind, symbols.line, files.path
            FROM symbols
            JOIN files ON files.id = symbols.file_id
            WHERE (symbols.name LIKE ? OR symbols.qualname LIKE ?) AND symbols.kind = ?
            ORDER BY files.is_test ASC, symbols.qualname ASC
            LIMIT ?
        """
        params = (pattern, pattern, args.kind, limit)
    else:
        query = """
            SELECT symbols.name, symbols.qualname, symbols.kind, symbols.line, files.path
            FROM symbols
            JOIN files ON files.id = symbols.file_id
            WHERE symbols.name LIKE ? OR symbols.qualname LIKE ?
            ORDER BY files.is_test ASC, symbols.qualname ASC
            LIMIT ?
        """
        params = (pattern, pattern, limit)
    return _json({"query": args.query, "results": _rows(db, query, params)})


class CodeTraceCallPathArgs(BaseModel):
    symbol: str = Field(description="Symbol name or qualified-name substring.")
    direction: Literal["inbound", "outbound"] = Field(
        default="outbound",
        description="Trace outbound calls from the symbol or inbound calls to the symbol.",
    )
    limit: int = Field(default=20, description="Maximum edge count.")


def code_trace_call_path(args: CodeTraceCallPathArgs, context: Optional[dict[str, Any]] = None) -> str:
    """Trace direct inbound or outbound call edges for a symbol."""

    root = _workspace_root(context)
    db = _db_path(root)
    limit = _bounded_limit(args.limit)
    symbol_rows = _rows(
        db,
        """
        SELECT symbols.id, symbols.name, symbols.qualname, symbols.line, files.path
        FROM symbols
        JOIN files ON files.id = symbols.file_id
        WHERE symbols.name LIKE ? OR symbols.qualname LIKE ?
        ORDER BY files.is_test ASC, symbols.qualname ASC
        LIMIT 1
        """,
        (f"%{args.symbol}%", f"%{args.symbol}%"),
    )
    if not symbol_rows:
        return _json({"symbol": args.symbol, "edges": []})
    symbol = symbol_rows[0]
    if args.direction == "outbound":
        edges = _rows(
            db,
            """
            SELECT calls.callee, calls.line, files.path
            FROM calls
            JOIN files ON files.id = calls.file_id
            WHERE calls.caller_symbol_id = ?
            ORDER BY calls.line ASC
            LIMIT ?
            """,
            (symbol["id"], limit),
        )
    else:
        edges = _rows(
            db,
            """
            SELECT caller.qualname AS caller, calls.line, files.path
            FROM calls
            JOIN files ON files.id = calls.file_id
            LEFT JOIN symbols AS caller ON caller.id = calls.caller_symbol_id
            WHERE calls.callee = ? OR calls.callee LIKE ?
            ORDER BY files.is_test ASC, files.path ASC, calls.line ASC
            LIMIT ?
            """,
            (symbol["name"], f"%.{symbol['name']}", limit),
        )
    return _json({"symbol": symbol, "direction": args.direction, "edges": edges})


class CodeDetectChangeImpactArgs(BaseModel):
    changed_files: list[str] = Field(description="Workspace-relative changed file paths.")
    limit: int = Field(default=20, description="Maximum rows per impact category.")


def code_detect_change_impact(args: CodeDetectChangeImpactArgs, context: Optional[dict[str, Any]] = None) -> str:
    """Summarize likely structural impact for changed files using the local code graph."""

    root = _workspace_root(context)
    db = _db_path(root)
    limit = _bounded_limit(args.limit)
    impacts = []
    for changed_file in args.changed_files[:MAX_LIMIT]:
        relative = _resolve_workspace_path(root, changed_file).relative_to(root).as_posix()
        file_rows = _rows(db, "SELECT id, path, language, is_test FROM files WHERE path = ?", (relative,))
        if not file_rows:
            impacts.append({"path": relative, "indexed": False})
            continue
        file_id = file_rows[0]["id"]
        symbols = _rows(
            db,
            "SELECT name, qualname, kind, line FROM symbols WHERE file_id = ? ORDER BY line ASC LIMIT ?",
            (file_id, limit),
        )
        routes = _rows(
            db,
            "SELECT method, route_path, handler, line FROM routes WHERE file_id = ? ORDER BY line ASC LIMIT ?",
            (file_id, limit),
        )
        tests = _rows(
            db,
            "SELECT framework, name, line FROM tests WHERE file_id = ? ORDER BY line ASC LIMIT ?",
            (file_id, limit),
        )
        outbound = _rows(
            db,
            "SELECT DISTINCT callee FROM calls WHERE file_id = ? ORDER BY callee ASC LIMIT ?",
            (file_id, limit),
        )
        module_hint = relative.rsplit(".", 1)[0].replace("/", ".")
        importers = _rows(
            db,
            """
            SELECT DISTINCT files.path
            FROM imports
            JOIN files ON files.id = imports.file_id
            WHERE imports.module = ? OR imports.module LIKE ?
            ORDER BY files.is_test ASC, files.path ASC
            LIMIT ?
            """,
            (module_hint, f"%{Path(relative).stem}%", limit),
        )
        impacts.append(
            {
                "path": relative,
                "indexed": True,
                "symbol_count": len(symbols),
                "route_count": len(routes),
                "test_count": len(tests),
                "outbound_call_count": len(outbound),
                "importer_count": len(importers),
                "symbols": symbols,
                "routes": routes,
                "tests": tests,
                "outbound_callees": outbound,
                "importers": importers,
            }
        )
    return _json({"changed_files": args.changed_files, "impacts": impacts})


class CodeGetArchitectureArgs(BaseModel):
    limit: int = Field(default=10, description="Maximum rows per sample section.")


def code_get_architecture(args: CodeGetArchitectureArgs, context: Optional[dict[str, Any]] = None) -> str:
    """Return a compact architecture summary from the local code graph."""

    root = _workspace_root(context)
    db = _db_path(root)
    limit = _bounded_limit(args.limit)
    return _json(
        {
            "totals": {
                "files": _rows(db, "SELECT COUNT(*) AS count FROM files")[0]["count"],
                "symbols": _rows(db, "SELECT COUNT(*) AS count FROM symbols")[0]["count"],
                "routes": _rows(db, "SELECT COUNT(*) AS count FROM routes")[0]["count"],
                "tests": _rows(db, "SELECT COUNT(*) AS count FROM tests")[0]["count"],
            },
            "languages": _rows(
                db,
                "SELECT language, COUNT(*) AS files FROM files GROUP BY language ORDER BY files DESC LIMIT ?",
                (limit,),
            ),
            "top_routes": _rows(
                db,
                "SELECT method, route_path, handler FROM routes ORDER BY route_path ASC LIMIT ?",
                (limit,),
            ),
            "largest_files": _rows(
                db,
                "SELECT path, language, size_bytes FROM files ORDER BY size_bytes DESC LIMIT ?",
                (limit,),
            ),
        }
    )


class CodeGetSnippetArgs(BaseModel):
    symbol: Optional[str] = Field(default=None, description="Symbol name or qualified-name substring.")
    path: Optional[str] = Field(default=None, description="Workspace-relative path.")
    line: Optional[int] = Field(default=None, description="Line number when path is provided.")
    context_lines: int = Field(default=4, description="Lines before and after the target.")


def code_get_snippet(args: CodeGetSnippetArgs, context: Optional[dict[str, Any]] = None) -> str:
    """Read a bounded source snippet by symbol or workspace-relative path and line."""

    root = _workspace_root(context)
    db = _db_path(root)
    target_path: Path
    target_line: int
    symbol = None
    if args.symbol:
        matches = _rows(
            db,
            """
            SELECT symbols.name, symbols.qualname, symbols.line, files.path
            FROM symbols
            JOIN files ON files.id = symbols.file_id
            WHERE symbols.name LIKE ? OR symbols.qualname LIKE ?
            ORDER BY files.is_test ASC, symbols.qualname ASC
            LIMIT 1
            """,
            (f"%{args.symbol}%", f"%{args.symbol}%"),
        )
        if not matches:
            return _json({"symbol": args.symbol, "snippet": ""})
        symbol = matches[0]
        target_path = _resolve_workspace_path(root, symbol["path"])
        target_line = int(symbol["line"])
    elif args.path and args.line:
        target_path = _resolve_workspace_path(root, args.path)
        target_line = args.line
    else:
        raise ValueError("Either symbol or both path and line must be provided.")

    lines = target_path.read_text(encoding="utf-8").splitlines()
    context_lines = max(0, min(20, args.context_lines))
    start = max(1, target_line - context_lines)
    end = min(len(lines), target_line + context_lines)
    snippet = [
        {"line": line_number, "text": lines[line_number - 1]}
        for line_number in range(start, end + 1)
    ]
    return _json(
        {
            "symbol": symbol,
            "path": target_path.relative_to(root).as_posix(),
            "start_line": start,
            "end_line": end,
            "snippet": snippet,
        }
    )
