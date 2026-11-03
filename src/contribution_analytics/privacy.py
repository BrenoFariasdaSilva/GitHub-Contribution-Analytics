"""Privacy helpers for generated analytics artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def public_metadata(metadata: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove local repository paths before writing shareable exports."""
    return [{key: value for key, value in item.items() if key != "path"} for item in metadata]


def safe_relative_path(path: Path, root: Path) -> str:
    """Return a relative path when possible, otherwise a non-sensitive label."""
    try:
        return str(path.relative_to(root))
    except ValueError:
        return path.name
