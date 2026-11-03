# GitHub Contribution Analytics

Local-first Streamlit dashboard for contribution, source-code, and historical Git analytics across configured repositories. It never writes to source repositories or GitHub.


<div align="center">

![GitHub Code Size in Bytes](https://img.shields.io/github/languages/code-size/BrenoFariasdaSilva/Angular-UI-Playground)
![GitHub Commits](https://img.shields.io/github/commit-activity/t/BrenoFariasdaSilva/Angular-UI-Playground/main)
![GitHub Last Commit](https://img.shields.io/github/last-commit/BrenoFariasdaSilva/Angular-UI-Playground)
![GitHub Forks](https://img.shields.io/github/forks/BrenoFariasdaSilva/Angular-UI-Playground)
![GitHub Language Count](https://img.shields.io/github/languages/count/BrenoFariasdaSilva/Angular-UI-Playground)
![GitHub License](https://img.shields.io/github/license/BrenoFariasdaSilva/Angular-UI-Playground)
![GitHub Stars](https://img.shields.io/github/stars/BrenoFariasdaSilva/Angular-UI-Playground)
![GitHub Contributors](https://img.shields.io/github/contributors/BrenoFariasdaSilva/Angular-UI-Playground)
![wakatime](https://wakatime.com/badge/github/BrenoFariasdaSilva/Angular-UI-Playground.svg)

</div>

<div align="center">
  
![RepoBeats Statistics](https://repobeats.axiom.co/api/embed/1baf2fdc789267d25b7a24b9755164ef7dc772e4.svg "Repobeats analytics image")

</div>

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

Contributions are what make the open-source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**. If you have suggestions for improving the code, your insights will be highly welcome.
In order to contribute to this project, please follow the guidelines below or read the [CONTRIBUTING.md](CONTRIBUTING.md) file for more details on how to contribute to this project, as it contains information about the commit standards and the entire pull request process.
Please follow these guidelines to make your contributions smooth and effective:

1. **Set Up Your Environment**: Ensure you've followed the setup instructions in the [Setup](#setup) section to prepare your development environment.

2. **Make Your Changes**:
   - **Create a Branch**: `git checkout -b feature/YourFeatureName`
   - **Implement Your Changes**: Make sure to test your changes thoroughly.
   - **Commit Your Changes**: Use clear commit messages, for example:
     - For new features: `git commit -m "FEAT: Add some AmazingFeature"`
     - For bug fixes: `git commit -m "FIX: Resolve Issue #123"`
     - For documentation: `git commit -m "DOCS: Update README with new instructions"`
     - For refactorings: `git commit -m "REFACTOR: Enhance component for better aspect"`
     - For snapshots: `git commit -m "SNAPSHOT: Temporary commit to save the current state for later reference"`
   - See more about crafting commit messages in the [CONTRIBUTING.md](CONTRIBUTING.md) file.

3. **Submit Your Contribution**:
   - **Push Your Changes**: `git push origin feature/YourFeatureName`
   - **Open a Pull Request (PR)**: Navigate to the repository on GitHub and open a PR with a detailed description of your changes.

4. **Stay Engaged**: Respond to any feedback from the project maintainers and make necessary adjustments to your PR.

5. **Celebrate**: Once your PR is merged, celebrate your contribution to the project!

## Collaborators

We thank the following people who contributed to this project:

<table>
  <tr>
    <td align="center">
      <a href="#" title="defina o titulo do link">
        <img src="https://github.com/BrenoFariasdaSilva.png" width="100px;" alt="My Profile Picture"/><br>
        <sub>
          <b>Breno Farias da Silva</b>
        </sub>
      </a>
    </td>
  </tr>
</table>

## License

### Apache License 2.0

This project is licensed under the [Apache License 2.0](LICENSE). This license permits use, modification, distribution, and sublicense of the code for both private and commercial purposes, provided that the original copyright notice and a disclaimer of warranty are included in all copies or substantial portions of the software. It also requires a clear attribution back to the original author(s) of the repository. For more details, see the [LICENSE](LICENSE) file in this repository.
