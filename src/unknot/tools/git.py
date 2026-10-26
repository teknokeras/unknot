import subprocess
from collections import Counter
from pathlib import Path


class GitError(Exception):
    """Raised when a git command fails or git is not available."""


def _git(repo_dir: Path, *args: str) -> str:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise GitError("git is not installed or not on PATH") from exc
    if completed.returncode != 0:
        raise GitError(f"git {' '.join(args)} failed: {completed.stderr.strip()}")
    return completed.stdout


def tracked_files(repo_dir: Path, patterns: list[str]) -> list[str]:
    """Paths (relative to the repo) of tracked files matching the patterns."""
    output = _git(repo_dir, "ls-files", "-z", "--", *patterns)
    return [path for path in output.split("\0") if path]


def commit_counts(repo_dir: Path, since: str) -> Counter[str]:
    """How many commits touched each file since the given date expression."""
    output = _git(
        repo_dir,
        "-c",
        "core.quotepath=off",
        "log",
        f"--since={since}",
        "--name-only",
        "--pretty=format:",
    )
    return Counter(line for line in output.splitlines() if line)
