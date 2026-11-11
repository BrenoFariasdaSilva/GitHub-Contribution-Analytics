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
    """Repository entries require exactly one explicit source."""
    path = tmp_path / "settings.yaml"
    path.write_text("repositories:\n  sample: {}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="exactly one of path or url"):
        load_config(path)


@pytest.mark.parametrize(
    "url",
    [
        "https://github.com/OWNER/backend.git",
        "https://github.com/OWNER/backend",
        "git@github.com:OWNER/backend.git",
        "ssh://git@example.org/owner/repo.git",
        "file:///tmp/test-remote.git",
    ],
)
def test_load_config_accepts_remote_urls(tmp_path: Path, url: str) -> None:
    """Common HTTPS, SSH, and local test remotes are accepted."""
    path = tmp_path / "settings.yaml"
    path.write_text(f"repositories:\n  backend:\n    url: {url}\n    github: OWNER/backend\n", encoding="utf-8")
    assert load_config(path)["repositories"]["backend"] == {"url": url, "github": "OWNER/backend"}


def test_load_config_accepts_mixed_sources(tmp_path: Path) -> None:
    """Local and URL repositories coexist without changing existing options."""
    path = tmp_path / "settings.yaml"
    path.write_text(
        "repositories:\n  local:\n    path: /tmp/local\n  remote:\n    url: https://example.org/team/repo.git\n"
        "github_enabled: false\nownership_enabled: true\n",
        encoding="utf-8",
    )
    config = load_config(path)
    assert config["repositories"]["local"]["path"] == "/tmp/local"
    assert config["repositories"]["remote"]["url"].endswith("repo.git")
    assert config["github_enabled"] is False and config["ownership_enabled"] is True


@pytest.mark.parametrize(
    "source",
    [
        "    path: /tmp/local\n    url: https://example.org/repo.git",
        "    path: ''\n    url: https://example.org/repo.git",
        "    path: ''",
        "    url: ext::ssh example.org",
        "    url: https://user:secret@example.org/repo.git",
        "    url: https://example.org/../repo.git",
        "    url: git@github.com:--upload-pack=evil",
        "    url: https://example.org/repo.git?token=secret",
    ],
)
def test_load_config_rejects_ambiguous_or_unsafe_sources(tmp_path: Path, source: str) -> None:
    """Configuration rejects multiple sources, credentials, and unsafe Git transports."""
    path = tmp_path / "settings.yaml"
    path.write_text(f"repositories:\n  sample:\n{source}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="sample"):
        load_config(path)


def test_load_config_rejects_invalid_timezone(tmp_path: Path) -> None:
    """Timezone values are validated before analytics begins."""
    path = tmp_path / "settings.yaml"
    path.write_text("repositories:\n  sample:\n    path: /tmp/sample\ntimezone: nowhere/invalid\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid timezone"):
        load_config(path)


def test_load_config_rejects_non_mapping(tmp_path: Path) -> None:
    """Malformed YAML root values receive a clear validation error."""
    path = tmp_path / "settings.yaml"
    path.write_text("- repository\n", encoding="utf-8")
    with pytest.raises(ValueError, match="YAML mapping"):
        load_config(path)


def test_local_dashboard_disables_usage_telemetry() -> None:
    """The local-first browser must not send Streamlit usage events."""
    settings = tomllib.loads((Path(__file__).resolve().parents[1] / ".streamlit" / "config.toml").read_text())
    assert settings["browser"]["gatherUsageStats"] is False
