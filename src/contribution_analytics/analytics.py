"""Timezone-aware, reusable analytics aggregations."""

from __future__ import annotations

import hashlib
from zoneinfo import ZoneInfo

import pandas as pd

PALETTE = ["#0072B2", "#E69F00", "#009E73", "#CC79A7", "#56B4E9", "#D55E00", "#6A5ACD", "#2F4F4F"]


def repository_colors(names: list[str]) -> dict[str, str]:
    """Assign each repository a stable color derived from its name."""
    return {name: PALETTE[int(hashlib.sha256(name.encode()).hexdigest(), 16) % len(PALETTE)] for name in names}


def localized_timestamps(commits: pd.DataFrame, timezone: str, column: str = "author_date") -> pd.Series:
    """Convert a timestamp column to the configured timezone without losing awareness."""
    if commits.empty or column not in commits:
        return pd.Series(dtype="datetime64[ns, UTC]")
    return pd.to_datetime(commits[column], utc=True, errors="coerce").dt.tz_convert(ZoneInfo(timezone))


def active_day_count(timestamps: pd.Series, timezone: str) -> int:
    """Count distinct authored days in the configured timezone."""
    return int(pd.to_datetime(timestamps, utc=True).dt.tz_convert(timezone).dt.date.nunique())


def activity_by_period(commits: pd.DataFrame, timezone: str, frequency: str = "D") -> pd.DataFrame:
    """Aggregate commits, churn, and active contributors by configured local period."""
    columns = ["period", "commits", "additions", "deletions", "churn", "net_changes", "contributors"]
    if commits.empty:
        return pd.DataFrame(columns=columns)
    data = commits.copy()
    data["period"] = localized_timestamps(data, timezone).dt.tz_localize(None).dt.to_period(frequency).astype(str)
    return (
        data.groupby("period", as_index=False)
        .agg(
            commits=("sha", "nunique"),
            additions=("additions", "sum"),
            deletions=("deletions", "sum"),
            contributors=("contributor", "nunique"),
        )
        .assign(
            churn=lambda frame: frame.additions + frame.deletions,
            net_changes=lambda frame: frame.additions - frame.deletions,
        )
    )


def repository_comparison(commits: pd.DataFrame, loc: pd.DataFrame, timezone: str) -> pd.DataFrame:
    """Compare selected repositories using consistently filtered local Git data."""
    rows: list[dict[str, object]] = []
    for name in sorted(set(commits.get("repo", pd.Series(dtype=str))) | set(loc.get("repo", pd.Series(dtype=str)))):
        data = commits[commits.repo == name]
        ordinary = data[~data.is_merge.astype(bool)] if not data.empty else data
        days = localized_timestamps(data, timezone).dt.date.nunique() if not data.empty else 0
        rows.append(
            {
                "repo": name,
                "commits": int(data.sha.nunique()) if not data.empty else 0,
                "contributors": int(data.contributor.nunique()) if not data.empty else 0,
                "active_days": int(days),
                "loc": int(loc[loc.repo == name].physical_loc.sum()) if not loc.empty else 0,
                "files": int(loc[loc.repo == name].path.nunique()) if not loc.empty else 0,
                "additions": int(ordinary.additions.sum()) if not ordinary.empty else 0,
                "deletions": int(ordinary.deletions.sum()) if not ordinary.empty else 0,
                "churn": int(ordinary.additions.sum() + ordinary.deletions.sum()) if not ordinary.empty else 0,
                "conventional_percent": round(float((data.commit_type != "nonconventional").mean() * 100), 1)
                if not data.empty
                else None,
                "latest_commit": str(localized_timestamps(data, timezone).max().date()) if not data.empty else None,
            }
        )
    return pd.DataFrame(rows)


def commit_timing(commits: pd.DataFrame, timezone: str) -> pd.DataFrame:
    """Count authored commits by local weekday and hour."""
    if commits.empty:
        return pd.DataFrame(columns=["weekday", "hour", "commits"])
    stamps = localized_timestamps(commits, timezone)
    return (
        pd.DataFrame({"weekday": stamps.dt.day_name(), "hour": stamps.dt.hour, "sha": commits.sha})
        .groupby(["weekday", "hour"], as_index=False)
        .agg(commits=("sha", "nunique"))
    )


def commit_intervals(commits: pd.DataFrame) -> pd.Series:
    """Return elapsed hours between consecutive authored commits."""
    stamps = pd.to_datetime(commits.get("author_date"), utc=True, errors="coerce").dropna().sort_values()
    return stamps.diff().dropna().dt.total_seconds().div(3600)


def contributor_ranking(commits: pd.DataFrame) -> pd.DataFrame:
    """Rank canonical contributors by unique commits with deterministic tie-breaking."""
    if commits.empty:
        return pd.DataFrame(columns=["contributor", "commits", "share_percent"])
    ranking = commits.groupby("contributor", dropna=False, as_index=False).agg(commits=("sha", "nunique"))
    ranking["contributor"] = ranking.contributor.fillna("Unknown")
    ranking = ranking.sort_values(["commits", "contributor"], ascending=[False, True], kind="stable").reset_index(
        drop=True
    )
    ranking["share_percent"] = ranking.commits.div(ranking.commits.sum()).mul(100)
    return ranking
