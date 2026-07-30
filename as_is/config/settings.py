from pathlib import Path

import yaml

# Resolves the path relative to this file's location
ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT_DIR / "config.yaml"


def load_settings() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)


SETTINGS = load_settings()

# Acceso directo a las configuraciones desde SETTINGS
raw_directory = SETTINGS["paths"]["raw_dir"]
processed_directory = SETTINGS["paths"]["processed_dir"]
required_columns = SETTINGS["required_columns"]
percentage_columns = SETTINGS["columns"]["pct_cols"]
