from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError


class ConfigError(Exception):
    """Raised when the config file is missing or invalid."""


class Baseline(BaseModel):
    """Recorded result of the target repo's test run on untouched code."""

    model_config = ConfigDict(extra="forbid")

    passed_tests: int = Field(ge=0)
    duration_seconds: float = Field(ge=0)
    flaky_tests: list[str] = Field(default_factory=list)


class Config(BaseModel):
    """Phase 0 settings: what a human records about the target repo."""

    model_config = ConfigDict(extra="forbid")

    language: Literal["typescript"] = "typescript"
    framework: str | None = None
    repo_path: Path
    install_command: str | None = None
    build_command: str | None = None
    test_command: str
    coverage_command: str | None = None
    test_timeout_seconds: int = Field(default=600, gt=0)
    max_file_lines: int = Field(default=300, gt=0)
    test_file_pattern: str = "*.test.ts"
    test_location: Literal["beside_source", "tests_dir"] = "beside_source"
    baseline: Baseline | None = None


def default_config() -> Config:
    return Config(
        repo_path=Path("../my-typescript-repo"),
        install_command="npm ci",
        build_command="npx tsc --noEmit",
        test_command="npm test",
    )


def _format_errors(err: ValidationError) -> str:
    lines = []
    for item in err.errors():
        location = ".".join(str(part) for part in item["loc"])
        lines.append(f"  {location}: {item['msg']}")
    return "\n".join(lines)


def load_config(path: Path) -> Config:
    try:
        raw = yaml.safe_load(path.read_text())
    except FileNotFoundError as exc:
        raise ConfigError(f"Config file not found: {path}") from exc
    except yaml.YAMLError as exc:
        raise ConfigError(f"Invalid YAML in {path}: {exc}") from exc

    if not isinstance(raw, dict):
        raise ConfigError(f"{path} must contain a mapping of settings.")

    try:
        return Config.model_validate(raw)
    except ValidationError as exc:
        raise ConfigError(f"Invalid config in {path}:\n{_format_errors(exc)}") from exc


def save_config(config: Config, path: Path) -> None:
    data = config.model_dump(mode="json")
    path.write_text(yaml.safe_dump(data, sort_keys=False))
