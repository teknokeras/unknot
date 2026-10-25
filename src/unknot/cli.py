from pathlib import Path
from typing import Annotated

import typer

from unknot.config import default_config, save_config

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


@app.command()
def check() -> None:
    """Verify the repo builds and tests pass against the recorded baseline."""
    typer.echo("check: not implemented yet")


@app.command()
def scan() -> None:
    """Produce a ranked report of files worth refactoring."""
    typer.echo("scan: not implemented yet")


@app.command()
def run(file: str) -> None:
    """Pin, plan, split and verify one file."""
    typer.echo(f"run: not implemented yet ({file})")
