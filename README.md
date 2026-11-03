# GitHub Contribution Analytics

Local-first Streamlit dashboard for contribution, source-code, and historical Git analytics across configured repositories. It never writes to source repositories or GitHub.

![GitHub Code Size](https://img.shields.io/github/languages/code-size/BrenoFariasdaSilva/GitHub-Contribution-Analytics)
![GitHub Last Commit](https://img.shields.io/github/last-commit/BrenoFariasdaSilva/GitHub-Contribution-Analytics)
![GitHub License](https://img.shields.io/github/license/BrenoFariasdaSilva/GitHub-Contribution-Analytics)

![RepoBeats statistics](https://repobeats.axiom.co/api/embed/1baf2fdc789267d25b7a24b9755164ef7dc772e4.svg)

## Features

- Analyze deduplicated Git history, source-file changes, and current tracked-file lines of code.
- Explore contributions, commit activity, languages, files/modules, collaboration, and historical churn in a filterable dashboard.
- Export CSV, JSON, an HTML executive summary, and high-resolution chart PNGs.
- Work fully offline for Git-based analytics; GitHub PR, issue, and review data is optional.

## Requirements

- Python 3.12 or later
- Git
- One or more local Git repositories to analyze

## Setup

Clone the repository and create local configuration:

```bash
git clone https://github.com/BrenoFariasdaSilva/GitHub-Contribution-Analytics.git
cd GitHub-Contribution-Analytics
cp config/settings.example.yaml config/settings.yaml
```

Edit `config/settings.yaml` with arbitrary repository names and paths, exact identity aliases, exclusions, timezone, bot patterns, and feature switches. This local file is ignored by Git. `CONTRIBUTION_ANALYTICS_CONFIG` can select another local settings file, while `CONTRIBUTION_ANALYTICS_DISPLAY_NAME` overrides the title derived from this application's Git origin.

The distribution is `github-contribution-analytics`; Python integrations import the generic package namespace:

```python
from contribution_analytics.git import analyze_repo
from contribution_analytics.metrics import summary
```

## Install and run

The quickest path creates a virtual environment, installs dependencies, refreshes local Git analysis and exports, then starts the dashboard:

```bash
make run
```

Or run the steps directly:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python main.py diagnostics
.venv/bin/python main.py analyze --repo all
.venv/bin/python main.py export --all
.venv/bin/python -m streamlit run app.py
```

## Commands

- `python main.py [--config PATH] analyze --repo all|CONFIGURED_NAME` — extract deduplicated Git history and current tracked-file LoC for any configured repository.
- `python main.py export --all` — write CSV, JSON, and HTML reports under `exports/`.
- `python main.py diagnostics` — validate configured repositories and GitHub availability.
- `python main.py test` — run the test suite.
- `make lint` — run Ruff.

## Dashboard

Pages cover overview, a project-derived contribution calendar, contributors, commits, current LoC and historical churn, ownership caveats, PRs, issues, repository comparison, languages, files/modules, collaboration, historical trends, data exploration, exports, and source configuration. Charts can be filtered by repository, contributor, date range, and bot inclusion.

Every chart has a high-resolution PNG download option. **Prepare all PNG assets (ZIP)** renders and packages the available local-data charts for the selected filters.

## Metric definitions

- **Unique commits** — SHA-deduplicated commits reachable from all available refs.
- **Historical additions, deletions, and churn** — Git `--numstat` for ordinary commits only; merge commits are excluded to avoid misleading churn.
- **Current LoC** — physical lines in Git-tracked, readable source files after configured exclusions; it is not historical additions.
- **Activity calendar** — local Git authored commits in the configured timezone; it is not GitHub's official contribution calendar.
- **Identity** — author and committer are retained separately. Contributors are canonicalized only through exact email/name aliases in `config/settings.yaml`.
- **Ownership** — disabled by default. Future Git blame data represents surviving-line attribution, not responsibility or quality.

## Privacy and GitHub API

Git commands are read-only, generated data stays in this project, and no tokens are stored or printed. Git-only analysis works fully offline. Local settings, caches, and generated CSV/JSON/HTML/PNG files are ignored. Public JSON metadata excludes absolute local repository paths, and report text is HTML-escaped.

Private-repository PR, issue, review, and lifecycle metrics require a valid GitHub CLI session:

```bash
gh auth login -h github.com
```

If authentication or collection is unavailable, those metrics are shown as unavailable rather than as zero or inferred data.

## Limitations

History is collected in bulk with one `git log` call per repository and cached in `data/processed`. Current LoC skips binary and unreadable tracked files. Rename detection is limited to Git's `numstat` output. Branch lifetime, GitHub reviews, issues, PRs, and blame ownership are never inferred when their data is absent. Shallow repositories are flagged in metadata.

## Development checks

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check .
.venv/bin/python -m ruff format --check .
```

The tests also enforce docstrings for every function in `app.py`, `main.py`, `src/`, and `tests/`.

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for branch, commit, and pull-request guidance.

## License

Distributed under the [Apache License 2.0](LICENSE).
