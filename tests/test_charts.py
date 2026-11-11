"""Regression tests for contributor chart readability."""

from io import BytesIO
from zipfile import ZipFile

import pandas as pd
import plotly.express as px
import pytest
import streamlit  # noqa: F401 - activate Streamlit's placeholder-color template
from PIL import Image

from contribution_analytics.charts import (
    configure_chart_colors,
    contributor_rank_bar,
    figures_zip,
    png_bytes,
    style_chart,
)


@pytest.fixture
def chart_theme():
    """Restore global Plotly Express defaults after each theme test."""
    original = (px.defaults.template, px.defaults.color_discrete_sequence, px.defaults.color_continuous_scale)
    yield configure_chart_colors
    px.defaults.template, px.defaults.color_discrete_sequence, px.defaults.color_continuous_scale = original


@pytest.fixture
def contributors() -> pd.DataFrame:
    """Provide a ranking with distinct commits and activity values."""
    return pd.DataFrame({"contributor": ["Ada", "Grace", "Linus"], "commits": [12, 8, 4], "active_days": [9, 6, 2]})


@pytest.fixture
def activity() -> pd.DataFrame:
    """Provide three contributor series across two months."""
    return pd.DataFrame(
        {
            "month": ["Jan", "Jan", "Jan", "Feb", "Feb", "Feb"],
            "contributor": ["Ada", "Grace", "Linus"] * 2,
            "commits": [3, 2, 1, 5, 4, 2],
        }
    )


@pytest.mark.parametrize("theme", ["plotly_dark", "plotly_white"])
def test_reported_charts_have_real_distinct_colors(chart_theme, contributors, activity, theme) -> None:
    """Ranking, area, and pie figures contain visible colors in both themes."""
    chart_theme(theme)
    ranking = style_chart(contributor_rank_bar(contributors, "active_days"), "Commit ranking", theme)
    area = style_chart(px.area(activity, x="month", y="commits", color="contributor"), "Activity", theme)
    pie = style_chart(px.pie(contributors, names="contributor", values="commits"), "Share", theme)

    scale = [color for _, color in ranking.layout.coloraxis.colorscale]
    assert len(set(scale)) == len(scale)
    assert all(not color.startswith("#0000") for color in scale)
    assert list(ranking.data[0].marker.color) == [2, 6, 9]
    assert len({trace.line.color for trace in area.data}) == 3
    assert all(not trace.line.color.startswith("#0000") for trace in area.data)
    assert [color.lower() for color in pie.layout.template.layout.colorway[:3]] == [
        color.lower() for color in px.colors.qualitative.Plotly[:3]
    ]
    assert list(pie.data[0].labels) == contributors.contributor.tolist()
    background = "rgb(17,17,17)" if theme == "plotly_dark" else "white"
    assert all(fig.layout.template.layout.paper_bgcolor == background for fig in (ranking, area, pie))


def test_explicit_colors_survive_chart_styling(chart_theme, contributors) -> None:
    """Repository-like mappings and explicit heatmap scales take precedence."""
    chart_theme("plotly_dark")
    figure = px.bar(
        contributors, x="contributor", y="commits", color="contributor", color_discrete_map={"Ada": "#f97316"}
    )
    style_chart(figure, "Explicit", "plotly_dark")
    assert next(trace.marker.color for trace in figure.data if trace.name == "Ada") == "#f97316"
    heatmap = px.density_heatmap(contributors, x="active_days", y="commits", color_continuous_scale="Greens")
    style_chart(heatmap, "Heatmap", "plotly_dark")
    assert heatmap.layout.coloraxis.colorscale[0][1] == "rgb(247,252,245)"


def test_other_plotly_express_charts_avoid_placeholders(chart_theme, contributors, activity) -> None:
    """Bar, line, histogram, and scatter traces avoid browser-only colors."""
    chart_theme("plotly_dark")
    figures = [
        px.bar(contributors, x="contributor", y="commits", color="contributor"),
        px.line(activity, x="month", y="commits", color="contributor"),
        px.histogram(activity, x="commits", color="contributor"),
        px.scatter(activity, x="month", y="commits", color="contributor"),
    ]
    for figure in figures:
        colors = [trace.marker.color or trace.line.color for trace in figure.data]
        assert len(set(colors)) == 3
        assert all(not color.startswith("#0000") for color in colors)


@pytest.mark.parametrize("theme", ["plotly_dark", "plotly_white"])
def test_png_and_zip_preserve_colors(chart_theme, contributors, activity, theme) -> None:
    """Kaleido renders colorful high-resolution PNGs inside both export paths."""
    chart_theme(theme)
    figures = [
        ("Commit ranking", style_chart(contributor_rank_bar(contributors, "active_days"), "Commit ranking", theme)),
        ("Activity", style_chart(px.area(activity, x="month", y="commits", color="contributor"), "Activity", theme)),
        ("Share", style_chart(px.pie(contributors, names="contributor", values="commits"), "Share", theme)),
    ]
    single = png_bytes(figures[0][1])
    assert single.startswith(b"\x89PNG\r\n\x1a\n")
    with Image.open(BytesIO(single)) as image:
        assert image.size[0] == 4800
        image.verify()

    with ZipFile(BytesIO(figures_zip(figures, "sample"))) as archive:
        assert len(archive.namelist()) == 3
        for name in archive.namelist():
            with Image.open(BytesIO(archive.read(name))) as image:
                image.thumbnail((200, 200))
                rgb = image.convert("RGB")
                pixels = (rgb.getpixel((x, y)) for y in range(0, rgb.height, 2) for x in range(0, rgb.width, 2))
                colors = {tuple(value // 32 for value in pixel) for pixel in pixels if max(pixel) - min(pixel) > 45}
                assert len(colors) >= 3, name


def test_ranking_bar_displays_every_label_with_room_for_long_lists() -> None:
    """The second-ranked contributor remains a visible y-axis tick among 33 people."""
    names = ["Leader", "Second"] + [f"Contributor {index:02d}" for index in range(31)]
    ranking = pd.DataFrame(
        {"contributor": names, "commits": list(range(33, 0, -1)), "active_days": list(range(33, 0, -1))}
    )
    figure = contributor_rank_bar(ranking, "active_days")
    assert len(figure.data[0].y) == 33
    assert figure.layout.yaxis.tickmode == "array"
    assert list(figure.layout.yaxis.tickvals) == names[::-1]
    assert figure.layout.height >= 32 * len(names) + 140
