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


def settings(args: argparse.Namespace) -> dict[str, object]:
    """Load settings from the requested configuration path."""
    return load_config(config_path(args.config, ROOT))


def analyze(args: argparse.Namespace) -> None:
    """Analyze configured repositories and save a local cache."""
    config = settings(args)
    repositories = config["repositories"]
    selected = list(repositories) if args.repo == "all" else [args.repo]
    if unknown := set(selected) - set(repositories):
        raise ValueError(f"Unknown repository: {', '.join(sorted(unknown))}. Available: {', '.join(repositories)}")
    commits, files, loc, metadata = [], [], [], []
    for name in selected:
        item = repositories[name]
        repository = Path(item["path"])
        repo_commits, repo_files, meta = analyze_repo(name, repository, config)
        commits.append(repo_commits)
        files.append(repo_files)
        loc.append(current_loc(name, repository, config))
        metadata.append(meta)
        print(f"{name}: {len(repo_commits)} unique commits, {len(repo_files)} changed-file records")
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
    config = settings(args)
    paths = export_all(ROOT, commits, files, loc, metadata, resolve_branding(ROOT, str(config["display_name"])))
    print(f"Generated {len(paths)} exports")


def diagnostics(args: argparse.Namespace) -> None:
    """Report whether each configured repository is available locally."""
    config = settings(args)
    for name, item in config["repositories"].items():
        repository = Path(item["path"])
        print(f"{name}: {'found' if (repository / '.git').exists() else 'missing'}")
    print(f"GitHub: {github_status()['reason']}")


def tests(_: argparse.Namespace) -> None:
    """Run the project test suite through pytest."""
    import pytest

    raise SystemExit(pytest.main([str(ROOT / "tests")]))


def main() -> None:
    """Parse CLI arguments and dispatch the chosen action."""
    parser = argparse.ArgumentParser(description=f"{resolve_branding(ROOT).title} local-first analytics")
    parser.add_argument(
        "--config", help="Path to YAML settings; defaults to CONTRIBUTION_ANALYTICS_CONFIG or config/settings.yaml"
    )
    actions = parser.add_subparsers(dest="action", required=True)
    analyze_parser = actions.add_parser("analyze", help="Analyze configured Git repositories")
    analyze_parser.add_argument("--repo", default="all", help="Configured repository name or 'all'")
    analyze_parser.set_defaults(func=analyze)
    export_parser = actions.add_parser("export", help="Create CSV, JSON, and HTML exports")
    export_parser.add_argument("--all", action="store_true", help="Export all available report formats")
    export_parser.set_defaults(func=export)
    actions.add_parser("diagnostics", help="Validate configured repository paths").set_defaults(func=diagnostics)
    actions.add_parser("test", help="Run tests").set_defaults(func=tests)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
