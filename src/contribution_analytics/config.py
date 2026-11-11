from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import yaml


def validate_repo_url(url: str) -> None:
    """Accept Git HTTPS, SSH, and local file URLs without credentials or option injection."""
    if not isinstance(url, str) or not url or any(char.isspace() or ord(char) < 32 for char in url):
        raise ValueError("URL must be a nonempty Git URL without whitespace")
    try:
        if url.startswith("git@") and ":" in url:
            host, path = url[4:].split(":", 1)
            valid = bool(re.fullmatch(r"[A-Za-z0-9.-]+", host) and not host.startswith("-"))
        else:
            parts = urlsplit(url)
            path = parts.path
            valid = (
                parts.scheme in {"https", "ssh", "file"}
                and not parts.query
                and not parts.fragment
                and not parts.password
                and (
                    parts.scheme == "file"
                    and not parts.netloc
                    or parts.scheme != "file"
                    and bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.:-]*", parts.hostname or ""))
                )
                and (parts.scheme != "https" or not parts.username)
                and (
                    parts.scheme != "ssh"
                    or not parts.username
                    or bool(re.fullmatch(r"[A-Za-z0-9._-]+", parts.username))
                )
            )
            _ = parts.port
    except ValueError:
        valid, path = False, ""
    segments = unquote(path).split("/")
    valid = (
        valid
        and bool(segments[-1])
        and all(segment not in {".", ".."} and not segment.startswith("-") for segment in segments if segment)
    )
    valid = valid and not any(char in url for char in ("\\", "%"))
    if not valid:
        raise ValueError("Unsafe or malformed Git URL; use HTTPS, SSH, or file URL without credentials")


def config_path(explicit_path: str | Path | None, root: Path) -> Path:
    """Resolve an explicit, environment-provided, or default settings path."""
    return Path(explicit_path or os.environ.get("CONTRIBUTION_ANALYTICS_CONFIG", root / "config" / "settings.yaml"))


def load_config(path: str | Path) -> dict[str, Any]:
    """Load and validate editable YAML configuration without expanding secrets."""
    with Path(path).open(encoding="utf-8") as handle:
        config = yaml.safe_load(handle) or {}
    if not isinstance(config, dict):
        raise ValueError("Settings must be a YAML mapping")
    repos = config.get("repositories", {})
    if not isinstance(repos, dict) or not repos:
        raise ValueError("settings.repositories requires named repositories with paths or URLs")
    for name, item in repos.items():
        if not isinstance(name, str) or not name or not isinstance(item, dict):
            raise ValueError("settings.repositories requires named repository mappings")
        has_path, has_url = "path" in item, "url" in item
        if has_path == has_url:
            raise ValueError(f"Repository {name!r} must specify exactly one of path or url")
        if has_url:
            try:
                validate_repo_url(item["url"])
            except ValueError as error:
                raise ValueError(f"Repository {name!r}: {error}") from error
        elif not isinstance(item["path"], str) or not item["path"].strip():
            raise ValueError(f"Repository {name!r}: path must be a nonempty string")
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
