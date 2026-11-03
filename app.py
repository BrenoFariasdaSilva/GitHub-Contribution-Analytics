from __future__ import annotations

import re
import sys
from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
from contribution_analytics.analytics import (
    activity_by_period,
    commit_intervals,
    commit_timing,
    repository_colors,
    repository_comparison,
)
from contribution_analytics.branding import resolve_branding
from contribution_analytics.config import config_path, load_config
from contribution_analytics.git import load_data
from contribution_analytics.metrics import commit_daily, contribution_streaks, filter_commits, github_status, summary

CONFIG = load_config(config_path(None, ROOT))
TIMEZONE = str(CONFIG["timezone"])
BRANDING = resolve_branding(ROOT, configured_name=str(CONFIG["display_name"]))
st.set_page_config(page_title=BRANDING.title, page_icon="📊", layout="wide")


@st.cache_data
def data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, list[dict[str, object]]]:
    """Load the cached data set for the dashboard."""
    return load_data(ROOT / "data" / "processed")


try:
    commits, file_changes, loc, metadata = data()
except FileNotFoundError:
    st.error("No processed data. Run `python main.py analyze --repo all` first.")
    st.stop()

pages = [
    "Overview",
    "Contributions Calendar",
    "Contributors",
    "Git Commits",
    "Lines of Code",
    "Code Ownership",
    "Pull Requests",
    "Issues",
    "Repository Comparison",
    "Languages",
    "Files and Modules",
    "Collaboration",
    "Historical Trends",
    "Data Explorer",
    "Export Reports",
    "Configuration / Data Sources",
    "Repository Activity",
    "Contributor Insights",
    "Code Evolution",
    "Commit Patterns",
]
available_repos = sorted(commits.repo.unique())
available_people = sorted(commits.contributor.dropna().unique())
url_page = st.query_params.get("page", "Overview")
initial_page = url_page if url_page in pages else "Overview"
url_repos = [value for value in st.query_params.get_all("repo") if value in available_repos]
url_people = [value for value in st.query_params.get_all("contributor") if value in available_people]
minimum, maximum = commits.author_date.min().date(), commits.author_date.max().date()
try:
    initial_dates = (
        pd.Timestamp(st.query_params.get("start", minimum)).date(),
        pd.Timestamp(st.query_params.get("end", maximum)).date(),
    )
    if not minimum <= initial_dates[0] <= initial_dates[1] <= maximum:
        initial_dates = (minimum, maximum)
except (TypeError, ValueError):
    initial_dates = (minimum, maximum)


def persist_navigation() -> None:
    """Make browser reload restore dashboard scope without server-side state."""
    current_dates = st.session_state["date_range_filter"]
    st.query_params["page"] = st.session_state["page_selector"]
    st.query_params["repo"] = st.session_state["repository_filter"]
    st.query_params["contributor"] = st.session_state["contributor_filter"]
    st.query_params["humans"] = "1" if st.session_state["human_filter"] else "0"
    st.query_params["start"] = current_dates[0].isoformat()
    st.query_params["end"] = current_dates[1].isoformat()


with st.sidebar:
    page = st.radio(
        "Section", pages, index=pages.index(initial_page), key="page_selector", on_change=persist_navigation
    )
    selected_repos = st.multiselect(
        "Repositories",
        available_repos,
        default=url_repos or available_repos,
        key="repository_filter",
        on_change=persist_navigation,
    )
    selected_people = st.multiselect(
        "Contributors", available_people, default=url_people, key="contributor_filter", on_change=persist_navigation
    )
    human_only = st.checkbox(
        "Human contributors only",
        value=st.query_params.get("humans", "1") == "1",
        key="human_filter",
        on_change=persist_navigation,
    )
    dates = st.date_input(
        "Date range",
        value=initial_dates,
        min_value=minimum,
        max_value=maximum,
        key="date_range_filter",
        on_change=persist_navigation,
    )
    if len(dates) != 2:
        st.stop()

filtered = filter_commits(
    commits, selected_repos, selected_people if selected_people else None, dates[0], dates[1], human_only
)
filtered_files = file_changes[file_changes.sha.isin(filtered.sha)]
filtered_loc = loc[loc.repo.isin(selected_repos)]
color = repository_colors(available_repos)


