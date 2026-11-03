# Configuration

Copy `config/settings.example.yaml` to ignored `config/settings.yaml`, then list one or more named local Git repositories. Names are arbitrary and are selected with `main.py analyze --repo NAME`.

An explicit `--config` path takes precedence over `CONTRIBUTION_ANALYTICS_CONFIG`, followed by the default local settings file. `CONTRIBUTION_ANALYTICS_DISPLAY_NAME` supplies an optional application-title override.
