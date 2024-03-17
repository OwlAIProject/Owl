"""
Utility functions for the `owl setup` command.
"""

import shutil
from pathlib import Path
from typing import Any

from rich.console import Console
from ruamel.yaml import YAML


def update_yaml(path: Path, data: dict[str, Any]) -> None:
    """
    Update the YAML file with the user's name and client token.
    """
    yaml = YAML()
    yaml.preserve_quotes = True
    with path.open("r", encoding="utf-8") as file:
        config: Any = yaml.load(file)

    for key_path, value in data.items():
        keys: list[str] = key_path.split(".")
        sub_config: Any = config

        for key in keys[:-1]:
            if key not in sub_config:
                sub_config[key] = {}

            sub_config = sub_config[key]
        sub_config[keys[-1]] = value

    with path.open("w", encoding="utf-8") as file:
        yaml.dump(config, file)


def setup_config(
    console: Console,
    data: dict[str, Any],
    origin_path: Path = Path(".config/sample-config.yaml"),
    dest_path: Path = Path("config.yaml"),
) -> None:
    """
    Create or update the config.yaml file.
    """
    if not dest_path.exists():
        shutil.copy(origin_path, dest_path)
        update_yaml(dest_path, data)
        console.print(f"- Created '{dest_path}' from '{origin_path}'.", style="green")
    else:
        console.print(
            f"- File '{dest_path}' already exists. Skipping.",
            style="yellow",
        )


def setup_env(console: Console, client_token: str, path: Path = Path(".")) -> None:
    """
    Create a .env file with the user's client token.
    """
    dest: Path = path / ".env"

    if dest.exists():
        console.print("- File '.env' already exists. Skipping.", style="yellow")
    else:
        with dest.open("w", encoding="utf-8") as file:
            file.write(f"OWL_USER_CLIENT_TOKEN={client_token}\n")
        console.print(
            "- Created '.env' file with 'OWL_USER_CLIENT_TOKEN'.", style="green"
        )
