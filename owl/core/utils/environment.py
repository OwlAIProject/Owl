"""
Managing configurations using YAML files and environment variables.
"""

import os


def export_config_to_env(config: dict) -> None:
    """
    Export configurations from a dictionary to environment variables.
    """
    for section_key, section in config.items():
        for key, value in section.items():
            name: str = f"OWL_{section_key.upper()}_{key.upper()}"
            if name not in os.environ:
                os.environ[name] = str(value)


def apply_env_overrides(config: dict, prefix: str = "OWL") -> dict:
    """
    Apply environment variable overrides to a configuration dictionary.
    """
    for key, value in config.items():
        if isinstance(value, dict):
            config[key] = apply_env_overrides(value, prefix=f"{prefix}_{key.upper()}")
        else:
            env_key: str = f"{prefix}_{key.upper()}"
            config[key] = os.environ.get(env_key, value)

    return config
