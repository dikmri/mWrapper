from __future__ import annotations

import os
from pathlib import Path

from ..constants import APP_NAME


def appdata_dir() -> Path:
    base = os.environ.get("APPDATA")
    if base:
        return Path(base) / APP_NAME
    return Path.home() / ".config" / APP_NAME


def local_appdata_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    if base:
        return Path(base) / APP_NAME
    return Path.home() / ".local" / "share" / APP_NAME


def default_output_dir() -> Path:
    return Path.home() / "Videos" / APP_NAME / "outputs"


def default_temp_dir() -> Path:
    return local_appdata_dir() / "temp"


def default_models_dir() -> Path:
    return local_appdata_dir() / "models"


def default_tools_dir() -> Path:
    return local_appdata_dir() / "tools"


def default_venvs_dir() -> Path:
    return local_appdata_dir() / "venvs"


def default_logs_dir() -> Path:
    return local_appdata_dir() / "logs"


def config_path() -> Path:
    return appdata_dir() / "config.json"


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path