def chart(fig, title: str) -> None:
    """Render a chart and provide a safe PNG download when Kaleido is available."""
    fig.update_layout(
        title=title, template=plotly_theme(), margin={"l": 20, "r": 20, "t": 45, "b": 20}, legend_title_text=""
    )
    st.plotly_chart(fig, width="stretch")
    filename = f"{BRANDING.slug}-{re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')}.png"
    try:
        image = png_bytes(fig)
    except ValueError as error:
        st.caption(f"PNG export unavailable: {error}")
    else:
        st.download_button(f"Download PNG — {title}", image, filename, "image/png", key=f"png-{filename}")


def period_strings(values: pd.Series, frequency: str) -> pd.Series:
    """Format periods in project timezone without pandas timezone-loss warnings."""
    return values.dt.tz_convert(TIMEZONE).dt.tz_localize(None).dt.to_period(frequency).astype(str)


def plotly_theme() -> str:
    """Keep rendered charts and downloaded PNGs in active Streamlit theme."""
    return "plotly_dark" if st.context.theme.type == "dark" else "plotly_white"


def png_bytes(fig) -> bytes:
    """Render a high-resolution PNG with a bounded height."""
    height = max(1200, min(3200, 80 * len(fig.data) + 1000))
    return fig.to_image(format="png", width=2400, height=height, scale=2)


def add_figure(figures: list[tuple[str, object]], title: str, figure: object) -> None:
    """Apply common styling and retain a figure for ZIP export."""
    figure.update_layout(
        title=title, template=plotly_theme(), margin={"l": 20, "r": 20, "t": 45, "b": 20}, legend_title_text=""
    )
    figures.append((title, figure))


