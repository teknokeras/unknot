import subprocess
from pathlib import Path

from typer.testing import CliRunner

from unknot.check import check_repo, slow_warning
from unknot.cli import app
from unknot.config import Baseline, Config, load_config, save_config

runner = CliRunner()


def make_config(
    repo: Path,
    test_command: str,
    install_command: str | None = None,
    build_command: str | None = None,
    timeout: int = 60,
) -> Config:
    return Config(
        repo_path=repo,
        install_command=install_command,
        build_command=build_command,
        test_command=test_command,
        test_timeout_seconds=timeout,
    )


def test_all_steps_pass(tmp_path: Path) -> None:
    config = make_config(tmp_path, "exit 0", "exit 0", "exit 0")

    report = check_repo(config, tmp_path, fresh=False)

    assert report.passed
    assert [s.name for s in report.steps] == ["install", "build", "test"]
    assert report.test_duration is not None


def test_stops_at_first_failure(tmp_path: Path) -> None:
    config = make_config(tmp_path, "exit 0", install_command="exit 1")

    report = check_repo(config, tmp_path, fresh=False)

    assert not report.passed
    assert [s.name for s in report.steps] == ["install"]


def test_failing_tests_fail_the_check(tmp_path: Path) -> None:
    config = make_config(tmp_path, "exit 1")

    report = check_repo(config, tmp_path, fresh=False)

    assert not report.passed
    assert report.test_duration is None


def test_timeout_is_reported(tmp_path: Path) -> None:
    config = make_config(tmp_path, "exec sleep 5", timeout=1)

    report = check_repo(config, tmp_path, fresh=False)

    assert not report.passed
    assert report.steps[0].result.timed_out


def test_slow_warning() -> None:
    config_dir = Path(".")
    report = check_repo(make_config(config_dir, "sleep 0.1"), config_dir, fresh=False)
    assert slow_warning(report, None) is None
    assert slow_warning(report, Baseline(duration_seconds=0.1)) is None

    # Fake a baseline far below the measured time to trigger the warning.
    from unknot.check import CheckReport, StepResult
    from unknot.runner import CommandResult

    slow = CheckReport([StepResult("test", CommandResult("t", 0, "", 30.0, False))])
    assert slow_warning(slow, Baseline(duration_seconds=5.0)) is not None


def test_cli_record_writes_baseline(tmp_path: Path) -> None:
    config_path = tmp_path / "unknot.yaml"
    save_config(make_config(tmp_path, "exit 0"), config_path)

    result = runner.invoke(app, ["check", "--config", str(config_path), "--record"])

    assert result.exit_code == 0
    assert load_config(config_path).baseline is not None


def test_cli_failure_exit_code(tmp_path: Path) -> None:
    config_path = tmp_path / "unknot.yaml"
    save_config(make_config(tmp_path, "exit 1"), config_path)

    result = runner.invoke(app, ["check", "--config", str(config_path)])

    assert result.exit_code == 1


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=test", "-c", "user.email=test@example.com", *args],
        cwd=repo,
        check=True,
        capture_output=True,
    )


def test_fresh_uses_only_committed_files(tmp_path: Path) -> None:
    repo = tmp_path / "target"
    repo.mkdir()
    _git(repo, "init", "-q")
    (repo / "committed.txt").write_text("x")
    _git(repo, "add", "committed.txt")
    _git(repo, "commit", "-q", "-m", "init")
    (repo / "untracked.txt").write_text("x")  # exists locally, not in git

    present = make_config(repo, "test -f committed.txt")
    missing = make_config(repo, "test -f untracked.txt")

    assert check_repo(present, repo, fresh=True).passed
    assert check_repo(missing, repo, fresh=False).passed
    assert not check_repo(missing, repo, fresh=True).passed
