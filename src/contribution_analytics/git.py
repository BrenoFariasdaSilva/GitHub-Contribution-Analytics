from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

RECORD = "\x1e"
FIELD = "\x1f"
CONVENTIONAL = re.compile(
    r"^(?P<type>feat|fix|refactor|docs|test|chore|perf|style|build|ci|revert)(?:\((?P<scope>[^)]+)\))?(?P<breaking>!)?:",
    re.IGNORECASE,
)
LANGUAGES = {
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".mjs": "JavaScript",
    ".py": "Python",
    ".sql": "SQL",
    ".json": "JSON",
    ".css": "CSS",
    ".scss": "SCSS",
    ".html": "HTML",
    ".yml": "YAML",
    ".yaml": "YAML",
    ".sh": "Shell",
    ".md": "Markdown",
}


def run_git(repo: Path, *args: str) -> str:
    """Run a read-only Git command in a validated repository directory."""
    if not repo.is_dir():
        raise ValueError(f"Repository directory does not exist: {repo}")
    completed = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, encoding="utf-8", errors="replace", check=False
    )
    if completed.returncode:
        raise RuntimeError(completed.stderr.strip() or f"git {' '.join(args)} failed")
    return completed.stdout


def default_ref(repo: Path) -> str:
    """Return the configured remote default or a sensible local reference."""
    try:
        value = run_git(repo, "symbolic-ref", "--short", "refs/remotes/origin/HEAD").strip()
        if value:
            return value
    except RuntimeError:
        pass
    local = set(run_git(repo, "for-each-ref", "--format=%(refname:short)", "refs/heads").splitlines())
    for candidate in ("main", "master", "dev"):
        if candidate in local:
            return candidate
    return "HEAD"


def canonical(name: str, email: str, aliases: dict[str, str]) -> str:
    """Normalize an author only through explicit configured aliases."""
    keys = (email.strip().lower(), name.strip().lower())
    return next((aliases[key] for key in keys if key in aliases), name.strip() or email.strip() or "Unknown")


def classify_language(path: str) -> str:
    """Classify a file from its extension without inspecting its contents."""
    return LANGUAGES.get(Path(path).suffix.lower(), "Other")


def excluded(path: str, config: dict[str, Any]) -> bool:
    """Return whether a configured path exclusion covers a repository path."""
    pieces = Path(path).parts
    return any(part in config["exclude_dirs"] for part in pieces) or Path(path).name in config["exclude_files"]


def parse_numstat(lines: list[str]) -> tuple[int, int, int, list[str]]:
    """Parse Git numstat rows, retaining binary files without fake line counts."""
    added = deleted = binary = 0
    files: list[str] = []
    for line in lines:
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        add, remove, path = parts[0], parts[1], parts[-1]
        files.append(path)
        if add == "-" or remove == "-":
            binary += 1
        else:
            added += int(add)
            deleted += int(remove)
    return added, deleted, binary, files


