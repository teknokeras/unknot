from pathlib import Path
from typing import Annotated

import typer

from unknot.check import CheckError, CheckReport, check_repo, slow_warning
from unknot.config import (
    Baseline,
    ConfigError,
    default_config,
    load_config,
    save_config,
)

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
    try:
        config = load_config(config_path)
    except ConfigError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=2) from exc

    repo_dir = (config_path.parent / config.repo_path).resolve()
    if not repo_dir.is_dir():
        typer.echo(f"Target repo not found: {repo_dir}", err=True)
        raise typer.Exit(code=2)

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


@app.command()
def scan() -> None:
    """Produce a ranked report of files worth refactoring."""
    typer.echo("scan: not implemented yet")


@app.command()
def run(file: str) -> None:
    """Pin, plan, split and verify one file."""
    typer.echo(f"run: not implemented yet ({file})")
