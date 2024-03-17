# pylint: disable=C0116
"""
Tests for environment variable overrides.
"""

import pytest
from dotenv import load_dotenv

from owl.core.config import Configuration

CONFIG_FILE = ".config/sample-config.yaml"
ENV_FILE = ".config/sample-env.env"


@pytest.fixture
def load_sample_env(monkeypatch) -> None:
    load_dotenv(ENV_FILE)
    monkeypatch.setenv("OWL_USER_NAME", "Owl")
    monkeypatch.setenv("OWL_USER_CLIENT_TOKEN", "<client-token>")


@pytest.mark.usefixtures("load_sample_env")
def test_user_config_overrides() -> None:
    config: Configuration = Configuration.load_config_yaml(CONFIG_FILE)
    assert config.user.name == "Owl"
    assert config.user.client_token == "<client-token>"
