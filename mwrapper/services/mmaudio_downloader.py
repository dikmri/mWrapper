from __future__ import annotations

import shutil
import tempfile
import zipfile
from collections.abc import Callable
from pathlib import Path

import requests

from ..constants import MMAUDIO_MAIN_ZIP_URL, MMAUDIO_REPOSITORY_URL
from .mmaudio_demo_patch import patch_mmaudio_demo


LogCallback = Callable[[str], None]


class MMAudioDownloadError(RuntimeError):
    pass


def default_mmaudio_install_dir(tools_dir: Path) -> Path:
    return tools_dir / "MMAudio"


def download_mmaudio_repository(
    tools_dir: Path,
    on_log: LogCallback,
    *,
    zip_url: str = MMAUDIO_MAIN_ZIP_URL,
) -> Path:
    """Download the MMAudio source repository and return its demo.py path."""
    install_dir = default_mmaudio_install_dir(tools_dir)
    demo_path = install_dir / "demo.py"
    if demo_path.exists():
        on_log(f"MMAudio already exists: {install_dir}")
        patch_result = patch_mmaudio_demo(demo_path)
        on_log(patch_result.message)
        return demo_path

    tools_dir.mkdir(parents=True, exist_ok=True)
    on_log(f"Downloading MMAudio from {MMAUDIO_REPOSITORY_URL}")

    with tempfile.TemporaryDirectory(prefix="mwrapper_mmaudio_") as temp_name:
        temp_dir = Path(temp_name)
        zip_path = temp_dir / "mmaudio-main.zip"
        _download_file(zip_url, zip_path, on_log)

        extract_dir = temp_dir / "extract"
        extract_dir.mkdir()
        on_log("Extracting MMAudio archive")
        with zipfile.ZipFile(zip_path) as archive:
            archive.extractall(extract_dir)

        roots = [path for path in extract_dir.iterdir() if path.is_dir()]
        if not roots:
            raise MMAudioDownloadError("Downloaded archive did not contain a repository directory.")
        source_dir = roots[0]
        source_demo = source_dir / "demo.py"
        if not source_demo.exists():
            raise MMAudioDownloadError("Downloaded MMAudio archive does not contain demo.py.")

        if install_dir.exists():
            backup_dir = install_dir.with_name(f"{install_dir.name}.old")
            if backup_dir.exists():
                shutil.rmtree(backup_dir)
            install_dir.replace(backup_dir)

        shutil.move(str(source_dir), str(install_dir))

    on_log(f"MMAudio installed: {install_dir}")
    patch_result = patch_mmaudio_demo(demo_path)
    on_log(patch_result.message)
    return demo_path


def _download_file(url: str, destination: Path, on_log: LogCallback) -> None:
    try:
        with requests.get(url, stream=True, timeout=(10, 60)) as response:
            response.raise_for_status()
            total = int(response.headers.get("content-length") or 0)
            downloaded = 0
            next_report = 0

            with destination.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if not chunk:
                        continue
                    handle.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        percent = int(downloaded * 100 / total)
                        if percent >= next_report:
                            on_log(f"Download progress: {percent}%")
                            next_report += 10
    except requests.RequestException as exc:
        raise MMAudioDownloadError(f"Failed to download MMAudio: {exc}") from exc

    if not destination.exists() or destination.stat().st_size == 0:
        raise MMAudioDownloadError("Downloaded MMAudio archive is empty.")
