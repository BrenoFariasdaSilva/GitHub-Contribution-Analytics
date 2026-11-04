"""Regression tests for contributor chart readability."""

import pandas as pd

from contribution_analytics.charts import contributor_rank_bar


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
