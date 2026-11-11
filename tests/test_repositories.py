"""Remote cache and CLI integration tests using local bare Git remotes."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

import pytest

import main
from contribution_analytics.config import load_config
from contribution_analytics.git import analyze_repo, current_loc, default_ref, load_data
from contribution_analytics.repositories import cache_path, inspect_cache, resolve_remote


def git(*args: str) -> str:
    """Run a local test Git command and return its output."""
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout.strip()


@pytest.fixture
def remote(tmp_path: Path) -> tuple[Path, Path]:
    """Create a source worktree and a full-history bare remote."""
    source, bare = tmp_path / "source", tmp_path / "remote.git"
    git("init", "-b", "main", str(source))
    git("init", "--bare", "-b", "main", str(bare))
    git("-C", str(source), "config", "user.name", "Tester")
    git("-C", str(source), "config", "user.email", "tester@example.com")
    (source / "code.py").write_text("one\n", encoding="utf-8")
    git("-C", str(source), "add", "code.py")
    git("-C", str(source), "commit", "-m", "feat: first")
    git("-C", str(source), "remote", "add", "origin", bare.as_uri())
    git("-C", str(source), "push", "-u", "origin", "main")
    return source, bare


def test_clone_reuse_refresh_default_branch_and_loc(remote, tmp_path: Path) -> None:
    """Managed clones keep full history and update LoC after a remote branch switch."""
    source, bare = remote
    root = tmp_path / "cache"
    repo, state = resolve_remote("project", bare.as_uri(), root)
    assert state == "cloned"
    assert inspect_cache("project", bare.as_uri(), root)[1] == "cached"
    assert resolve_remote("project", bare.as_uri(), root) == (repo, "refreshed")
    config = {"aliases": {}, "bot_patterns": [], "exclude_dirs": [], "exclude_files": []}
    assert len(analyze_repo("project", repo, config)[0]) == 1
    git("-C", str(source), "checkout", "-b", "next")
    (source / "code.py").write_text("one\ntwo\nthree\n", encoding="utf-8")
    git("-C", str(source), "commit", "-am", "feat: next")
    git("-C", str(source), "push", "origin", "next")
    git("-C", str(bare), "symbolic-ref", "HEAD", "refs/heads/next")
    assert resolve_remote("project", bare.as_uri(), root)[1] == "refreshed"
    assert default_ref(repo) == "origin/next"
    assert len(analyze_repo("project", repo, config)[0]) == 2
    assert current_loc("project", repo, config).iloc[0].physical_loc == 3
    assert git("-C", str(repo), "rev-parse", "--is-shallow-repository") == "false"


def test_cache_isolated_corruption_and_failed_clone(remote, tmp_path: Path) -> None:
    """Source hashes avoid collisions, and failed or damaged caches never replace another source."""
    _, bare = remote
    root = tmp_path / "cache"
    first, _ = resolve_remote("same/name", bare.as_uri(), root)
    assert cache_path("same/name", bare.as_uri(), root) != cache_path("same?name", bare.as_uri(), root)
    missing = (tmp_path / "absent.git").as_uri()
    with pytest.raises(RuntimeError):
        resolve_remote("other", missing, root)
    assert not cache_path("other", missing, root).exists()
    assert not list(root.glob("clone-*"))
    git("-C", str(first), "remote", "set-url", "origin", missing)
    assert inspect_cache("same/name", bare.as_uri(), root)[1] == "corrupted cache"
    with pytest.raises(RuntimeError, match="corrupted cache"):
        resolve_remote("same/name", bare.as_uri(), root)


def test_loc_skips_tracked_symlinks(remote, tmp_path: Path) -> None:
    """An untrusted remote cannot make LoC read a local file through a symlink."""
    source, bare = remote
    secret = tmp_path / "outside.py"
    secret.write_text("private\n", encoding="utf-8")
    try:
        (source / "outside.py").symlink_to(secret)
    except (OSError, NotImplementedError):
        pytest.skip("Creating symlinks requires host permission")
    git("-C", str(source), "add", "outside.py")
    git("-C", str(source), "commit", "-m", "test: tracked symlink")
    git("-C", str(source), "push", "origin", "main")
    repo, _ = resolve_remote("project", bare.as_uri(), tmp_path / "cache")
    if not (repo / "outside.py").is_symlink():
        pytest.skip("Git checkout did not preserve symlinks on this host")
    config = {"aliases": {}, "bot_patterns": [], "exclude_dirs": [], "exclude_files": []}
    assert current_loc("project", repo, config).path.tolist() == ["code.py"]


def test_offline_cache_and_authentication_error(remote, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A failed fetch reports stale data while retaining the last good checkout."""
    from contribution_analytics import repositories

    _, bare = remote
    root = tmp_path / "cache"
    repo, _ = resolve_remote("project", bare.as_uri(), root)
    original = repositories._git

    def offline(*args: str, cwd: Path | None = None) -> str:
        """Fail only network refreshes."""
        if "fetch" in args:
            raise RuntimeError("network unavailable; check connectivity and retry")
        return original(*args, cwd=cwd)

    monkeypatch.setattr(repositories, "_git", offline)
    assert resolve_remote("project", bare.as_uri(), root) == (
        repo,
        "stale cached data: network unavailable; check connectivity and retry",
    )
    assert repositories._failure("Permission denied (publickey)").startswith("authentication failed")


def test_cli_mixed_and_partial_analysis(remote, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    """CLI analysis combines local and URL sources and preserves unselected cached rows."""
    source, bare = remote
    config = tmp_path / "settings.yaml"
    config.write_text(
        f"repositories:\n  local:\n    path: {source}\n  remote:\n    url: {bare.as_uri()}\n", encoding="utf-8"
    )
    monkeypatch.setattr(main, "ROOT", tmp_path)
    args = argparse.Namespace(config=str(config), repo="all")
    main.analyze(args)
    commits, _, loc, _ = load_data(tmp_path / "data" / "processed")
    assert set(commits.repo) == {"local", "remote"}
    assert set(loc.repo) == {"local", "remote"}
    assert (source / "code.py").read_text() == "one\n"
    args.repo = "remote"
    main.analyze(args)
    commits, _, _, _ = load_data(tmp_path / "data" / "processed")
    assert set(commits.repo) == {"local", "remote"}
    main.diagnostics(argparse.Namespace(config=str(config), refresh=False))
    assert "valid local repository" in capsys.readouterr().out
    main.diagnostics(argparse.Namespace(config=str(config), refresh=True))
    assert "remote URL configured; refreshed" in capsys.readouterr().out
    main.export(argparse.Namespace(config=str(config), display_name="Test Analytics"))
    assert (tmp_path / "exports" / "csv" / "commit_history.csv").exists()
    assert (tmp_path / "exports" / "reports" / "test-analytics-executive-summary.html").exists()
    assert load_config(config)["repositories"]["remote"]["url"] == bare.as_uri()
