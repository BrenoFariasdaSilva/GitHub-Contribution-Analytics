"""Cross-platform project setup tasks used before the virtual environment exists."""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def git_available() -> bool:
    """Check that Git can actually run, not merely that a path exists."""
    executable = shutil.which("git")
    return bool(
        executable and subprocess.run([executable, "--version"], capture_output=True, check=False).returncode == 0
    )


def installation_command(system: str | None = None) -> list[str]:
    """Select an installed, supported package manager without changing the system."""
    system = system or platform.system()
    if system == "Linux":
        managers = {
            "apt-get": ["apt-get", "install", "-y", "git"],
            "dnf": ["dnf", "install", "-y", "git"],
            "yum": ["yum", "install", "-y", "git"],
            "pacman": ["pacman", "-S", "--noconfirm", "git"],
            "zypper": ["zypper", "--non-interactive", "install", "git"],
        }
        command = next((value for name, value in managers.items() if shutil.which(name)), None)
        if command is None:
            raise RuntimeError("No supported Linux package manager found; install Git with your distribution's manager")
        if hasattr(os, "geteuid") and os.geteuid() != 0:
            if not shutil.which("sudo"):
                raise RuntimeError("Git installation requires administrator rights; install Git or provide sudo")
            return ["sudo", *command]
        return command
    if system == "Darwin":
        if shutil.which("brew"):
            return ["brew", "install", "git"]
        if shutil.which("xcode-select"):
            return ["xcode-select", "--install"]
        raise RuntimeError("Install Homebrew or Apple's Command Line Tools, then install Git")
    if system == "Windows":
        managers = {
            "winget": [
                "winget",
                "install",
                "--id",
                "Git.Git",
                "-e",
                "--source",
                "winget",
                "--accept-package-agreements",
                "--accept-source-agreements",
            ],
            "choco": ["choco", "install", "git", "-y"],
            "scoop": ["scoop", "install", "git"],
        }
        command = next((value for name, value in managers.items() if shutil.which(name)), None)
        if command is None:
            raise RuntimeError("No supported Windows package manager found; install Git for Windows manually")
        return command
    raise RuntimeError(f"Automatic Git installation is unsupported on {system}; install Git manually")


def refresh_windows_path() -> None:
    """Discover common Git install locations after Windows installers update PATH externally."""
    candidates = [
        Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Git" / "cmd",
        Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))) / "Programs" / "Git" / "cmd",
        Path(os.environ.get("ChocolateyInstall", "C:/ProgramData/chocolatey")) / "bin",
        Path.home() / "scoop" / "shims",
    ]
    os.environ["PATH"] = os.pathsep.join(
        [str(path) for path in candidates if path.is_dir()] + [os.environ.get("PATH", "")]
    )


def windows_admin() -> bool:
    """Check whether Chocolatey can install packages in this terminal."""
    import ctypes

    return bool(ctypes.windll.shell32.IsUserAnAdmin())


def ensure_git(*, install: bool = True) -> None:
    """Offer a transparent installation, honoring opt-out and explicit approval."""
    if git_available():
        print("Git is available")
        return
    if not install or os.environ.get("AUTO_INSTALL_GIT", "1") == "0":
        raise RuntimeError("Git executable missing; install Git manually or enable AUTO_INSTALL_GIT=1")
    command = installation_command()
    print(f"Git is missing. Proposed installation: {' '.join(command)}")
    if os.environ.get("GIT_INSTALL_APPROVED") != "1":
        try:
            answer = input("Run this installation command? [y/N] ").strip().lower()
        except EOFError as error:
            raise RuntimeError(
                "Git installation needs approval; set GIT_INSTALL_APPROVED=1 after reviewing the command"
            ) from error
        if answer not in {"y", "yes"}:
            raise RuntimeError("Git installation declined")
    if command[0] == "choco" and platform.system() == "Windows" and not windows_admin():
        raise RuntimeError("Chocolatey needs an administrator terminal; reopen one or use winget/Scoop")
    result = subprocess.run(command, check=False)
    if result.returncode:
        raise RuntimeError(f"Git installation failed with exit code {result.returncode}")
    if platform.system() == "Windows":
        refresh_windows_path()
    if not git_available():
        raise RuntimeError(
            "Installer finished but Git is not yet usable; complete any system dialog or restart your terminal"
        )
    print("Git is available")


def main() -> None:
    """Dispatch Git setup, configuration copying, or cache cleanup."""
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["check-git", "install-git", "ensure-git", "config", "clean", "run"])
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.action == "check-git":
        ensure_git(install=False)
    elif args.action in {"install-git", "ensure-git"}:
        ensure_git()
    elif args.action == "config":
        destination = ROOT / "config" / "settings.yaml"
        if not destination.exists():
            shutil.copyfile(ROOT / "config" / "settings.example.yaml", destination)
    elif args.action == "run":
        if not args.command:
            raise RuntimeError("run requires a command")
        if platform.system() == "Windows":
            refresh_windows_path()
        raise SystemExit(subprocess.run(args.command, check=False).returncode)
    else:
        for name in (".pytest_cache", ".ruff_cache"):
            shutil.rmtree(ROOT / name, ignore_errors=True)


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as error:
        raise SystemExit(str(error)) from error
