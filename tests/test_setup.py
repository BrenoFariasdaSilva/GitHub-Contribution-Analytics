"""Package-manager selection and installation approval tests without system changes."""

from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest

from scripts import project_setup


@pytest.mark.parametrize(
    ("system", "manager", "expected"),
    [
        ("Linux", "apt-get", "apt-get"),
        ("Linux", "dnf", "dnf"),
        ("Linux", "yum", "yum"),
        ("Linux", "pacman", "pacman"),
        ("Linux", "zypper", "zypper"),
        ("Darwin", "brew", "brew"),
        ("Darwin", "xcode-select", "xcode-select"),
        ("Windows", "winget", "winget"),
        ("Windows", "choco", "choco"),
        ("Windows", "scoop", "scoop"),
    ],
)
def test_installation_command_selects_available_manager(monkeypatch, system, manager, expected) -> None:
    """Each supported platform uses an installed package manager."""
    monkeypatch.setattr(project_setup.shutil, "which", lambda name: f"/bin/{name}" if name == manager else None)
    monkeypatch.setattr(project_setup.os, "geteuid", lambda: 0, raising=False)
    assert project_setup.installation_command(system)[0] == expected


def test_installation_command_uses_sudo_or_reports_missing_manager(monkeypatch) -> None:
    """Linux requests sudo only when needed and gives actionable fallback errors."""
    monkeypatch.setattr(
        project_setup.shutil, "which", lambda name: f"/bin/{name}" if name in {"apt-get", "sudo"} else None
    )
    monkeypatch.setattr(project_setup.os, "geteuid", lambda: 1000, raising=False)
    assert project_setup.installation_command("Linux")[:2] == ["sudo", "apt-get"]
    monkeypatch.setattr(project_setup.shutil, "which", lambda name: None)
    with pytest.raises(RuntimeError, match="package manager"):
        project_setup.installation_command("Linux")


def test_git_present_skips_installer(monkeypatch) -> None:
    """An existing Git executable never starts package installation."""
    monkeypatch.setattr(project_setup, "git_available", lambda: True)
    monkeypatch.setattr(project_setup, "installation_command", lambda: pytest.fail("installer selected"))
    project_setup.ensure_git()


def test_git_opt_out_and_approval(monkeypatch) -> None:
    """Missing Git respects opt-out and explicit approval before running an installer."""
    monkeypatch.setattr(project_setup, "git_available", lambda: False)
    monkeypatch.setattr(project_setup, "installation_command", lambda: ["brew", "install", "git"])
    monkeypatch.setenv("AUTO_INSTALL_GIT", "0")
    with pytest.raises(RuntimeError, match="missing"):
        project_setup.ensure_git()
    monkeypatch.setenv("AUTO_INSTALL_GIT", "1")
    monkeypatch.setattr("builtins.input", lambda _: "no")
    with pytest.raises(RuntimeError, match="declined"):
        project_setup.ensure_git()


def test_install_failure_and_post_install_verification(monkeypatch) -> None:
    """Installer failures and PATH lag are reported instead of claiming success."""
    monkeypatch.setattr(project_setup, "git_available", lambda: False)
    monkeypatch.setattr(project_setup, "installation_command", lambda: ["brew", "install", "git"])
    monkeypatch.setenv("GIT_INSTALL_APPROVED", "1")
    monkeypatch.setattr(project_setup.subprocess, "run", lambda *_args, **_kwargs: SimpleNamespace(returncode=1))
    with pytest.raises(RuntimeError, match="exit code 1"):
        project_setup.ensure_git()
    monkeypatch.setattr(project_setup.subprocess, "run", lambda *_args, **_kwargs: SimpleNamespace(returncode=0))
    with pytest.raises(RuntimeError, match="not yet usable"):
        project_setup.ensure_git()


def test_successful_installation(monkeypatch) -> None:
    """An approved installation succeeds only after Git becomes available."""
    states = iter([False, True])
    monkeypatch.setattr(project_setup, "git_available", lambda: next(states))
    monkeypatch.setattr(project_setup, "installation_command", lambda: ["brew", "install", "git"])
    monkeypatch.setattr(project_setup.subprocess, "run", lambda *_args, **_kwargs: SimpleNamespace(returncode=0))
    monkeypatch.setenv("GIT_INSTALL_APPROVED", "1")
    project_setup.ensure_git()


def test_chocolatey_requires_administrator(monkeypatch) -> None:
    """Chocolatey is never invoked without an administrator terminal."""
    monkeypatch.setattr(project_setup, "git_available", lambda: False)
    monkeypatch.setattr(project_setup, "installation_command", lambda: ["choco", "install", "git", "-y"])
    monkeypatch.setattr(project_setup.platform, "system", lambda: "Windows")
    monkeypatch.setattr(project_setup, "windows_admin", lambda: False)
    monkeypatch.setattr(project_setup.subprocess, "run", lambda *_args, **_kwargs: pytest.fail("installer invoked"))
    monkeypatch.setenv("GIT_INSTALL_APPROVED", "1")
    with pytest.raises(RuntimeError, match="administrator"):
        project_setup.ensure_git()


def test_run_dispatches_command_with_current_environment(monkeypatch) -> None:
    """The Make wrapper executes its child and propagates its exit status."""
    monkeypatch.setattr(sys, "argv", ["project_setup.py", "run", "python", "-m", "pytest"])
    monkeypatch.setattr(project_setup.platform, "system", lambda: "Windows")
    called = []
    monkeypatch.setattr(project_setup, "refresh_windows_path", lambda: called.append("path"))

    def run(command, **_kwargs):
        """Record the command forwarded by the setup helper."""
        called.append(command)
        return SimpleNamespace(returncode=3)

    monkeypatch.setattr(project_setup.subprocess, "run", run)
    with pytest.raises(SystemExit) as error:
        project_setup.main()
    assert called == ["path", ["python", "-m", "pytest"]] and error.value.code == 3
