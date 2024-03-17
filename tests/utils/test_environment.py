# pylint: disable=C0116
"""
Tests for environment variable overrides.
"""
import os
from typing import Any

import pytest

from owl.core.utils.environment import apply_env_overrides, export_config_to_env

CONFIG_FILE = ".config/sample-config.yaml"
ENV_FILE = ".config/sample-env.env"


@pytest.fixture
def sample_config() -> dict[str, Any]:
    return {"web": {"base_url": "http://localhost", "port": "3000"}}


def test_export_config_to_env(sample_config) -> None:
    export_config_to_env(sample_config)
    assert os.environ["OWL_WEB_BASE_URL"] == "http://localhost"
    assert os.environ["OWL_WEB_PORT"] == "3000"


def test_apply_env_overrides(sample_config) -> None:
    os.environ["OWL_WEB_PORT"] = "4000"
    config: dict[Any, Any] = apply_env_overrides(sample_config)
    assert config["web"]["port"] == "4000"
