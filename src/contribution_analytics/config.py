from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import yaml


def config_path(explicit_path: str | Path | None, root: Path) -> Path:
    """Resolve an explicit, environment-provided, or default settings path."""
    return Path(explicit_path or os.environ.get("CONTRIBUTION_ANALYTICS_CONFIG", root / "config" / "settings.yaml"))


def load_config(path: str | Path) -> dict[str, Any]:
    """Load and validate editable YAML configuration without expanding secrets."""
    with Path(path).open(encoding="utf-8") as handle:
        config = yaml.safe_load(handle) or {}
    repos = config.get("repositories", {})
    if (
        not isinstance(repos, dict)
        or not repos
        or not all(isinstance(item, dict) and item.get("path") for item in repos.values())
    ):
        raise ValueError("settings.repositories requires named repositories with paths")
    config.setdefault("timezone", "America/Sao_Paulo")
    config.setdefault("aliases", {})
    config.setdefault("exclude_dirs", [])
    config.setdefault("exclude_files", [])
    config.setdefault("bot_patterns", [])
    try:
        ZoneInfo(str(config["timezone"]))
    except ZoneInfoNotFoundError as error:
        raise ValueError(f"Invalid timezone: {config['timezone']}") from error
    config.setdefault("display_name", "")
    return config
