import typer

app = typer.Typer(
    help="Split large source files into small, tested modules.",
    no_args_is_help=True,
)


@app.command()
def init() -> None:
    """Create the Phase 0 config file."""
    typer.echo("init: not implemented yet")


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