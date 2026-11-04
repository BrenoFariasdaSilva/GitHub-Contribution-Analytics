"""Tests for redacted and escaped report exports."""

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

from contribution_analytics.branding import Branding
from contribution_analytics.metrics import export_all
from contribution_analytics.privacy import public_metadata


def test_export_html_escapes_title_and_metadata_hides_paths(tmp_path: Path) -> None:
    """Reports escape HTML and JSON metadata does not expose local paths."""
    commits = pd.DataFrame(columns=["sha", "contributor", "is_merge", "additions", "deletions", "author_date"])
    files = pd.DataFrame()
    loc = pd.DataFrame(columns=["path", "physical_loc", "language"])
    paths = export_all(
        tmp_path, commits, files, loc, [{"name": "sample", "path": "/private/path"}], Branding("<Unsafe>", "safe")
    )
    report = next(path for path in paths if path.suffix == ".html")
    assert "&lt;Unsafe&gt;" in report.read_text(encoding="utf-8")
    metadata = (tmp_path / "exports" / "json" / "analysis_metadata.json").read_text(encoding="utf-8")
    assert "/private/path" not in metadata


def test_kaleido_renders_png_bytes() -> None:
    """The supported Plotly and Kaleido stack produces a valid PNG signature."""
    image = go.Figure(go.Bar(x=["A", "B"], y=[1, 2])).to_image(format="png", width=640, height=480)
    assert image.startswith(b"\x89PNG\r\n\x1a\n") and len(image) > 1_000


def test_public_metadata_hides_local_repository_paths() -> None:
    """Dashboard metadata must not reveal private repository locations."""
    assert public_metadata([{"name": "api", "path": "/private/path"}]) == [{"name": "api"}]