def all_figures(
    commits_data: pd.DataFrame, files_data: pd.DataFrame, loc_data: pd.DataFrame
) -> list[tuple[str, object]]:
    """Build every local-data visualization for a single ZIP export."""
    figures: list[tuple[str, object]] = []
    daily = commit_daily(commits_data, TIMEZONE)
    weekly = (
        commits_data.assign(week=period_strings(commits_data.author_date, "W"))
        .groupby("week", as_index=False)
        .agg(commits=("sha", "nunique"))
    )
    ranks = (
        commits_data.groupby("contributor", as_index=False)
        .agg(commits=("sha", "nunique"), churn=("additions", "sum"))
        .sort_values("commits", ascending=False)
    )
    add_figure(figures, "Commit activity by day", px.line(daily, x="date", y="commits", markers=True))
    add_figure(figures, "Commit activity by week", px.bar(weekly, x="week", y="commits"))
    add_figure(
        figures,
        "Contributors by commits and additions",
        px.bar(ranks, x="contributor", y="commits", color="churn", color_continuous_scale="Teal"),
    )
    calendar_year = int(commits_data.author_date.dt.year.max())
    calendar_daily = commit_daily(commits_data[commits_data.author_date.dt.year == calendar_year], TIMEZONE)
    grid = calendar_daily.assign(
        day=pd.to_datetime(calendar_daily.date),
        weekday=lambda x: x.day.dt.weekday,
        week=lambda x: x.day.dt.isocalendar().week.astype(int),
    )
    add_figure(
        figures,
        f"{calendar_year} authored commits per day",
        px.density_heatmap(
            grid,
            x="week",
            y="weekday",
            z="commits",
            color_continuous_scale="Greens",
            hover_data=["date", "additions", "deletions"],
        ),
    )
    ranking = commits_data.groupby("contributor", as_index=False).agg(
        commits=("sha", "nunique"),
        additions=("additions", "sum"),
        deletions=("deletions", "sum"),
        files=("files_changed", "sum"),
        active_days=("author_date", lambda x: x.dt.date.nunique()),
    )
    activity = (
        commits_data.assign(month=period_strings(commits_data.author_date, "M"))
        .groupby(["month", "contributor"], as_index=False)
        .agg(commits=("sha", "nunique"))
    )
    languages = files_data.groupby(["contributor", "language"], as_index=False).agg(changes=("sha", "nunique"))
    add_figure(
        figures,
        "Commit ranking",
        px.bar(ranking.sort_values("commits"), x="commits", y="contributor", orientation="h", color="active_days"),
    )
    add_figure(figures, "Contributor share of commits", px.pie(ranking, names="contributor", values="commits"))
    add_figure(
        figures, "Contributor activity over time", px.area(activity, x="month", y="commits", color="contributor")
    )
    add_figure(
        figures,
        "Contributor language specialization",
        px.bar(languages, x="contributor", y="changes", color="language", barmode="stack"),
    )
    by_type = commits_data.groupby("commit_type", as_index=False).agg(commits=("sha", "nunique"))
    by_hour = (
        commits_data.assign(hour=commits_data.author_date.dt.hour, weekday=commits_data.author_date.dt.day_name())
        .groupby(["weekday", "hour"], as_index=False)
        .agg(commits=("sha", "nunique"))
    )
    monthly_repo = (
        commits_data.assign(month=period_strings(commits_data.author_date, "M"))
        .groupby(["month", "repo"], as_index=False)
        .agg(commits=("sha", "nunique"))
    )
    merge_data = (
        commits_data.assign(category=commits_data.is_merge.astype(bool).map({True: "Merge", False: "Ordinary"}))
        .groupby("category", as_index=False)
        .agg(commits=("sha", "nunique"))
    )
    add_figure(figures, "Conventional commit types", px.pie(by_type, names="commit_type", values="commits"))
    add_figure(
        figures,
        "Commit weekday-hour heatmap",
        px.density_heatmap(by_hour, x="hour", y="weekday", z="commits", color_continuous_scale="Blues"),
    )
    add_figure(
        figures,
        "Commit activity by repository",
        px.bar(monthly_repo, x="month", y="commits", color="repo", barmode="group", color_discrete_map=color),
    )
    add_figure(figures, "Commit file-change distribution", px.histogram(commits_data, x="files_changed", nbins=30))
    add_figure(figures, "Merge versus ordinary commits", px.bar(merge_data, x="category", y="commits"))
    by_language = loc_data.groupby(["repo", "language"], as_index=False).physical_loc.sum()
    churn = (
        commits_data[~commits_data.is_merge.astype(bool)]
        .groupby(["contributor", "repo"], as_index=False)
        .agg(additions=("additions", "sum"), deletions=("deletions", "sum"))
    )
    add_figure(
        figures,
        "Current physical LoC by language",
        px.bar(by_language, x="language", y="physical_loc", color="repo", barmode="group", color_discrete_map=color),
    )
    add_figure(
        figures,
        "Historical additions-deletions",
        px.bar(churn, x="contributor", y=["additions", "deletions"], barmode="group", facet_col="repo"),
    )
    add_figure(
        figures,
        "Tracked source-file size",
        px.treemap(loc_data, path=["repo", "directory", "path"], values="physical_loc", color="language"),
    )
    add_figure(
        figures,
        "Largest source directories",
        px.bar(
            loc_data.groupby("directory", as_index=False).physical_loc.sum().nlargest(25, "physical_loc"),
            x="physical_loc",
            y="directory",
            orientation="h",
        ),
    )
    comparison = pd.DataFrame(
        [
            {
                "repo": repo,
                **summary(
                    commits_data[commits_data.repo == repo],
                    files_data[files_data.repo == repo],
                    loc_data[loc_data.repo == repo],
                ),
            }
            for repo in sorted(commits_data.repo.unique())
        ]
    )
    add_figure(
        figures,
        "Repository comparison",
        px.bar(
            comparison.melt(id_vars="repo", value_vars=["commits", "contributors", "loc", "churn"]),
            x="variable",
            y="value",
            color="repo",
            barmode="group",
            color_discrete_map=color,
        ),
    )
    add_figure(
        figures,
        "Repository activity",
        px.line(monthly_repo, x="month", y="commits", color="repo", color_discrete_map=color),
    )
    add_figure(
        figures, "Current language composition", px.sunburst(loc_data, path=["repo", "language"], values="physical_loc")
    )
    add_figure(
        figures,
        "Historical file-change activity by language",
        px.histogram(files_data, x="language", color="contributor", barmode="stack"),
    )
    hotspots = files_data.groupby(["path", "directory"], as_index=False).agg(
        commits=("sha", "nunique"), contributors=("contributor", "nunique")
    )
    module = files_data.groupby("directory", as_index=False).agg(
        changes=("sha", "nunique"), contributors=("contributor", "nunique")
    )
    add_figure(
        figures,
        "Most frequently changed files",
        px.bar(hotspots.nlargest(25, "commits"), x="commits", y="path", color="contributors", orientation="h"),
    )
    add_figure(
        figures,
        "Module activity hotspots",
        px.scatter(module, x="changes", y="contributors", size="changes", hover_name="directory"),
    )
    add_figure(
        figures,
        "Contributor versus directory activity",
        px.imshow(
            pd.crosstab(files_data.contributor, files_data.directory), aspect="auto", color_continuous_scale="Viridis"
        ),
    )
    monthly = (
        commits_data.assign(month=period_strings(commits_data.author_date, "M"))
        .groupby("month", as_index=False)
        .agg(commits=("sha", "nunique"), additions=("additions", "sum"), deletions=("deletions", "sum"))
    )
    monthly["cumulative_commits"] = monthly.commits.cumsum()
    add_figure(figures, "Cumulative commits", px.line(monthly, x="month", y="cumulative_commits"))
    add_figure(figures, "Monthly code churn", px.bar(monthly, x="month", y=["additions", "deletions"], barmode="group"))
    return figures