def analyze_repo(
    name: str, repo: Path, config: dict[str, Any], ref: str = "--all"
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Extract unique commits and changed files from an arbitrary Git repository."""
    if not (repo / ".git").exists():
        raise ValueError(f"Not a Git repository: {repo}")
    fmt = FIELD.join(["%H", "%P", "%an", "%ae", "%cn", "%ce", "%aI", "%cI", "%s", "%D"])
    raw = run_git(repo, "log", ref, "--date=iso-strict", f"--format={RECORD}{fmt}", "--numstat", "-z")
    chunks = [chunk for chunk in raw.split(RECORD) if chunk.strip()]
    commits: list[dict[str, Any]] = []
    files: list[dict[str, Any]] = []
    seen: set[str] = set()
    for chunk in chunks:
        header, *body = chunk.split("\n", 1)
        values = header.split(FIELD)
        if len(values) != 10 or values[0] in seen:
            continue
        seen.add(values[0])
        stat_lines = body[0].replace("\x00", "\n").splitlines() if body else []
        added, deleted, binary, changed = parse_numstat(stat_lines)
        match = CONVENTIONAL.match(values[8])
        author = canonical(values[2], values[3], config["aliases"])
        is_bot = any(token.lower() in f"{values[2]} {values[3]}".lower() for token in config["bot_patterns"])
        item = {
            "repo": name,
            "sha": values[0],
            "parents": values[1].split(),
            "author_name": values[2],
            "author_email": values[3],
            "committer_name": values[4],
            "committer_email": values[5],
            "author_date": pd.Timestamp(values[6]),
            "committer_date": pd.Timestamp(values[7]),
            "message": values[8],
            "refs": values[9],
            "contributor": author,
            "is_bot": is_bot,
            "is_merge": len(values[1].split()) > 1,
            "commit_type": match.group("type").lower() if match else "nonconventional",
            "scope": match.group("scope") if match and match.group("scope") else "",
            "breaking": bool(match and match.group("breaking")),
            "additions": added,
            "deletions": deleted,
            "binary_files": binary,
            "files_changed": len(changed),
        }
        commits.append(item)
        for path in changed:
            if not excluded(path, config):
                files.append(
                    {
                        "repo": name,
                        "sha": values[0],
                        "author_date": values[6],
                        "contributor": author,
                        "path": path,
                        "directory": str(Path(path).parent),
                        "language": classify_language(path),
                        "is_merge": item["is_merge"],
                    }
                )
    refs = run_git(
        repo, "for-each-ref", "--format=%(refname:short)", "refs/heads", "refs/remotes", "refs/tags"
    ).splitlines()
    meta = {
        "name": name,
        "path": str(repo),
        "default_ref": default_ref(repo),
        "refs": refs,
        "is_shallow": run_git(repo, "rev-parse", "--is-shallow-repository").strip() == "true",
        "analyzed_at": datetime.now().astimezone().isoformat(),
    }
    return pd.DataFrame(commits), pd.DataFrame(files), meta


def current_loc(name: str, repo: Path, config: dict[str, Any]) -> pd.DataFrame:
    """Measure readable, tracked source files without modifying the repository."""
    rows: list[dict[str, Any]] = []
    for raw_path in run_git(repo, "ls-files", "-z").split("\0"):
        if not raw_path or excluded(raw_path, config):
            continue
        path = repo / raw_path
        if path.is_symlink():
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        lines = content.splitlines()
        nonempty = [line for line in lines if line.strip()]
        comments = sum(line.strip().startswith(("//", "#", "/*", "*", "--")) for line in nonempty)
        rows.append(
            {
                "repo": name,
                "path": raw_path,
                "directory": str(Path(raw_path).parent),
                "language": classify_language(raw_path),
                "physical_loc": len(lines),
                "nonempty_loc": len(nonempty),
                "blank_loc": len(lines) - len(nonempty),
                "comment_loc": comments,
            }
        )
    return pd.DataFrame(rows)


def save_data(
    output: Path, commits: pd.DataFrame, files: pd.DataFrame, loc: pd.DataFrame, metadata: list[dict[str, Any]]
) -> None:
    """Persist local analysis cache files, including private local metadata."""
    output.mkdir(parents=True, exist_ok=True)
    for label, frame in {"commits": commits, "files": files, "loc": loc}.items():
        frame.to_csv(output / f"{label}.csv", index=False)
    (output / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")


def load_data(output: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, list[dict[str, Any]]]:
    """Load locally cached analysis data and normalize commit timestamps."""
    frames = [pd.read_csv(output / f"{label}.csv") for label in ("commits", "files", "loc")]
    commits = frames[0]
    for column in ("author_date", "committer_date"):
        if column in commits:
            commits[column] = pd.to_datetime(commits[column], utc=True)
    return commits, frames[1], frames[2], json.loads((output / "metadata.json").read_text(encoding="utf-8"))
