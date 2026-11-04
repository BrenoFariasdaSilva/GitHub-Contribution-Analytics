"""Tests for generic colors and timezone-aware analytics."""

from datetime import date

import pandas as pd

from contribution_analytics.analytics import (
    active_day_count,
    activity_by_period,
    commit_timing,
    contributor_ranking,
    localized_timestamps,
    repository_colors,
    repository_comparison,
)
from contribution_analytics.metrics import filter_commits, initial_repositories, summary


def test_repository_colors_are_stable_when_filtering() -> None:
    """A repository keeps its deterministic color in a smaller selection."""
    all_colors = repository_colors(["api", "web", "mobile"])
    assert all_colors["api"] == repository_colors(["api"])["api"]


def test_empty_repository_filter_selects_no_commits() -> None:
    """An explicit empty repository list differs from no repository filter."""
    commits = pd.DataFrame(
        {
            "repo": ["api"],
            "contributor": ["A"],
            "is_bot": [False],
            "author_date": pd.to_datetime(["2026-01-01"], utc=True),
        }
    )
    assert filter_commits(commits, []).empty
    assert len(filter_commits(commits, None)) == 1


def test_explicit_empty_repository_selection_survives_refresh() -> None:
    """An empty selection marker takes precedence over the default repositories."""
    assert initial_repositories(["api", "web"], [], True) == []
    assert initial_repositories(["api", "web"], [], False) == ["api", "web"]
    assert initial_repositories(["api", "web"], ["api"], False) == ["api"]


def test_date_filter_uses_configured_timezone() -> None:
    """A commit near UTC midnight belongs to its configured local date."""
    commits = pd.DataFrame(
        {
            "repo": ["api"],
            "contributor": ["A"],
            "is_bot": [False],
            "author_date": pd.to_datetime(["2026-01-01T01:00:00Z"]),
        }
    )
    assert (
        len(filter_commits(commits, start=date(2025, 12, 31), end=date(2025, 12, 31), timezone="America/Sao_Paulo"))
        == 1
    )
    assert filter_commits(commits, start=date(2026, 1, 1), end=date(2026, 1, 1), timezone="America/Sao_Paulo").empty


def test_activity_uses_configured_timezone_at_midnight() -> None:
    """A UTC-midnight-adjacent commit groups into the configured local day."""
    commits = pd.DataFrame(
        {
            "sha": ["a"],
            "contributor": ["A"],
            "author_date": pd.to_datetime(["2026-01-01T01:00:00Z"]),
            "additions": [2],
            "deletions": [1],
        }
    )
    assert activity_by_period(commits, "America/Sao_Paulo").period.iloc[0] == "2025-12-31"
    assert activity_by_period(commits, "UTC").period.iloc[0] == "2026-01-01"


def test_calendar_year_uses_local_authored_date() -> None:
    """A UTC January commit appears in the previous local calendar year."""
    commits = pd.DataFrame({"author_date": pd.to_datetime(["2026-01-01T01:00:00Z"])})
    assert localized_timestamps(commits, "America/Sao_Paulo").dt.year.tolist() == [2025]


def test_commit_heatmap_uses_local_weekday_and_hour() -> None:
    """The timing heatmap places UTC-midnight commits in the local slot."""
    commits = pd.DataFrame({"sha": ["a"], "author_date": pd.to_datetime(["2026-01-01T01:00:00Z"])})
    timing = commit_timing(commits, "America/Sao_Paulo")
    assert timing.loc[0, ["weekday", "hour", "commits"]].tolist() == ["Wednesday", 22, 1]


def test_contributor_active_days_use_local_dates() -> None:
    """Two UTC dates can be one contributor day in the configured timezone."""
    timestamps = pd.to_datetime(["2026-01-01T01:00:00Z", "2025-12-31T23:00:00Z"])
    assert active_day_count(pd.Series(timestamps), "America/Sao_Paulo") == 1
    assert active_day_count(pd.Series(timestamps), "UTC") == 2


def test_summary_uses_local_first_last_and_average_day() -> None:
    """Headline dates and daily average agree with local chart aggregation."""
    commits = pd.DataFrame(
        {
            "sha": ["a", "b"],
            "author_date": pd.to_datetime(["2026-01-01T01:00:00Z", "2026-01-01T23:00:00Z"]),
            "contributor": ["A", "A"],
            "is_merge": [False, False],
            "additions": [1, 1],
            "deletions": [0, 0],
        }
    )
    loc = pd.DataFrame(columns=["path", "physical_loc", "language"])
    result = summary(commits, pd.DataFrame(), loc, "America/Sao_Paulo")
    assert (result["first_commit"], result["last_commit"], result["average_daily_commits"]) == (
        "2025-12-31",
        "2026-01-01",
        1.0,
    )


def test_repository_comparison_handles_arbitrary_names() -> None:
    """Comparison metrics do not depend on fixed repository labels."""
    commits = pd.DataFrame(
        {
            "repo": ["mobile-app"],
            "sha": ["a"],
            "contributor": ["A"],
            "is_merge": [False],
            "commit_type": ["feat"],
            "author_date": pd.to_datetime(["2026-01-01"], utc=True),
            "additions": [3],
            "deletions": [1],
        }
    )
    loc = pd.DataFrame({"repo": ["mobile-app"], "path": ["a.py"], "physical_loc": [10]})
    result = repository_comparison(commits, loc, "UTC")
    assert result.loc[0, "repo"] == "mobile-app" and result.loc[0, "conventional_percent"] == 100.0


def test_contributor_ranking_is_deterministic() -> None:
    """Ranking uses commit count then contributor name across all comparison charts."""
    commits = pd.DataFrame({"sha": ["1", "2", "3", "4"], "contributor": ["Zoe", "Ana", "Zoe", "Beto"]})
    ranking = contributor_ranking(commits)
    assert ranking.contributor.tolist() == ["Zoe", "Ana", "Beto"]
    assert ranking.commits.tolist() == [2, 1, 1]
    assert round(ranking.share_percent.sum(), 5) == 100
