"""Tests for the generic package namespace and entry point."""

import subprocess
import sys
from pathlib import Path


def test_generic_package_imports() -> None:
    """The public generic package imports without the legacy namespace."""
    from contribution_analytics import git

    assert callable(git.analyze_repo)


def test_cli_help_uses_dynamic_application_identity() -> None:
    """The CLI imports successfully and exposes its dynamic title."""
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run([sys.executable, "main.py", "--help"], cwd=root, capture_output=True, text=True, check=True)
    assert "GitHub Contribution Analytics" in result.stdout
