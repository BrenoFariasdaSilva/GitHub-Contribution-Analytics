"""AST-based documentation coverage validation."""

from __future__ import annotations

import ast
from pathlib import Path


def undocumented_functions(paths: list[Path]) -> list[str]:
    """Return path-and-line entries for every function missing a docstring."""
    missing: list[str] = []
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and ast.get_docstring(node) is None:
                missing.append(f"{path}:{node.lineno}")
    return missing


def project_python_files(root: Path) -> list[Path]:
    """List production, entry-point, and test Python files covered by the policy."""
    return (
        [root / name for name in ("app.py", "main.py")]
        + sorted((root / "src").rglob("*.py"))
        + sorted((root / "tests").rglob("*.py"))
    )


def check(root: Path) -> list[str]:
    """Check all covered files and return documentation failures."""
    return undocumented_functions(project_python_files(root))