def build_assets_zip(commits_data: pd.DataFrame, files_data: pd.DataFrame, loc_data: pd.DataFrame) -> bytes:
    """Render the dashboard's local-data charts into a downloadable ZIP archive."""
    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        for index, (title, figure) in enumerate(all_figures(commits_data, files_data, loc_data), start=1):
            filename = f"{BRANDING.slug}-{index:02d}-{re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')}.png"
            archive.writestr(filename, png_bytes(figure))
    return output.getvalue()


asset_scope = (
    tuple(selected_repos),
    tuple(selected_people),
    human_only,
    str(dates[0]),
    str(dates[1]),
    st.context.theme.type,
)
with st.sidebar:
    st.divider()
    if st.button("Prepare all PNG assets (ZIP)", disabled=filtered.empty, width="stretch"):
        with st.spinner("Rendering high-resolution PNG assets…"):
            st.session_state["assets_zip"] = build_assets_zip(filtered, filtered_files, filtered_loc)
            st.session_state["assets_scope"] = asset_scope
    if st.session_state.get("assets_scope") == asset_scope and "assets_zip" in st.session_state:
        st.download_button(
            "Download all PNG assets (ZIP)",
            st.session_state["assets_zip"],
            f"{BRANDING.slug}-assets.zip",
            "application/zip",
            width="stretch",
        )


def unavailable(kind: str) -> None:
    """Show an explicit empty state for unavailable optional data sources."""
    st.info(f"{kind} analytics unavailable. {github_status()['reason']}")


if not selected_repos:
    st.warning("No repositories selected. Choose at least one repository to view analytics.")
    st.stop()


if page == "Overview":
    st.title(BRANDING.title)
    values = summary(filtered, filtered_files, filtered_loc)
    cards = [
        ("Unique commits", values["commits"]),
        ("Contributors", values["contributors"]),
        ("Current source LoC", values["loc"]),
        ("Ordinary-commit churn", values["churn"]),
        ("Files", values["files"]),
        ("Languages", values["languages"]),
        ("First commit", values["first_commit"]),
        ("Last commit", values["last_commit"]),
    ]
    for row in range(0, len(cards), 4):
        columns = st.columns(4)
        for column, (label, value) in zip(columns, cards[row : row + 4]):
            column.metric(label, f"{value:,}" if isinstance(value, int) else value)
    daily = commit_daily(filtered, TIMEZONE)
    chart(px.line(daily, x="date", y="commits", markers=True), "Commit activity by day")
    weekly = (
        filtered.assign(week=period_strings(filtered.author_date, "W"))
        .groupby("week", as_index=False)
        .agg(commits=("sha", "nunique"))
    )
    chart(px.bar(weekly, x="week", y="commits"), "Commit activity by week")
    ranks = (
        filtered.groupby("contributor", as_index=False)
        .agg(commits=("sha", "nunique"), churn=("additions", "sum"))
        .sort_values("commits", ascending=False)
    )
    chart(
        px.bar(ranks, x="contributor", y="commits", color="churn", color_continuous_scale="Teal"),
        "Contributors by commits and additions",
    )
