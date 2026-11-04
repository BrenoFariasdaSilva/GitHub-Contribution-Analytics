"""Tests for safe configuration loading."""

import tomllib
from pathlib import Path

import pytest

from contribution_analytics.config import config_path, load_config


def test_config_path_prefers_explicit_value(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """An explicit CLI path wins over the environment setting."""
    monkeypatch.setenv("CONTRIBUTION_ANALYTICS_CONFIG", "environment.yaml")
    assert config_path("explicit.yaml", tmp_path) == Path("explicit.yaml")


def test_load_config_adds_safe_defaults(tmp_path: Path) -> None:
    """A minimal valid configuration receives non-sensitive defaults."""
    path = tmp_path / "settings.yaml"
    path.write_text("repositories:\n  sample:\n    path: /tmp/sample\n", encoding="utf-8")
    assert load_config(path)["timezone"] == "America/Sao_Paulo"


def test_load_config_rejects_missing_repository_paths(tmp_path: Path) -> None:
    """Repository entries require an explicit local path."""
    path = tmp_path / "settings.yaml"
    path.write_text("repositories:\n  sample: {}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="requires named repositories"):
        load_config(path)


def test_load_config_rejects_invalid_timezone(tmp_path: Path) -> None:
    """Timezone values are validated before analytics begins."""
    path = tmp_path / "settings.yaml"
    path.write_text("repositories:\n  sample:\n    path: /tmp/sample\ntimezone: nowhere/invalid\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid timezone"):
        load_config(path)


def test_local_dashboard_disables_usage_telemetry() -> None:
    """The local-first browser must not send Streamlit usage events."""
    settings = tomllib.loads((Path(__file__).resolve().parents[1] / ".streamlit" / "config.toml").read_text())
    assert settings["browser"]["gatherUsageStats"] is False
