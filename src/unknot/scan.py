import fnmatch
from pathlib import Path, PurePosixPath

from pydantic import BaseModel

from unknot.config import Config
from unknot.tools.git import commit_counts, tracked_files

SOURCE_PATTERNS = ["*.ts", "*.tsx"]
SKIP_PATTERNS = ["*.d.ts", "*.test.ts", "*.test.tsx", "*.spec.ts", "*.spec.tsx"]
CHURN_WINDOW = "12 months ago"


class FileMetrics(BaseModel):
    path: str
    lines: int
    commits: int
    over_threshold: bool


class ScanReport(BaseModel):
    repo: str
    max_file_lines: int
    churn_window: str
    files: list[FileMetrics]


def is_source_file(path: str, test_pattern: str) -> bool:
    name = PurePosixPath(path).name
    patterns = [*SKIP_PATTERNS, test_pattern]
    return not any(fnmatch.fnmatch(name, pattern) for pattern in patterns)


def count_lines(path: Path) -> int:
    with path.open("rb") as handle:
        return sum(1 for _ in handle)


def build_report(config: Config, repo_dir: Path) -> ScanReport:
    paths = [
        path
        for path in tracked_files(repo_dir, SOURCE_PATTERNS)
        if is_source_file(path, config.test_file_pattern)
    ]
    churn = commit_counts(repo_dir, CHURN_WINDOW)

    files: list[FileMetrics] = []
    for path in paths:
        full_path = repo_dir / path
        if not full_path.is_file():  # tracked but deleted in the working tree
            continue
        lines = count_lines(full_path)
        files.append(
            FileMetrics(
                path=path,
                lines=lines,
                commits=churn[path],
                over_threshold=lines > config.max_file_lines,
            )
        )

    files.sort(key=lambda f: (-f.lines, -f.commits, f.path))
    return ScanReport(
        repo=str(repo_dir),
        max_file_lines=config.max_file_lines,
        churn_window=CHURN_WINDOW,
        files=files,
    )
