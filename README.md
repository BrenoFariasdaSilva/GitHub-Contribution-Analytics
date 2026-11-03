<div align="center">
  
# [GitHub-Contribution-Analytics.](https://github.com/BrenoFariasdaSilva/GitHub-Contribution-Analytics) <img src="https://github.com/BrenoFariasdaSilva/GitHub-Contribution-Analytics/blob/eb9af994aa7e9096bd8dad4bc15b91b01f38208c/.assets/Images/Github.svg"  width="3%" height="3%">

</div>

<div align="center">
  
---

GitHub Contribution Analytics is a local-first Streamlit dashboard for exploring contribution activity, source-code evolution, and Git history across any configured repositories. Analysis is strictly read-only: it never changes source repositories, rewrites Git history, or writes data to GitHub.

Use the dashboard to examine unique commits, contributors, activity calendars and streaks, additions, deletions, churn, languages, files, modules, and current lines of code. Interactive filters support repository, contributor, date-range, and bot selection, while CSV, JSON, HTML, PNG, and ZIP exports make it easy to share or retain the resulting analysis.

---

</div>

<div align="center">

![GitHub Code Size in Bytes](https://img.shields.io/github/languages/code-size/BrenoFariasdaSilva/GitHub-Contribution-Analytics)
![GitHub Commits](https://img.shields.io/github/commit-activity/t/BrenoFariasdaSilva/GitHub-Contribution-Analytics/main)
![GitHub Last Commit](https://img.shields.io/github/last-commit/BrenoFariasdaSilva/GitHub-Contribution-Analytics)
![GitHub Forks](https://img.shields.io/github/forks/BrenoFariasdaSilva/GitHub-Contribution-Analytics)
![GitHub Language Count](https://img.shields.io/github/languages/count/BrenoFariasdaSilva/GitHub-Contribution-Analytics)
![GitHub License](https://img.shields.io/github/license/BrenoFariasdaSilva/GitHub-Contribution-Analytics)
![GitHub Stars](https://img.shields.io/github/stars/BrenoFariasdaSilva/GitHub-Contribution-Analytics)
![GitHub Contributors](https://img.shields.io/github/contributors/BrenoFariasdaSilva/GitHub-Contribution-Analytics)
![wakatime](https://wakatime.com/badge/github/BrenoFariasdaSilva/GitHub-Contribution-Analytics.svg)

</div>

<div align="center">
  
![RepoBeats Statistics](https://repobeats.axiom.co/api/embed/1baf2fdc789267d25b7a24b9755164ef7dc772e4.svg "Repobeats analytics image")

</div>

## Setup

Clone the repository and create local configuration:

```bash
git clone https://github.com/BrenoFariasdaSilva/GitHub-Contribution-Analytics.git
cd GitHub-Contribution-Analytics
cp config/settings.example.yaml config/settings.yaml
```

Edit `config/settings.yaml` with arbitrary repository names and paths, exact identity aliases, exclusions, timezone, bot patterns, and feature switches. This local file is ignored by Git. Display-name precedence is runtime `--display-name`, nonempty `CONTRIBUTION_ANALYTICS_DISPLAY_NAME`, nonempty YAML `display_name`, Git origin, then the application directory. All calendar metrics use the validated `timezone` setting.

The distribution is `github-contribution-analytics`; Python integrations import the generic package namespace:

```python
from contribution_analytics.git import analyze_repo
from contribution_analytics.metrics import summary
```

## Requirements

- Python 3.12 or later
- Git
- One or more local Git repositories to analyze

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

PNG export uses Plotly with Kaleido 1.x and requires a locally installed Google Chrome or Chromium browser. The application reports export failures instead of generating invalid downloads.

## Commands

- `python main.py [--config PATH] analyze --repo all|CONFIGURED_NAME` — extract deduplicated Git history and current tracked-file LoC for any configured repository.
- `python main.py export --all` — write CSV, JSON, and HTML reports under `exports/`.
- `python main.py diagnostics` — validate configured repositories and GitHub availability.
- `python main.py test` — run the test suite.
- `make lint` — run Ruff.

## Dashboard

Pages cover repository activity, contributor insights, code evolution, commit patterns, a project-derived contribution calendar, current LoC and historical churn, repository comparison, languages, files/modules, collaboration, historical trends, exports, and source configuration. Charts can be filtered by repository, contributor, date range, and bot inclusion; repository colors are stable and derived from each configured name.

Every chart has a high-resolution PNG download option. **Prepare all PNG assets (ZIP)** renders and packages the available local-data charts for the selected filters.

## Metric definitions

- **Unique commits** — SHA-deduplicated commits reachable from all available refs.
- **Historical additions, deletions, and churn** — Git `--numstat` for ordinary commits only; merge commits are excluded to avoid misleading churn.
- **Current LoC** — physical lines in Git-tracked, readable source files after configured exclusions; it is not historical additions.
- **Activity calendar** — local Git authored commits in the configured timezone; it is not GitHub's official contribution calendar.
- **Identity** — author and committer are retained separately. Contributors are canonicalized only through exact email/name aliases in `config/settings.yaml`.
- **Ownership** — disabled by default. Future Git blame data represents surviving-line attribution, not responsibility or quality.
- **Commit timing** — local author timestamp distributions and intervals; they do not measure time spent programming.
- **Repository comparison** — filtered commit, contributor, activity-day, LoC, churn, and Conventional Commit adoption figures; higher values are not quality rankings.

## Privacy and GitHub API

Git commands are read-only, generated data stays in this project, and no tokens are stored or printed. Git-only analysis works fully offline. Local settings, caches, and generated CSV/JSON/HTML/PNG files are ignored. Public JSON metadata excludes absolute local repository paths, and report text is HTML-escaped.

Private-repository PR, issue, review, and lifecycle metrics require a valid GitHub CLI session:

```bash
gh auth login -h github.com
```

If authentication or collection is unavailable, those metrics are shown as unavailable rather than as zero or inferred data.

## Limitations

History is collected in bulk with one `git log` call per repository and cached in `data/processed`. Current LoC skips binary and unreadable tracked files. Rename detection is limited to Git's `numstat` output. Branch lifetime, GitHub reviews, issues, PRs, and blame ownership are never inferred when their data is absent. Shallow repositories are flagged in metadata.

## Development verifications

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
