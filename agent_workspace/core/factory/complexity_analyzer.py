"""AST-based Code Complexity and Dependency Coupling Analyzer (Phase 101).

Calculates cyclomatic complexity, afferent/efferent module coupling, lines of code,
and composite risk scores across repository modules using standard Python AST traversal.
"""

from __future__ import annotations

import ast
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, Union

from agent_workspace.core.factory.models import CodeComplexityMetrics

logger = logging.getLogger("ComplexityAnalyzer")


class CyclomaticComplexityVisitor(ast.NodeVisitor):
    """AST visitor to compute standard McCabe cyclomatic complexity."""

    def __init__(self) -> None:
        self.complexity: int = 1
        self.function_count: int = 0
        self.class_count: int = 0
        self.imported_modules: Set[str] = set()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.function_count += 1
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.function_count += 1
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.class_count += 1
        self.generic_visit(node)

    def visit_If(self, node: ast.If) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_IfExp(self, node: ast.IfExp) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_While(self, node: ast.While) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_With(self, node: ast.With) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_AsyncWith(self, node: ast.AsyncWith) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_Assert(self, node: ast.Assert) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        # Each operand after the first represents a conditional decision branch
        if len(node.values) > 1:
            self.complexity += len(node.values) - 1
        self.generic_visit(node)

    def visit_comprehension(self, node: ast.comprehension) -> None:
        self.complexity += 1 + len(node.ifs)
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.imported_modules.add(alias.name.split(".")[0])
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module:
            self.imported_modules.add(node.module.split(".")[0])
        self.generic_visit(node)


class CodeComplexityAnalyzer:
    """Enterprise code complexity and coupling audit engine."""

    def __init__(self, root_dir: Optional[Union[str, Path]] = None) -> None:
        self.root_dir = Path(root_dir) if root_dir else None

    def analyze_source(self, code: str, file_path: str = "snippet.py") -> CodeComplexityMetrics:
        """Analyzes a Python code snippet or file string and returns complexity metrics."""
        loc = len([line for line in code.splitlines() if line.strip() and not line.strip().startswith("#")])

        try:
            tree = ast.parse(code, filename=file_path)
            visitor = CyclomaticComplexityVisitor()
            visitor.visit(tree)

            metrics = CodeComplexityMetrics(
                file_path=file_path,
                loc=loc,
                cyclomatic_complexity=visitor.complexity,
                function_count=visitor.function_count,
                class_count=visitor.class_count,
                efferent_coupling=len(visitor.imported_modules),
            )
        except SyntaxError as e:
            logger.warning("SyntaxError while parsing %s: %s; falling back to line estimation", file_path, e)
            metrics = CodeComplexityMetrics(
                file_path=file_path,
                loc=loc,
                cyclomatic_complexity=max(1, loc // 15),
                function_count=0,
                class_count=0,
                efferent_coupling=0,
            )

        metrics.compute_risk()
        return metrics

    def analyze_file(self, file_path: Union[str, Path]) -> CodeComplexityMetrics:
        """Reads and analyzes a single file from disk."""
        path = Path(file_path)
        if not path.is_file():
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            code = path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            logger.error("Failed to read file %s: %s", file_path, e)
            raise

        rel_path = str(path.relative_to(self.root_dir)) if self.root_dir and path.is_relative_to(self.root_dir) else str(path)
        return self.analyze_source(code, file_path=rel_path)

    def analyze_repository(
        self,
        target_dir: Optional[Union[str, Path]] = None,
        extensions: Optional[List[str]] = None,
        max_files: int = 100,
    ) -> Dict[str, CodeComplexityMetrics]:
        """Scans a repository directory, computing per-file complexity and cross-module coupling."""
        base_dir = Path(target_dir or self.root_dir or ".")
        valid_exts = set(extensions or [".py"])

        raw_metrics: Dict[str, CodeComplexityMetrics] = {}
        file_imports: Dict[str, Set[str]] = {}

        for p in base_dir.rglob("*"):
            if not p.is_file() or p.suffix not in valid_exts:
                continue
            # Skip virtual environments, git directories, node_modules, and cache
            parts = p.parts
            if any(ign in parts for ign in [".venv", "venv", ".git", "node_modules", "__pycache__", ".agent"]):
                continue

            if len(raw_metrics) >= max_files:
                break

            try:
                code = p.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(code, filename=str(p))
                visitor = CyclomaticComplexityVisitor()
                visitor.visit(tree)

                rel_str = str(p.relative_to(base_dir)).replace("\\", "/")
                loc = len([line for line in code.splitlines() if line.strip() and not line.strip().startswith("#")])

                raw_metrics[rel_str] = CodeComplexityMetrics(
                    file_path=rel_str,
                    loc=loc,
                    cyclomatic_complexity=visitor.complexity,
                    function_count=visitor.function_count,
                    class_count=visitor.class_count,
                    efferent_coupling=len(visitor.imported_modules),
                )
                # Store file stem for coupling calculation
                file_imports[rel_str] = visitor.imported_modules
            except Exception as e:
                logger.debug("Skipped %s during repo analysis: %s", p, e)

        # Compute afferent coupling across scanned files
        stem_to_file = {Path(f).stem: f for f in raw_metrics}
        for current_file, imported_mods in file_imports.items():
            for mod in imported_mods:
                if mod in stem_to_file:
                    target_file = stem_to_file[mod]
                    if target_file != current_file:
                        raw_metrics[target_file].afferent_coupling += 1

        # Re-compute risk scores with finalized coupling metrics
        for metric in raw_metrics.values():
            metric.compute_risk()

        return raw_metrics
