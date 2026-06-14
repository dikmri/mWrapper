from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import requests


LogCallback = Callable[[str], None]

NSFW_MMAUDIO_MODEL_ID = "nsfw_mmaudio"
MMAUDIO_MODEL_ID = "large_44k_v2"
NSFW_MMAUDIO_FILENAME = "nsfw_gold_8.5k_final.pth"
NSFW_MMAUDIO_URL = (
    "https://huggingface.co/cloud19/NSFW_MMaudio/resolve/main/nsfw_gold_8.5k_final.pth"
)

MODEL_CHOICES = {
    NSFW_MMAUDIO_MODEL_ID: "NSFW_MMaudio",
    MMAUDIO_MODEL_ID: "MMAudio",
}


def nsfw_mmaudio_model_path(mmaudio_dir: Path) -> Path:
    return mmaudio_dir / "weights" / NSFW_MMAUDIO_FILENAME


def normalize_model_id(model_id: str) -> str:
    normalized = model_id.strip()
    aliases = {
        "NSFW_MMaudio": NSFW_MMAUDIO_MODEL_ID,
        "MMAudio": MMAUDIO_MODEL_ID,
        "large_44k_v2": MMAUDIO_MODEL_ID,
        "nsfw_mmaudio": NSFW_MMAUDIO_MODEL_ID,
    }
    return aliases.get(normalized, normalized if normalized in MODEL_CHOICES else NSFW_MMAUDIO_MODEL_ID)


def download_nsfw_mmaudio_model(
    mmaudio_dir: Path,
    on_log: LogCallback,
    *,
    url: str = NSFW_MMAUDIO_URL,
) -> Path:
    destination = nsfw_mmaudio_model_path(mmaudio_dir)
    if destination.exists() and destination.stat().st_size > 0:
        on_log(f"NSFW_MMaudio model already exists: {destination}")
        return destination

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    on_log(f"Downloading NSFW_MMaudio model: {url}")
    try:
        with requests.get(url, stream=True, timeout=(10, 60)) as response:
            response.raise_for_status()
            total = int(response.headers.get("content-length") or 0)
            downloaded = 0
            next_report = 0

            with temporary.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if not chunk:
                        continue
                    handle.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        percent = int(downloaded * 100 / total)
                        if percent >= next_report:
                            on_log(f"NSFW_MMaudio download progress: {percent}%")
                            next_report += 5
    except Exception:
        temporary.unlink(missing_ok=True)
        raise

    if not temporary.exists() or temporary.stat().st_size == 0:
        temporary.unlink(missing_ok=True)
        raise RuntimeError("Downloaded NSFW_MMaudio model is empty.")
    temporary.replace(destination)
    on_log(f"NSFW_MMaudio model installed: {destination}")
    return destination
