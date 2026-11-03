"""Tests for documentation-policy enforcement."""

from pathlib import Path

from contribution_analytics.docstrings import check, undocumented_functions


def test_docstring_checker_finds_nested_functions(tmp_path: Path) -> None:
    """Nested undocumented functions include their source line in the result."""
    source = tmp_path / "sample.py"
    source.write_text('def documented():\n    """Documented."""\n    def missing():\n        pass\n', encoding="utf-8")
    assert undocumented_functions([source]) == [f"{source}:3"]


def test_project_has_complete_function_docstrings() -> None:
    """Every covered project function has a meaningful docstring."""
    root = Path(__file__).resolve().parents[1]
    assert check(root) == []