elif page == "Repository Activity":
    st.title("Repository activity")
    frequency = st.segmented_control("Aggregation", {"D": "Daily", "W": "Weekly", "M": "Monthly"}, default="W")
    activity = activity_by_period(filtered, TIMEZONE, frequency or "W")
    st.caption(f"Author timestamps are grouped in {TIMEZONE}. A commit is not a measure of time spent programming.")
    values = summary(filtered, filtered_files, filtered_loc)
    cards = [
        ("Active days", filtered.author_date.dt.tz_convert(TIMEZONE).dt.date.nunique()),
        ("Average active day", f"{values['average_daily_commits']:.2f}"),
        ("Latest commit", values["last_commit"]),
        ("Timezone", TIMEZONE),
    ]
    for column, (label, value) in zip(st.columns(4), cards):
        column.metric(label, value)
    chart(px.line(activity, x="period", y="commits", markers=True), "Commit activity over time")
    chart(
        px.bar(activity, x="period", y=["additions", "deletions"], barmode="group"),
        "Historical additions and deletions",
    )
    timing = commit_timing(filtered, TIMEZONE)
    chart(
        px.density_heatmap(timing, x="hour", y="weekday", z="commits", color_continuous_scale="Blues"),
        "Commit timing by weekday and hour",
    )
elif page == "Contributor Insights":
    st.title("Contributor insights")
    ranking = filtered.groupby("contributor", as_index=False).agg(
        commits=("sha", "nunique"),
        first=("author_date", "min"),
        last=("author_date", "max"),
        repositories=("repo", "nunique"),
    )
    chart(
        px.bar(ranking.sort_values("commits"), x="commits", y="contributor", orientation="h", color="repositories"),
        "Contributor commit distribution",
    )
    chart(px.pie(ranking, names="contributor", values="commits"), "Contributor share of commits")
    monthly = (
        filtered.assign(month=period_strings(filtered.author_date, "M"))
        .groupby(["month", "contributor"], as_index=False)
        .agg(commits=("sha", "nunique"))
    )
    chart(px.area(monthly, x="month", y="commits", color="contributor"), "Contributor activity over time")
    st.dataframe(ranking.sort_values("commits", ascending=False), width="stretch", hide_index=True)
elif page == "Code Evolution":
    st.title("Code evolution and churn")
    st.caption("Historical churn is Git numstat activity, not a historical source-code size estimate.")
    monthly = activity_by_period(filtered, TIMEZONE, "M")
    chart(
        px.bar(monthly, x="period", y=["additions", "deletions", "net_changes"], barmode="group"),
        "Monthly code changes",
    )
    churn_by_repo = (
        filtered[~filtered.is_merge.astype(bool)]
        .groupby("repo", as_index=False)
        .agg(additions=("additions", "sum"), deletions=("deletions", "sum"), churn=("additions", "sum"))
    )
    churn_by_repo["churn"] = churn_by_repo.additions + churn_by_repo.deletions
    chart(
        px.bar(churn_by_repo, x="repo", y="churn", color="repo", color_discrete_map=color),
        "Historical churn by repository",
    )
    hotspots = filtered_files.groupby(["path", "directory"], as_index=False).agg(
        commits=("sha", "nunique"), contributors=("contributor", "nunique")
    )
    chart(
        px.bar(hotspots.nlargest(25, "commits"), x="commits", y="path", color="contributors", orientation="h"),
        "Most frequently changed files",
    )
elif page == "Commit Patterns":
    st.title("Commit patterns")
    conventional = (
        filtered.assign(category=filtered.commit_type.ne("nonconventional").map({True: "Conventional", False: "Other"}))
        .groupby("category", as_index=False)
        .agg(commits=("sha", "nunique"))
    )
    chart(px.pie(conventional, names="category", values="commits"), "Conventional Commit adoption")
    types = filtered.groupby(["repo", "commit_type"], as_index=False).agg(commits=("sha", "nunique"))
    chart(
        px.bar(types, x="commit_type", y="commits", color="repo", barmode="group", color_discrete_map=color),
        "Commit type distribution by repository",
    )
    scopes = (
        filtered[filtered.scope.astype(bool)]
        .groupby("scope", as_index=False)
        .agg(commits=("sha", "nunique"))
        .nlargest(20, "commits")
    )
    if not scopes.empty:
        chart(px.bar(scopes, x="commits", y="scope", orientation="h"), "Most common Conventional Commit scopes")
    intervals = commit_intervals(filtered)
    if not intervals.empty:
        st.metric("Median interval between authored commits", f"{intervals.median():.1f} hours")
        chart(
            px.histogram(intervals, nbins=30, labels={"value": "Hours between commits"}), "Commit interval distribution"
        )
