from pathlib import Path
from typing import Annotated

import typer

from unknot.check import CheckError, CheckReport, check_repo, slow_warning
from unknot.config import (
    Baseline,
    Config,
    ConfigError,
    default_config,
    load_config,
    save_config,
)
from unknot.scan import ScanReport, build_report
from unknot.tools.git import GitError

app = typer.Typer(
    help="Split large source files into small, tested modules.",
    no_args_is_help=True,
)


@app.command()
def init(
    path: Annotated[Path, typer.Option(help="Where to write the config file.")] = Path(
        "unknot.yaml"
    ),
    force: Annotated[bool, typer.Option("--force", help="Overwrite an existing file.")] = False,
) -> None:
    """Create the Phase 0 config file."""
    if path.exists() and not force:
        typer.echo(f"{path} already exists. Use --force to overwrite.", err=True)
        raise typer.Exit(code=1)
    save_config(default_config(), path)
    typer.echo(f"Wrote {path}. Edit it for your target repo, then run: unknot check")


def _print_report(report: CheckReport) -> None:
    for step in report.steps:
        result = step.result
        if result.ok:
            typer.echo(f"PASS  {step.name}  ({result.duration_seconds:.1f}s)")
        elif result.timed_out:
            typer.echo(f"FAIL  {step.name}  (timed out after {result.duration_seconds:.0f}s)")
        else:
            typer.echo(f"FAIL  {step.name}  (exit code {result.returncode})")
            tail = "\n".join(result.output.strip().splitlines()[-20:])
            if tail:
                typer.echo(tail)


def _load_target(config_path: Path) -> tuple[Config, Path]:
    try:
        config = load_config(config_path)
    except ConfigError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=2) from exc

    repo_dir = (config_path.parent / config.repo_path).resolve()
    if not repo_dir.is_dir():
        typer.echo(f"Target repo not found: {repo_dir}", err=True)
        raise typer.Exit(code=2)
    return config, repo_dir


@app.command()
def check(
    config_path: Annotated[Path, typer.Option("--config", help="Path to the config file.")] = Path(
        "unknot.yaml"
    ),
    fresh: Annotated[
        bool,
        typer.Option("--fresh", help="Clone the repo to a temp folder first."),
    ] = False,
    record: Annotated[
        bool,
        typer.Option("--record", help="Save this run as the baseline if it passes."),
    ] = False,
) -> None:
    """Verify the repo builds and tests pass, and compare with the baseline."""
    config, repo_dir = _load_target(config_path)

    try:
        report = check_repo(config, repo_dir, fresh=fresh)
    except CheckError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=2) from exc

    _print_report(report)
    if not report.passed:
        raise typer.Exit(code=1)

    warning = slow_warning(report, config.baseline)
    if warning:
        typer.echo(f"WARNING  {warning}")

    duration = report.test_duration
    if record and duration is not None:
        config.baseline = Baseline(duration_seconds=duration)
        save_config(config, config_path)
        typer.echo(f"Baseline recorded in {config_path}")
    elif config.baseline is None:
        typer.echo("No baseline yet. Run again with --record to save one.")

    typer.echo("Check passed.")


def _print_scan_summary(report: ScanReport, top: int) -> None:
    over = [f for f in report.files if f.over_threshold]
    typer.echo(f"{len(report.files)} source files, {len(over)} over {report.max_file_lines} lines")
    if not over:
        return
    typer.echo(f"\n{'LINES':>6}  {'COMMITS':>7}  PATH  (commits: {report.churn_window})")
    for item in over[:top]:
        typer.echo(f"{item.lines:>6}  {item.commits:>7}  {item.path}")


@app.command()
def scan(
    config_path: Annotated[Path, typer.Option("--config", help="Path to the config file.")] = Path(
        "unknot.yaml"
    ),
    output: Annotated[Path, typer.Option(help="Where to write the JSON report.")] = Path(
        "unknot-report.json"
    ),
    top: Annotated[int, typer.Option(help="How many files to show.")] = 20,
) -> None:
    """Produce a ranked report of files worth refactoring."""
    config, repo_dir = _load_target(config_path)

    try:
        report = build_report(config, repo_dir)
    except GitError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=2) from exc

    output.write_text(report.model_dump_json(indent=2))
    _print_scan_summary(report, top)
    typer.echo(f"\nFull report written to {output}")


@app.command()
def run(file: str) -> None:
    """Pin, plan, split and verify one file."""
    typer.echo(f"run: not implemented yet ({file})")
