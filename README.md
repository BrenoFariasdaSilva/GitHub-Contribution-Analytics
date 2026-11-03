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
.venv/bin/streamlit run app.py
```

### Dependencies

1. Install the project dependencies with the following command:

   ```bash
   make dependencies
   ```

### Dataset - Optional

1. Download the dataset from [WEBSITE-HERE]() and place it in this project directory `(/Template-Project)` and run the following command:

   ```bash
   make dataset
   ```

## Usage

In order to run the project, run the following command:

```bash
make run
```

## Results - Optional

Discuss the results obtained in the project.

## How to Cite?

If you use the Repository-Name in your research, please cite it using the following BibTeX entry:

```
@misc{softwareRepository-Name:2024,
  title = {Repository-Name: Project-Description},
  author = {Breno Farias da Silva},
  year = {2024},
  howpublished = {https://github.com/BrenoFariasdaSilva/Repository-Name},
  note = {Accessed on September 11, 2024}
}
```

Additionally, a `main.bib` file is available in the root directory of this repository, in which contains the BibTeX entry for this project.

If you find this repository valuable, please don't forget to give it a ⭐ to show your support! Contributions are highly encouraged, whether by creating issues for feedback or submitting pull requests (PRs) to improve the project. For details on how to contribute, please refer to the [Contributing](#contributing) section below.

Thank you for your support and for recognizing the contribution of this tool to your work!

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
    <td align="center">
      <a href="#" title="defina o titulo do link">
        <img src="https://github.com/BrenoFariasdaSilva.png" width="100px;" alt="My Profile Picture"/><br>
        <sub>
          <b>Breno Farias da Silva</b>
        </sub>
      </a>
    </td>
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

### Creative Commons Zero v1.0 Universal (CC0 1.0)

This project is licensed under the [Creative Commons Zero v1.0 Universal](LICENSE) (CC0 1.0) Public Domain Dedication. This means that the work is released into the public domain, allowing anyone to use, modify, distribute, and perform the work, even for commercial purposes, without asking permission and without attributing the original author(s). However, it's appreciated if you include a copy of the license or a link to it in any significant use or distribution. For more details, see the [LICENSE](LICENSE) file in this repository.

### MIT License

This project is licensed under the [MIT License](LICENSE). The MIT License is a permissive license that is short and to the point. It lets people do anything they want with your code as long as they provide attribution back to you and don’t hold you liable. This license allows for commercial use, modification, distribution, private use, and sublicensing. See the [LICENSE](LICENSE) file in this repository for more details.