elif page == "Contributions Calendar":
    st.title("Project-derived activity calendar")
    st.caption("Not GitHub official contribution counting. Counts selected local Git authored commits.")
    year = st.selectbox("Year", sorted(filtered.author_date.dt.year.unique(), reverse=True))
    daily = commit_daily(filtered[filtered.author_date.dt.year == year], TIMEZONE)
    grid = daily.assign(
        day=pd.to_datetime(daily.date),
        weekday=lambda x: x.day.dt.weekday,
        week=lambda x: x.day.dt.isocalendar().week.astype(int),
    )
    chart(
        px.density_heatmap(
            grid,
            x="week",
            y="weekday",
            z="commits",
            color_continuous_scale="Greens",
            hover_data=["date", "additions", "deletions"],
        ),
        f"{year} authored commits per day",
    )
    stats = contribution_streaks(daily, year)
    st.json(stats)
elif page == "Contributors":
    st.title("Contributor comparison")
    ranking = filtered.groupby("contributor", as_index=False).agg(
        commits=("sha", "nunique"),
        additions=("additions", "sum"),
        deletions=("deletions", "sum"),
        files=("files_changed", "sum"),
        active_days=("author_date", lambda x: x.dt.date.nunique()),
    )
    chart(
        px.bar(ranking.sort_values("commits"), x="commits", y="contributor", orientation="h", color="active_days"),
        "Commit ranking",
    )
    chart(px.pie(ranking, names="contributor", values="commits"), "Contributor share of commits")
    activity = (
        filtered.assign(month=period_strings(filtered.author_date, "M"))
        .groupby(["month", "contributor"], as_index=False)
        .agg(commits=("sha", "nunique"))
    )
    chart(px.area(activity, x="month", y="commits", color="contributor"), "Contributor activity over time")
    languages = filtered_files.groupby(["contributor", "language"], as_index=False).agg(changes=("sha", "nunique"))
    chart(
        px.bar(languages, x="contributor", y="changes", color="language", barmode="stack"),
        "Contributor language specialization",
    )
    st.dataframe(ranking.sort_values("commits", ascending=False), width="stretch", hide_index=True)
elif page == "Git Commits":
    st.title("Git commits")
    by_type = filtered.groupby("commit_type", as_index=False).agg(commits=("sha", "nunique"))
    by_hour = (
        filtered.assign(hour=filtered.author_date.dt.hour, weekday=filtered.author_date.dt.day_name())
        .groupby(["weekday", "hour"], as_index=False)
        .agg(commits=("sha", "nunique"))
    )
    chart(px.pie(by_type, names="commit_type", values="commits"), "Conventional commit types")
    chart(
        px.density_heatmap(by_hour, x="hour", y="weekday", z="commits", color_continuous_scale="Blues"),
        "Commit weekday/hour heatmap",
    )
    monthly = (
        filtered.assign(month=period_strings(filtered.author_date, "M"))
        .groupby(["month", "repo"], as_index=False)
        .agg(commits=("sha", "nunique"))
    )
    chart(
        px.bar(monthly, x="month", y="commits", color="repo", barmode="group", color_discrete_map=color),
        "Commit activity by repository",
    )
    chart(px.histogram(filtered, x="files_changed", nbins=30), "Commit file-change distribution")
    merge_data = (
        filtered.assign(category=filtered.is_merge.astype(bool).map({True: "Merge", False: "Ordinary"}))
        .groupby("category", as_index=False)
        .agg(commits=("sha", "nunique"))
    )
    chart(px.bar(merge_data, x="category", y="commits"), "Merge versus ordinary commits")
elif page == "Lines of Code":
    st.title("Current codebase size vs historical churn")
    st.caption(
        "Current LoC derives from tracked working-tree files. Churn derives from non-merge Git numstat; "
        "they are different measures."
    )
    by_language = filtered_loc.groupby(["repo", "language"], as_index=False).physical_loc.sum()
    chart(
        px.bar(by_language, x="language", y="physical_loc", color="repo", barmode="group", color_discrete_map=color),
        "Current physical LoC by language",
    )
    churn = (
        filtered[~filtered.is_merge.astype(bool)]
        .groupby(["contributor", "repo"], as_index=False)
        .agg(additions=("additions", "sum"), deletions=("deletions", "sum"))
    )
    chart(
        px.bar(churn, x="contributor", y=["additions", "deletions"], barmode="group", facet_col="repo"),
        "Historical additions/deletions",
    )
    chart(
        px.treemap(filtered_loc, path=["repo", "directory", "path"], values="physical_loc", color="language"),
        "Tracked source-file size",
    )
    chart(
        px.bar(
            filtered_loc.groupby("directory", as_index=False).physical_loc.sum().nlargest(25, "physical_loc"),
            x="physical_loc",
            y="directory",
            orientation="h",
        ),
        "Largest source directories",
    )
