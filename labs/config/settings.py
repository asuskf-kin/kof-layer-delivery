# config/settings.py
from pathlib import Path

import yaml

ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT_DIR / "config.yaml"


def load_settings() -> dict:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Configuration file not found at: {CONFIG_PATH}")

    # Explicit utf-8 encoding prevents Windows from using CP1252
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # Resolve using the "data" key as defined in your YAML
    config["data"]["raw_path"] = ROOT_DIR / config["data"]["raw_path"]
    config["data"]["processed_path"] = ROOT_DIR / config["data"]["processed_path"]

    return config


SETTINGS = load_settings()
