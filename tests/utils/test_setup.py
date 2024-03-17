# pylint: disable=C0116,w0613
"""
Tests for the `owl setup` command and utility functions.
"""
from pathlib import Path
from typing import Any
from unittest.mock import patch

from ruamel.yaml import YAML

from owl.core.utils.setup import setup_config, setup_env, update_yaml

USER_NAME = "Owl"
CLIENT_TOKEN = "qkirJuCHF9lKK1DvwZ2LmYSPTTFe9rR5mmJU6kp5o2M"
YAML_DATA: dict[str, Any] = {
    "user.name": USER_NAME,
    "user.client_token": CLIENT_TOKEN,
}


def test_update_yaml(tmpdir) -> None:
    file_path = Path(tmpdir.join("config.yaml"))
    initial_content: dict[str, Any] = {"user": {"name": "", "client_token": ""}}
    yaml = YAML()
    with file_path.open("w", encoding="utf-8") as f:
        yaml.dump(initial_content, f)

    update_yaml(file_path, YAML_DATA)
    with file_path.open("r", encoding="utf-8") as f:
        content: Any = yaml.load(f)

    assert content["user"]["name"] == USER_NAME
    assert content["user"]["client_token"] == CLIENT_TOKEN


@patch("owl.core.utils.setup.update_yaml")
@patch("pathlib.Path.exists")
@patch("shutil.copy")
def test_setup_config_no_exist(
    mock_copy, mock_exists, mock_update_yaml, tmpdir, mocker
) -> None:
    mock_console: Any = mocker.Mock()
    mock_exists.return_value = False
    origin_path = Path(".config/sample-config.yaml")
    dest_path: Path = Path(tmpdir) / "config.yaml"
    setup_config(mock_console, YAML_DATA, origin_path=origin_path, dest_path=dest_path)
    mock_copy.assert_called_once_with(origin_path, dest_path)
    mock_update_yaml.assert_called_once_with(dest_path, YAML_DATA)
    mock_console.print.assert_called_with(
        f"- Created '{dest_path}' from '{origin_path}'.", style="green"
    )


@patch("owl.core.utils.setup.update_yaml")
@patch("pathlib.Path.exists")
@patch("shutil.copy")
def test_setup_config_exists(
    mock_copy, mock_exists, mock_update_yaml, tmpdir, mocker
) -> None:
    mock_console: Any = mocker.Mock()
    mock_exists.return_value = True
    dest_path: Path = Path(tmpdir) / "config.yaml"
    setup_config(mock_console, YAML_DATA, dest_path=dest_path)
    mock_copy.assert_not_called()
    mock_update_yaml.assert_not_called()
    mock_console.print.assert_called_with(
        f"- File '{dest_path}' already exists. Skipping.",
        style="yellow",
    )


def test_setup_env_no_exist(tmpdir, mocker) -> None:
    mock_console: Any = mocker.Mock()
    dest = Path(tmpdir)
    setup_env(mock_console, CLIENT_TOKEN, path=dest)
    env_file: Path = dest / ".env"
    assert env_file.exists()
    with env_file.open("r", encoding="utf-8") as file:
        content: str = file.read()
        assert f"OWL_USER_CLIENT_TOKEN={CLIENT_TOKEN}\n" in content

    mock_console.print.assert_called_with(
        "- Created '.env' file with 'OWL_USER_CLIENT_TOKEN'.", style="green"
    )
