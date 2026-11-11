"""Command-line interface for local Git contribution analytics."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from contribution_analytics.branding import resolve_branding
from contribution_analytics.config import config_path, load_config
from contribution_analytics.git import analyze_repo, current_loc, load_data, save_data
from contribution_analytics.metrics import export_all, github_status
from contribution_analytics.repositories import git_available, inspect_cache, resolve_remote


def settings(args: argparse.Namespace) -> dict[str, object]:
    """Load settings from the requested configuration path."""
    return load_config(config_path(args.config, ROOT))


def branding(args: argparse.Namespace) -> object:
    """Resolve the identity shared by CLI output and generated exports."""
    return resolve_branding(ROOT, getattr(args, "display_name", None), str(settings(args)["display_name"]))


def analyze(args: argparse.Namespace) -> None:
    """Analyze configured repositories and save a local cache."""
    config = settings(args)
    repositories = config["repositories"]
    selected = list(repositories) if args.repo == "all" else [args.repo]
    if unknown := set(selected) - set(repositories):
        raise ValueError(f"Unknown repository: {', '.join(sorted(unknown))}. Available: {', '.join(repositories)}")
    if not git_available():
        raise RuntimeError("Git executable missing; install Git or run make ensure-git")
    commits, files, loc, metadata = [], [], [], []
    for name in selected:
        item = repositories[name]
        cache_status = None
        if "url" in item:
            repository, cache_status = resolve_remote(name, item["url"], ROOT / "data" / "repositories")
            print(f"{name}: remote {cache_status}")
        else:
            repository = Path(item["path"])
        repo_commits, repo_files, meta = analyze_repo(name, repository, config)
        if cache_status:
            meta["cache_status"] = cache_status
        commits.append(repo_commits)
        files.append(repo_files)
        loc.append(current_loc(name, repository, config))
        metadata.append(meta)
        print(f"{name}: {len(repo_commits)} unique commits, {len(repo_files)} changed-file records")
    if args.repo != "all":
        try:
            cached_commits, cached_files, cached_loc, cached_metadata = load_data(ROOT / "data" / "processed")
        except FileNotFoundError:
            cached_commits, cached_files, cached_loc, cached_metadata = (
                pd.DataFrame(),
                pd.DataFrame(),
                pd.DataFrame(),
                [],
            )
        commits.insert(
            0, cached_commits[~cached_commits.repo.isin(selected)] if not cached_commits.empty else cached_commits
        )
        files.insert(0, cached_files[~cached_files.repo.isin(selected)] if not cached_files.empty else cached_files)
        loc.insert(0, cached_loc[~cached_loc.repo.isin(selected)] if not cached_loc.empty else cached_loc)
        metadata = [item for item in cached_metadata if item.get("name") not in selected] + metadata
    save_data(
        ROOT / "data" / "processed",
        pd.concat(commits, ignore_index=True),
        pd.concat(files, ignore_index=True),
        pd.concat(loc, ignore_index=True),
        metadata,
    )
    print(f"GitHub: {github_status()['state']}")


def export(args: argparse.Namespace) -> None:
    """Generate public-facing exports from the local analysis cache."""
    commits, files, loc, metadata = load_data(ROOT / "data" / "processed")
    paths = export_all(ROOT, commits, files, loc, metadata, branding(args), str(settings(args)["timezone"]))
    print(f"Generated {len(paths)} exports")


def diagnostics(args: argparse.Namespace) -> None:
    """Report local paths and remote cache state, optionally refreshing remotes."""
    config = settings(args)
    if not git_available():
        print("Git executable missing; install Git or run make ensure-git")
        return
    for name, item in config["repositories"].items():
        if "url" in item:
            if getattr(args, "refresh", False):
                try:
                    _, state = resolve_remote(name, item["url"], ROOT / "data" / "repositories")
                except RuntimeError as error:
                    state = str(error)
            else:
                _, state = inspect_cache(name, item["url"], ROOT / "data" / "repositories")
            print(f"{name}: remote URL configured; {state}")
        else:
            repository = Path(item["path"])
            print(
                f"{name}: {'valid local repository' if (repository / '.git').exists() else 'missing local repository'}"
            )
    print(f"GitHub: {github_status()['reason']}")


def tests(_: argparse.Namespace) -> None:
    """Run the project test suite through pytest."""
    import pytest

    raise SystemExit(pytest.main([str(ROOT / "tests")]))


def main() -> None:
    """Parse CLI arguments and dispatch the chosen action."""
    default_name = str(load_config(config_path(None, ROOT))["display_name"])
    parser = argparse.ArgumentParser(
        description=f"{resolve_branding(ROOT, configured_name=default_name).title} local-first analytics"
    )
    parser.add_argument(
        "--config", help="Path to YAML settings; defaults to CONTRIBUTION_ANALYTICS_CONFIG or config/settings.yaml"
    )
    parser.add_argument("--display-name", help="Override the resolved application display name for this invocation")
    actions = parser.add_subparsers(dest="action", required=True)
    analyze_parser = actions.add_parser("analyze", help="Analyze configured Git repositories")
    analyze_parser.add_argument("--repo", default="all", help="Configured repository name or 'all'")
    analyze_parser.set_defaults(func=analyze)
    export_parser = actions.add_parser("export", help="Create CSV, JSON, and HTML exports")
    export_parser.add_argument("--all", action="store_true", help="Export all available report formats")
    export_parser.set_defaults(func=export)
    diagnostics_parser = actions.add_parser("diagnostics", help="Inspect local repositories and remote caches")
    diagnostics_parser.add_argument("--refresh", action="store_true", help="Clone or refresh remote caches")
    diagnostics_parser.set_defaults(func=diagnostics)
    actions.add_parser("test", help="Run tests").set_defaults(func=tests)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
