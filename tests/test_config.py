from pathlib import Path

import pytest
from typer.testing import CliRunner

from unknot.cli import app
from unknot.config import ConfigError, default_config, load_config, save_config

runner = CliRunner()


def test_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "unknot.yaml"
    config = default_config()

    save_config(config, path)

    assert load_config(path) == config


def test_missing_test_command_is_reported(tmp_path: Path) -> None:
    path = tmp_path / "unknot.yaml"
    path.write_text("repo_path: ./x\n")

    with pytest.raises(ConfigError, match="test_command"):
        load_config(path)


def test_unknown_key_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "unknot.yaml"
    path.write_text("repo_path: ./x\ntest_command: npm test\nbanana: 1\n")

    with pytest.raises(ConfigError, match="banana"):
        load_config(path)


def test_missing_file_is_reported(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="not found"):
        load_config(tmp_path / "nope.yaml")


def test_init_writes_a_loadable_file(tmp_path: Path) -> None:
    path = tmp_path / "unknot.yaml"

    result = runner.invoke(app, ["init", "--path", str(path)])

    assert result.exit_code == 0
    assert load_config(path) == default_config()


def test_init_refuses_to_overwrite(tmp_path: Path) -> None:
    path = tmp_path / "unknot.yaml"
    path.write_text("keep me")

    result = runner.invoke(app, ["init", "--path", str(path)])

    assert result.exit_code == 1
    assert path.read_text() == "keep me"
