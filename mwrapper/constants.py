from __future__ import annotations

from pathlib import Path

APP_NAME = "mWrapper"
APP_VERSION = "0.1.3"
PACKAGE_DIR = Path(__file__).resolve().parent
APP_ICON_PATH = PACKAGE_DIR / "resources" / "icons" / "icon.png"

SUPPORTED_VIDEO_EXTENSIONS = {
    ".mp4",
    ".mov",
    ".mkv",
    ".webm",
    ".avi",
}

GOOGLE_API_KEY_ENV = "MWRAPPER_GOOGLE_API_KEY"

DEFAULT_MODEL_ID = "nsfw_mmaudio"

MMAUDIO_REPOSITORY_URL = "https://github.com/hkchengrex/MMAudio"
MMAUDIO_MAIN_ZIP_URL = "https://github.com/hkchengrex/MMAudio/archive/refs/heads/main.zip"
