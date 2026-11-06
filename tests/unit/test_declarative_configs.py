"""Strict validation for every tracked declarative configuration file.

Coverage: all tracked YAML, JSON, and TOML files regardless of purpose
(spec FR-005 / Clarifications Q1) — CI pipeline definitions, build and
quality-tool configuration, as well as IDE and tool-installed configuration.
Parse must be strict: duplicate mapping keys at any level fail naming the
file and the key, because a duplicate silently overrides its predecessor.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest
import yaml

from tests.unit.support.repo_files import (
    REPO_ROOT,
    inventory_class_files,
    strict_json_loads,
    strict_yaml_load,
)

CONFIG_FILES = inventory_class_files("declarative-configs")

YAML_SUFFIXES = {".yml", ".yaml"}
TOML_NAMES = {".toml"}


def _is_toml(config: Path) -> bool:
    return config.suffix in TOML_NAMES or config.name == "poetry.lock"


def test_declarative_config_files_were_found() -> None:
    """Sanity: the inventory enumerates the declarative config surface, not nothing."""
    assert CONFIG_FILES, "no tracked YAML/JSON/TOML files matched the inventory patterns"


@pytest.mark.parametrize(
    "config",
    CONFIG_FILES,
    ids=lambda c: str(c.relative_to(REPO_ROOT)),
)
def test_tracked_config_is_strictly_valid(config: Path) -> None:
    """Each tracked config parses strictly; duplicate keys are ambiguous and fail."""
    rel = config.relative_to(REPO_ROOT)
    try:
        text = config.read_text(encoding="utf-8")
        if config.suffix in YAML_SUFFIXES:
            strict_yaml_load(text)
        elif config.suffix == ".json":
            strict_json_loads(text)
        elif _is_toml(config):
            tomllib.loads(text)
        else:
            pytest.fail(f"{rel}: not a declarative config extension")
    except (ValueError, yaml.YAMLError, tomllib.TOMLDecodeError, UnicodeDecodeError) as exc:
        pytest.fail(f"{rel} is not strictly valid: {exc}")