elif page == "Code Ownership":
    st.title("Code ownership")
    st.warning(
        "Git blame ownership is disabled by default because it is expensive. "
        "Surviving-line attribution is not architectural ownership."
    )
    st.write("Enable `ownership_enabled` in configuration before adding cached blame analysis.")
elif page in {"Pull Requests", "Issues"}:
    st.title(page)
    unavailable(page)
elif page == "Repository Comparison":
    st.title("Repository comparison")
    comparison = repository_comparison(filtered, filtered_loc, TIMEZONE)
    chart(
        px.bar(
            comparison.melt(id_vars="repo", value_vars=["commits", "contributors", "loc", "churn"]),
            x="variable",
            y="value",
            color="repo",
            barmode="group",
            color_discrete_map=color,
        ),
        "Repository comparison",
    )
    chart(
        px.line(
            filtered.assign(month=period_strings(filtered.author_date, "M"))
            .groupby(["month", "repo"], as_index=False)
            .agg(commits=("sha", "nunique")),
            x="month",
            y="commits",
            color="repo",
            color_discrete_map=color,
        ),
        "Repository activity",
    )
    st.dataframe(comparison, width="stretch", hide_index=True)
elif page == "Languages":
    st.title("Languages")
    chart(px.sunburst(filtered_loc, path=["repo", "language"], values="physical_loc"), "Current language composition")
    chart(
        px.histogram(filtered_files, x="language", color="contributor", barmode="stack"),
        "Historical file-change activity by language",
    )
elif page == "Files and Modules":
    st.title("Files and modules")
    hotspots = filtered_files.groupby(["path", "directory"], as_index=False).agg(
        commits=("sha", "nunique"), contributors=("contributor", "nunique")
    )
    chart(
        px.bar(hotspots.nlargest(25, "commits"), x="commits", y="path", color="contributors", orientation="h"),
        "Most frequently changed files",
    )
    module = filtered_files.groupby("directory", as_index=False).agg(
        changes=("sha", "nunique"), contributors=("contributor", "nunique")
    )
    chart(
        px.scatter(module, x="changes", y="contributors", size="changes", hover_name="directory"),
        "Module activity hotspots",
    )
elif page == "Collaboration":
    st.title("Collaboration")
    matrix = pd.crosstab(filtered_files.contributor, filtered_files.directory)
    chart(px.imshow(matrix, aspect="auto", color_continuous_scale="Viridis"), "Contributor versus directory activity")
    st.info("PR review network requires authenticated GitHub data.")
elif page == "Historical Trends":
    st.title("Historical trends")
    monthly = (
        filtered.assign(month=period_strings(filtered.author_date, "M"))
        .groupby("month", as_index=False)
        .agg(commits=("sha", "nunique"), additions=("additions", "sum"), deletions=("deletions", "sum"))
    )
    monthly["cumulative_commits"] = monthly.commits.cumsum()
    chart(px.line(monthly, x="month", y="cumulative_commits"), "Cumulative commits")
    chart(px.bar(monthly, x="month", y=["additions", "deletions"], barmode="group"), "Monthly code churn")
elif page == "Data Explorer":
    st.title("Data explorer")
    st.dataframe(filtered.sort_values("author_date", ascending=False), width="stretch", hide_index=True)
    st.download_button(
        "Download filtered commits CSV", filtered.to_csv(index=False), "filtered_commits.csv", "text/csv"
    )
elif page == "Export Reports":
    st.title("Export reports")
    st.write("Use `python main.py export --all` to regenerate CSV, JSON, and executive HTML report.")
    st.dataframe(
        pd.DataFrame({"path": [str(p.relative_to(ROOT)) for p in (ROOT / "exports").rglob("*") if p.is_file()]}),
        hide_index=True,
    )
else:
    st.title("Configuration / data sources")
    st.json(
        {
            "repositories": metadata,
            "github": github_status(),
            "scope": "Local Git refs (--all), unique SHAs, ordinary-commit numstat churn; "
            "current LoC from Git-tracked files.",
        }
    )
