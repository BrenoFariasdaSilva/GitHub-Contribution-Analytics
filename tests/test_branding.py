"""Tests for application identity resolution."""

from pathlib import Path

from contribution_analytics.branding import display_name, filename_slug, repository_name, resolve_branding


def test_remote_urls_resolve_repository_name() -> None:
    """HTTPS and SSH origins resolve to their repository component."""
    assert repository_name("https://github.com/example/Project-Name.git") == "Project-Name"
    assert repository_name("git@github.com:example/Project-Name") == "Project-Name"


def test_invalid_remote_and_filename_slug_are_safe() -> None:
    """Invalid remotes and special characters use safe outcomes."""
    assert repository_name("invalid") is None
    assert filename_slug("A Project! / 2026") == "a-project-2026"


def test_override_wins_over_application_directory(tmp_path: Path) -> None:
    """A configured display name has highest precedence."""
    branding = resolve_branding(tmp_path / "application-name", runtime_name="Custom analytics")
    assert branding.display_name == "Custom Analytics"
    assert branding.slug == "custom-analytics"


def test_display_name_normalizes_separators() -> None:
    """Repository separators become readable words."""
    assert display_name("github_contribution-analytics") == "GitHub Contribution Analytics"


def test_environment_override_precedes_yaml(monkeypatch, tmp_path: Path) -> None:
    """A nonempty environment name overrides a configured YAML display name."""
    monkeypatch.setenv("CONTRIBUTION_ANALYTICS_DISPLAY_NAME", "Environment API")
    assert resolve_branding(tmp_path, configured_name="YAML name").display_name == "Environment API"


def test_empty_environment_keeps_yaml_value(monkeypatch, tmp_path: Path) -> None:
    """Whitespace-only environment values do not suppress configured branding."""
    monkeypatch.setenv("CONTRIBUTION_ANALYTICS_DISPLAY_NAME", " ")
    assert resolve_branding(tmp_path, configured_name="YAML name").display_name == "YAML Name"
