from __future__ import annotations

import subprocess
from pathlib import Path

import pandas as pd

from contribution_analytics.git import CONVENTIONAL, canonical, classify_language, parse_numstat
from contribution_analytics.metrics import contribution_streaks


def test_aliases_only_merge_explicit_values() -> None:
    """Canonical identities change only for exact configured aliases."""
    assert canonical("Ana", "ANA@EXAMPLE.COM", {"ana@example.com": "Ana Silva"}) == "Ana Silva"
    assert canonical("Ana", "ana@example.com", {}) == "Ana"


def test_conventional_commit_parsing() -> None:
    """Conventional commit categories and scopes are parsed."""
    match = CONVENTIONAL.match("feat(api)!: incompatible endpoint")
    assert match and match.group("type") == "feat" and match.group("scope") == "api"
    assert CONVENTIONAL.match("plain message") is None


def test_numstat_binary_and_normal() -> None:
    """Binary numstat rows have no invented line counts."""
    added, deleted, binary, paths = parse_numstat(["4\t2\tsrc/a.ts", "-\t-\timage.png"])
    assert (added, deleted, binary, paths) == (4, 2, 1, ["src/a.ts", "image.png"])


def test_language_detection() -> None:
    """Known extensions map to language labels."""
    assert classify_language("src/a.tsx") == "TypeScript"
    assert classify_language("asset.unknown") == "Other"


def test_daily_streaks() -> None:
    """Separated activity periods do not merge into one streak."""
    frame = pd.DataFrame(
        {
            "date": ["2025-01-01", "2025-01-02", "2025-01-04"],
            "commits": [1, 3, 1],
            "additions": [1, 1, 1],
            "deletions": [0, 0, 0],
        }
    )
    result = contribution_streaks(frame)
    assert result["active_days"] == 3 and result["longest_streak"] == 2


def test_temp_git_repository_parses_history(tmp_path: Path) -> None:
    """A synthetic Git repository can create a valid commit history."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", str(repo)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Tester"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "tester@example.com"], check=True)
    (repo / "x.txt").write_text("x\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-m", "feat: init"], check=True, capture_output=True)
    assert (
        subprocess.run(
            ["git", "-C", str(repo), "rev-list", "--count", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip()
        == "1"
    )
