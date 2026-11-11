"""Managed full-history clones for URL-based analysis sources."""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from contribution_analytics.config import validate_repo_url


def git_available() -> bool:
    """Report whether a usable Git executable is on PATH."""
    if not shutil.which("git"):
        return False
    return subprocess.run(["git", "--version"], capture_output=True, check=False).returncode == 0


def cache_path(name: str, url: str, root: Path) -> Path:
    """Give each configured source a safe, stable, collision-resistant cache directory."""
    label = re.sub(r"[^A-Za-z0-9_-]+", "-", name).strip("-")[:40] or "repository"
    digest = hashlib.sha256(f"{name}\0{url}".encode("utf-8")).hexdigest()[:20]
    return root / f"{label}-{digest}"


def _failure(stderr: str) -> str:
    """Classify Git failures without exposing URLs or credential-helper output."""
    message = stderr.lower()
    if any(
        token in message for token in ("authentication", "permission denied", "could not read username", "publickey")
    ):
        return "authentication failed; check your Git credential helper or SSH key"
    if any(
        token in message for token in ("could not resolve", "unable to access", "connection", "network is unreachable")
    ):
        return "network unavailable; check connectivity and retry"
    return "Git operation failed; check the URL, access, and remote repository"


def _git(*args: str, cwd: Path | None = None) -> str:
    """Execute Git without a shell, interactive credential prompts, or leaked stderr."""
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, errors="replace", env=env)
    if result.returncode:
        raise RuntimeError(_failure(result.stderr))
    return result.stdout.strip()


def inspect_cache(name: str, url: str, root: Path) -> tuple[Path, str]:
    """Inspect a managed cache without network access or working-tree changes."""
    path = cache_path(name, url, root)
    if not path.exists() and not path.is_symlink():
        return path, "not yet cached"
    if path.is_symlink() or not path.is_dir() or (path / ".git").is_symlink() or not (path / ".git").is_dir():
        return path, "corrupted cache"
    try:
        top = _git("-C", str(path), "rev-parse", "--show-toplevel")
        origin = _git("-C", str(path), "config", "--get", "remote.origin.url")
        shallow = _git("-C", str(path), "rev-parse", "--is-shallow-repository")
        _git("-C", str(path), "rev-parse", "--verify", "HEAD")
        _git("-C", str(path), "cat-file", "-e", "HEAD^{commit}")
    except RuntimeError:
        return path, "corrupted cache"
    if Path(top).resolve() != path.resolve() or origin != url or shallow != "false":
        return path, "corrupted cache"
    return path, "cached"


def _checkout_default(path: Path) -> None:
    """Move only a managed worktree to the remote's current default branch."""
    head = _git("-C", str(path), "ls-remote", "--symref", "origin", "HEAD")
    match = re.search(r"^ref: refs/heads/(.+)\s+HEAD$", head, re.MULTILINE)
    if not match:
        raise RuntimeError("Remote default branch unavailable; check the remote HEAD")
    branch = match.group(1)
    ref = f"refs/remotes/origin/{branch}"
    _git("-C", str(path), "rev-parse", "--verify", ref)
    _git("-C", str(path), "symbolic-ref", "refs/remotes/origin/HEAD", ref)
    _git("-C", str(path), "checkout", "--force", "--detach", ref)


def resolve_remote(name: str, url: str, root: Path) -> tuple[Path, str]:
    """Clone or refresh a full remote cache, retaining stale data when offline."""
    validate_repo_url(url)
    if not git_available():
        raise RuntimeError("Git executable missing; install Git or run make ensure-git")
    root.mkdir(parents=True, exist_ok=True)
    path, state = inspect_cache(name, url, root)
    if state == "corrupted cache":
        raise RuntimeError(f"{name}: corrupted cache at {path}; remove that managed directory and retry")
    if state == "not yet cached":
        with tempfile.TemporaryDirectory(prefix="clone-", dir=root) as temporary:
            staged = Path(temporary) / "repo"
            _git("clone", "--no-local", "--", url, str(staged))
            _checkout_default(staged)
            staged.rename(path)
        return path, "cloned"
    try:
        _git("-C", str(path), "fetch", "--prune", "origin", "+refs/heads/*:refs/remotes/origin/*")
        _checkout_default(path)
    except RuntimeError as error:
        return path, f"stale cached data: {error}"
    return path, "refreshed"
