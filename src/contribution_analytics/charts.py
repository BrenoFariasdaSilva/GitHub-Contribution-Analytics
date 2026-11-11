"""Reusable Plotly charts for the local dashboard."""

from __future__ import annotations

import re
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def configure_chart_colors(theme: str) -> None:
    """Give Plotly Express real colors before Streamlit can insert browser-only placeholders."""
    px.defaults.template = theme
    px.defaults.color_discrete_sequence = px.colors.qualitative.Plotly
    px.defaults.color_continuous_scale = (
        ["#1d4ed8", "#3b82f6", "#60a5fa", "#a5d8ff"]
        if theme == "plotly_dark"
        else ["#bfdbfe", "#60a5fa", "#2563eb", "#1e3a8a"]
    )


def style_chart(figure: go.Figure, title: str, theme: str) -> go.Figure:
    """Apply the same layout to dashboard and exported figures."""
    figure.update_layout(title=title, template=theme, margin={"l": 20, "r": 20, "t": 45, "b": 20}, legend_title_text="")
    return figure


def png_bytes(figure: go.Figure) -> bytes:
    """Render a high-resolution PNG with a bounded height."""
    height = max(1200, min(3200, 80 * len(figure.data) + 1000))
    return figure.to_image(format="png", width=2400, height=height, scale=2)


def figures_zip(figures: list[tuple[str, go.Figure]], slug: str) -> bytes:
    """Package figures using the same renderer as individual downloads."""
    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        for index, (title, figure) in enumerate(figures, start=1):
            filename = f"{slug}-{index:02d}-{re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')}.png"
            archive.writestr(filename, png_bytes(figure))
    return output.getvalue()


def contributor_rank_bar(ranking: pd.DataFrame, color: str) -> go.Figure:
    """Keep every contributor label visible in a descending horizontal ranking."""
    ordered = ranking.iloc[::-1]
    figure = px.bar(ordered, x="commits", y="contributor", orientation="h", color=color, text="commits")
    figure.update_layout(height=max(500, 32 * len(ordered) + 140))
    figure.update_yaxes(tickmode="array", tickvals=ordered.contributor.tolist(), automargin=True)
    return figure
