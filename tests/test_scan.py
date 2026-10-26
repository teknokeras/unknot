import json
import subprocess
from pathlib import Path

from typer.testing import CliRunner

from unknot.cli import app
from unknot.config import Config, save_config
from unknot.scan import build_report, is_source_file

runner = CliRunner()


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=test", "-c", "user.email=test@example.com", *args],
        cwd=repo,
        check=True,
        capture_output=True,
    )


def _make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "target"
    repo.mkdir()
    _git(repo, "init", "-q")
    (repo / "big.ts").write_text("const x = 1;\n" * 350)
    (repo / "small.ts").write_text("const y = 1;\n" * 10)
    (repo / "big.test.ts").write_text("test();\n" * 400)
    (repo / "types.d.ts").write_text("declare const z: number;\n" * 400)
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "first")
    (repo / "big.ts").write_text("const x = 2;\n" * 350)
    _git(repo, "commit", "-q", "-am", "second")
    return repo


def _config(repo: Path) -> Config:
    return Config(repo_path=repo, test_command="exit 0", max_file_lines=300)


def test_is_source_file() -> None:
    assert is_source_file("src/a.ts", "*.test.ts")
    assert not is_source_file("src/a.test.ts", "*.test.ts")
    assert not is_source_file("src/a.spec.ts", "*.test.ts")
    assert not is_source_file("src/a.d.ts", "*.test.ts")


def test_build_report(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)

    report = build_report(_config(repo), repo)

    assert [f.path for f in report.files] == ["big.ts", "small.ts"]
    big, small = report.files
    assert big.lines == 350 and big.over_threshold and big.commits == 2
    assert small.lines == 10 and not small.over_threshold and small.commits == 1


def test_cli_scan_writes_report(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    config_path = tmp_path / "unknot.yaml"
    save_config(_config(repo), config_path)
    output = tmp_path / "report.json"

    result = runner.invoke(app, ["scan", "--config", str(config_path), "--output", str(output)])

    assert result.exit_code == 0
    assert "big.ts" in result.output
    data = json.loads(output.read_text())
    assert data["files"][0]["path"] == "big.ts"
