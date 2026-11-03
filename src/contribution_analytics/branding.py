"""Resolve generic application identity from the application repository."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Branding:
    """User-facing and filename-safe application identity."""

    display_name: str
    slug: str

    @property
    def title(self) -> str:
        """Return the dashboard and report title."""
        return f"{self.display_name}"


def repository_name(remote_url: str) -> str | None:
    """Extract a repository name from HTTPS or SSH Git remote URLs."""
    value = remote_url.strip().rstrip("/")
    if not value or "/" not in value and ":" not in value:
        return None
    candidate = re.split(r"[/:]", value)[-1]
    candidate = re.sub(r"\.git$", "", candidate, flags=re.IGNORECASE)
    return candidate or None


def display_name(value: str) -> str:
    """Turn a repository-style name into a readable display name."""
    words = re.sub(r"[_-]+", " ", value).strip()
    return re.sub(r"\s+", " ", words).title()


def filename_slug(value: str) -> str:
    """Create a stable, safe filename component from arbitrary text."""
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "contribution-analytics"


def origin_url(root: Path) -> str | None:
    """Read this application's origin URL without using the caller's directory."""
    completed = subprocess.run(
        ["git", "-C", str(root), "remote", "get-url", "origin"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return completed.stdout.strip() if completed.returncode == 0 else None


def resolve_branding(root: Path, configured_name: str | None = None) -> Branding:
    """Resolve branding from override, app remote, root directory, then fallback."""
    source = configured_name or repository_name(origin_url(root) or "") or root.name or "Contribution Analytics"
    name = display_name(source)
    return Branding(display_name=name, slug=filename_slug(name))
