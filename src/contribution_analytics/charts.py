"""Reusable Plotly charts for the local dashboard."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def contributor_rank_bar(ranking: pd.DataFrame, color: str) -> go.Figure:
    """Keep every contributor label visible in a descending horizontal ranking."""
    ordered = ranking.iloc[::-1]
    figure = px.bar(ordered, x="commits", y="contributor", orientation="h", color=color, text="commits")
    figure.update_layout(height=max(500, 32 * len(ordered) + 140))
    figure.update_yaxes(tickmode="array", tickvals=ordered.contributor.tolist(), automargin=True)
    return figure
