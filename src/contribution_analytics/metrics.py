from __future__ import annotations

from datetime import date
from html import escape
from itertools import pairwise
from pathlib import Path
from typing import Any

import pandas as pd

from contribution_analytics.branding import Branding
from contribution_analytics.privacy import public_metadata


def filter_commits(
    commits: pd.DataFrame,
    repos: list[str] | None = None,
    contributors: list[str] | None = None,
    start: date | None = None,
    end: date | None = None,
    humans_only: bool = False,
    timezone: str = "UTC",
) -> pd.DataFrame:
    """Filter commits by repository, contributor, local authored date, and bot status."""
    data = commits.copy()
    if repos is not None:
        data = data[data.repo.isin(repos)]
    if contributors is not None:
        data = data[data.contributor.isin(contributors)]
    if humans_only:
        data = data[~data.is_bot.astype(bool)]
    if start or end:
        local_dates = pd.to_datetime(data.author_date, utc=True).dt.tz_convert(timezone).dt.date
        if start:
            data = data[local_dates >= start]
            local_dates = local_dates.loc[data.index]
        if end:
            data = data[local_dates <= end]
    return data


def commit_daily(commits: pd.DataFrame, timezone: str = "UTC") -> pd.DataFrame:
    """Aggregate unique commits and ordinary churn by configured local authored day."""
    if commits.empty:
        return pd.DataFrame(columns=["date", "commits", "additions", "deletions", "churn"])
    data = commits.assign(date=pd.to_datetime(commits.author_date, utc=True).dt.tz_convert(timezone).dt.date)
    return (
        data.groupby("date", as_index=False)
        .agg(commits=("sha", "nunique"), additions=("additions", "sum"), deletions=("deletions", "sum"))
        .assign(churn=lambda x: x.additions + x.deletions)
    )


def contribution_streaks(daily: pd.DataFrame, year: int | None = None) -> dict[str, Any]:
    """Calculate active-day and contiguous contribution streak statistics."""
    if daily.empty:
        return {
            "active_days": 0,
            "longest_streak": 0,
            "current_streak": 0,
            "most_active_day": None,
            "average_active_day": 0,
        }
    dates = pd.to_datetime(daily.date)
    if year:
        daily = daily[dates.dt.year == year].copy()
        dates = pd.to_datetime(daily.date)
    if daily.empty:
        return {
            "active_days": 0,
            "longest_streak": 0,
            "current_streak": 0,
            "most_active_day": None,
            "average_active_day": 0,
        }
    ordered = sorted(dates.dt.date.unique())
    longest = current = 1
    for previous, today in pairwise(ordered):
        current = current + 1 if (today - previous).days == 1 else 1
        longest = max(longest, current)
    today = pd.Timestamp.now(tz="UTC").date()
    running = 0
    cursor = today
    active = set(ordered)
    while cursor in active:
        running += 1
        cursor -= pd.Timedelta(days=1)
    peak = daily.loc[daily.commits.idxmax()]
    return {
        "active_days": len(ordered),
        "longest_streak": longest,
        "current_streak": running,
        "most_active_day": str(peak.date),
        "average_active_day": float(daily.commits.mean()),
    }


def summary(commits: pd.DataFrame, files: pd.DataFrame, loc: pd.DataFrame) -> dict[str, Any]:
    """Return headline metrics while excluding merge churn from totals."""
    ordinary = commits[~commits.is_merge.astype(bool)] if not commits.empty else commits
    daily = commit_daily(commits)
    return {
        "commits": int(commits.sha.nunique()) if not commits.empty else 0,
        "contributors": int(commits.contributor.nunique()) if not commits.empty else 0,
        "active_contributors": int(
            commits[commits.author_date >= commits.author_date.max() - pd.Timedelta(days=90)].contributor.nunique()
        )
        if not commits.empty
        else 0,
        "merge_commits": int(commits.is_merge.astype(bool).sum()) if not commits.empty else 0,
        "additions": int(ordinary.additions.sum()) if not ordinary.empty else 0,
        "deletions": int(ordinary.deletions.sum()) if not ordinary.empty else 0,
        "churn": int(ordinary.additions.sum() + ordinary.deletions.sum()) if not ordinary.empty else 0,
        "files": int(loc.path.nunique()) if not loc.empty else 0,
        "loc": int(loc.physical_loc.sum()) if not loc.empty else 0,
        "languages": int(loc.language.nunique()) if not loc.empty else 0,
        "first_commit": str(commits.author_date.min().date()) if not commits.empty else "Unavailable",
        "last_commit": str(commits.author_date.max().date()) if not commits.empty else "Unavailable",
        "average_daily_commits": float(daily.commits.mean()) if not daily.empty else 0.0,
    }


def github_status() -> dict[str, str]:
    """Describe unavailable optional GitHub-only metrics without fabricating data."""
    return {
        "state": "unavailable",
        "reason": "GitHub CLI authentication unavailable; run `gh auth login -h github.com` then refresh GitHub data.",
    }


def export_all(
    root: Path,
    commits: pd.DataFrame,
    files: pd.DataFrame,
    loc: pd.DataFrame,
    metadata: list[dict[str, Any]],
    branding: Branding,
) -> list[Path]:
    """Write CSV, JSON, and HTML exports with escaped text and redacted paths."""
    csv_dir, json_dir, reports = (root / "exports" / name for name in ("csv", "json", "reports"))
    for directory in (csv_dir, json_dir, reports):
        directory.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for name, frame in {"commit_history": commits, "file_changes": files, "current_loc": loc}.items():
        csv_path = csv_dir / f"{name}.csv"
        json_path = json_dir / f"{name}.json"
        frame.to_csv(csv_path, index=False)
        frame.to_json(json_path, orient="records", date_format="iso", indent=2)
        written.extend([csv_path, json_path])
    overall = summary(commits, files, loc)
    report = reports / f"{branding.slug}-executive-summary.html"
    html = (
        f"<html><body><h1>{escape(branding.title)}</h1><h2>Local Git analysis</h2>"
        f"<pre>{escape(pd.Series(overall).to_string())}</pre>"
        "<p>GitHub-only metrics: unavailable unless authenticated API data is refreshed.</p></body></html>"
    )
    report.write_text(html, encoding="utf-8")
    (json_dir / "analysis_metadata.json").write_text(
        pd.Series({"repositories": public_metadata(metadata), "summary": overall, "github": github_status()}).to_json(
            indent=2
        ),
        encoding="utf-8",
    )
    return written + [report]
