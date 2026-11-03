# Architecture

`contribution_analytics` separates application identity, configuration, Git reads, metrics, privacy helpers, and documentation checks. The CLI and Streamlit dashboard call those shared modules rather than reimplementing analytics logic.

Git commands always use argument lists and run with `git -C`; the application never mutates an analyzed repository. Cached analysis data is local-only, while generated public metadata omits absolute repository paths.
