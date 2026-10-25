import shlex
import tempfile
from dataclasses import dataclass
from pathlib import Path

from unknot.config import Baseline, Config
from unknot.runner import CommandResult, run_command


class CheckError(Exception):
    """Raised when the check cannot run at all (for example, git clone fails)."""


@dataclass(frozen=True)
class StepResult:
    name: str
    result: CommandResult


@dataclass(frozen=True)
class CheckReport:
    steps: list[StepResult]

    @property
    def passed(self) -> bool:
        return all(step.result.ok for step in self.steps)

    @property
    def test_duration(self) -> float | None:
        for step in self.steps:
            if step.name == "test" and step.result.ok:
                return step.result.duration_seconds
        return None


def _run_steps(config: Config, cwd: Path) -> CheckReport:
    plan = [
        ("install", config.install_command),
        ("build", config.build_command),
        ("test", config.test_command),
    ]
    steps: list[StepResult] = []
    for name, command in plan:
        if command is None:
            continue
        result = run_command(command, cwd, config.test_timeout_seconds)
        steps.append(StepResult(name, result))
        if not result.ok:
            break
    return CheckReport(steps)


def check_repo(config: Config, repo_dir: Path, fresh: bool) -> CheckReport:
    if not fresh:
        return _run_steps(config, repo_dir)

    with tempfile.TemporaryDirectory(prefix="unknot-") as tmp:
        target = Path(tmp) / "checkout"
        clone = run_command(
            f"git clone --quiet {shlex.quote(str(repo_dir))} {shlex.quote(str(target))}",
            cwd=Path(tmp),
            timeout_seconds=300,
        )
        if not clone.ok:
            raise CheckError(f"git clone failed:\n{clone.output}")
        return _run_steps(config, target)


def slow_warning(report: CheckReport, baseline: Baseline | None, factor: float = 2.0) -> str | None:
    """Warn when tests take much longer than the recorded baseline."""
    duration = report.test_duration
    if baseline is None or duration is None:
        return None
    base = baseline.duration_seconds
    if duration > base * factor and duration - base > 5:
        return f"Tests took {duration:.1f}s, more than {factor:g}x the baseline of {base:.1f}s."
    return None
