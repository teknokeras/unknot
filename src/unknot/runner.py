import subprocess
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CommandResult:
    command: str
    returncode: int | None  # None when the command timed out
    output: str
    duration_seconds: float
    timed_out: bool

    @property
    def ok(self) -> bool:
        return self.returncode == 0 and not self.timed_out


def _to_text(data: str | bytes | None) -> str:
    if data is None:
        return ""
    if isinstance(data, bytes):
        return data.decode(errors="replace")
    return data


def run_command(command: str, cwd: Path, timeout_seconds: int) -> CommandResult:
    """Run a shell command and capture its output.

    The command comes from the user's own config file, so it runs through
    the shell. Only use config files you trust.
    """
    start = time.monotonic()
    try:
        completed = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        output = _to_text(exc.stdout) + _to_text(exc.stderr)
        return CommandResult(command, None, output, time.monotonic() - start, True)

    output = completed.stdout + completed.stderr
    return CommandResult(command, completed.returncode, output, time.monotonic() - start, False)
