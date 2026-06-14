from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import requests

from ..constants import APP_VERSION
from .subprocess_utils import hidden_subprocess_kwargs


GITHUB_REPOSITORY = "dikmri/mWrapper"
LATEST_RELEASE_API_URL = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/releases/latest"
INSTALLER_USER_AGENT = "mWrapper-updater"
WINDOWS_ASSET_RE = re.compile(r"^mWrapper-v?[0-9][^-]*-windows\.zip$", re.IGNORECASE)

ProgressCallback = Callable[[int, int], None]


@dataclass(frozen=True, slots=True)
class ReleaseAsset:
    name: str
    download_url: str
    size: int


@dataclass(frozen=True, slots=True)
class UpdateInfo:
    tag_name: str
    version: str
    asset: ReleaseAsset


def auto_update_enabled() -> bool:
    return os.environ.get("MWRAPPER_DISABLE_AUTO_UPDATE") != "1"


def is_frozen_app() -> bool:
    return bool(getattr(sys, "frozen", False))


def current_install_dir() -> Path:
    return Path(sys.executable).resolve().parent


def current_exe_name() -> str:
    return Path(sys.executable).name


def parse_version(value: str) -> tuple[int, ...]:
    normalized = value.strip()
    if normalized.startswith(("v", "V")):
        normalized = normalized[1:]
    parts = re.findall(r"\d+", normalized)
    return tuple(int(part) for part in parts)


def is_newer_version(candidate: str, current: str = APP_VERSION) -> bool:
    candidate_parts = parse_version(candidate)
    current_parts = parse_version(current)
    length = max(len(candidate_parts), len(current_parts))
    candidate_parts += (0,) * (length - len(candidate_parts))
    current_parts += (0,) * (length - len(current_parts))
    return candidate_parts > current_parts


def fetch_latest_update_info(
    current_version: str = APP_VERSION,
    *,
    timeout_seconds: int = 5,
) -> UpdateInfo | None:
    response = requests.get(
        LATEST_RELEASE_API_URL,
        headers={"User-Agent": INSTALLER_USER_AGENT},
        timeout=(3, timeout_seconds),
    )
    response.raise_for_status()
    data = response.json()
    tag_name = str(data.get("tag_name") or "")
    if not tag_name or not is_newer_version(tag_name, current_version):
        return None

    asset = _select_windows_asset(data.get("assets") or [])
    if asset is None:
        return None

    return UpdateInfo(
        tag_name=tag_name,
        version=tag_name.lstrip("vV"),
        asset=asset,
    )


def download_update_asset(
    update: UpdateInfo,
    destination: Path,
    on_progress: ProgressCallback,
) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    try:
        with requests.get(
            update.asset.download_url,
            stream=True,
            headers={"User-Agent": INSTALLER_USER_AGENT},
            timeout=(10, 60),
        ) as response:
            response.raise_for_status()
            total = int(response.headers.get("content-length") or update.asset.size or 0)
            downloaded = 0
            with temporary.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if not chunk:
                        continue
                    handle.write(chunk)
                    downloaded += len(chunk)
                    on_progress(downloaded, total)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise

    if not temporary.exists() or temporary.stat().st_size == 0:
        temporary.unlink(missing_ok=True)
        raise RuntimeError("Downloaded update archive is empty.")
    temporary.replace(destination)


def launch_update_replacer(
    *,
    zip_path: Path,
    install_dir: Path,
    exe_name: str,
    wait_pid: int,
    temp_root: Path,
) -> None:
    temp_root.mkdir(parents=True, exist_ok=True)
    script_path = temp_root / "apply_update.ps1"
    log_path = install_dir / "update.log"
    script_path.write_text(_updater_script(), encoding="utf-8")

    command = [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script_path),
        "-WaitPid",
        str(wait_pid),
        "-ZipPath",
        str(zip_path),
        "-InstallDir",
        str(install_dir),
        "-ExeName",
        exe_name,
        "-TempRoot",
        str(temp_root),
        "-LogPath",
        str(log_path),
    ]
    subprocess.Popen(
        command,
        cwd=str(temp_root),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        shell=False,
        **hidden_subprocess_kwargs(),
    )


def make_update_temp_dir() -> Path:
    return Path(tempfile.mkdtemp(prefix="mwrapper-update-"))


def _select_windows_asset(assets: list[dict]) -> ReleaseAsset | None:
    for asset in assets:
        name = str(asset.get("name") or "")
        download_url = str(asset.get("browser_download_url") or "")
        if WINDOWS_ASSET_RE.match(name) and download_url:
            return ReleaseAsset(
                name=name,
                download_url=download_url,
                size=int(asset.get("size") or 0),
            )
    return None


def _updater_script() -> str:
    return r'''
param(
    [int]$WaitPid,
    [string]$ZipPath,
    [string]$InstallDir,
    [string]$ExeName,
    [string]$TempRoot,
    [string]$LogPath
)

$ErrorActionPreference = "Stop"

function Ensure-Directory {
    param([string]$Path)
    if ([string]::IsNullOrWhiteSpace($Path)) {
        return
    }
    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Force -LiteralPath $Path | Out-Null
    }
}

function Write-UpdateLog {
    param([string]$Message)
    try {
        Ensure-Directory (Split-Path -Parent $LogPath)
        $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        Add-Content -LiteralPath $LogPath -Value "[$timestamp] $Message" -Encoding UTF8
    }
    catch {
    }
}

try {
    Ensure-Directory $TempRoot
    Set-Location -LiteralPath $TempRoot
    Ensure-Directory $InstallDir

    Write-UpdateLog "Waiting for process $WaitPid to exit."
    $process = Get-Process -Id $WaitPid -ErrorAction SilentlyContinue
    if ($process) {
        Wait-Process -Id $WaitPid -Timeout 180 -ErrorAction SilentlyContinue
    }
    Start-Sleep -Milliseconds 700

    $extractPath = Join-Path $TempRoot "extract"
    if (Test-Path -LiteralPath $extractPath) {
        Remove-Item -LiteralPath $extractPath -Recurse -Force
    }
    New-Item -ItemType Directory -Force -Path $extractPath | Out-Null
    Write-UpdateLog "Extracting $ZipPath"
    Expand-Archive -LiteralPath $ZipPath -DestinationPath $extractPath -Force

    $sourceExe = Get-ChildItem -LiteralPath $extractPath -Recurse -Filter $ExeName | Select-Object -First 1
    if (-not $sourceExe) {
        throw "$ExeName was not found in update archive."
    }
    $sourceDir = $sourceExe.Directory.FullName
    $backupPath = Join-Path $TempRoot "backup"
    if (Test-Path -LiteralPath $backupPath) {
        Remove-Item -LiteralPath $backupPath -Recurse -Force
    }
    New-Item -ItemType Directory -Force -Path $backupPath | Out-Null
    $sourceItems = @(Get-ChildItem -LiteralPath $sourceDir)

    Write-UpdateLog "Replacing app files in $InstallDir"

    try {
        foreach ($item in $sourceItems) {
            $destination = Join-Path $InstallDir $item.Name
            if (Test-Path -LiteralPath $destination) {
                Move-Item -LiteralPath $destination -Destination (Join-Path $backupPath $item.Name) -Force
            }
        }

        foreach ($item in $sourceItems) {
            Copy-Item -LiteralPath $item.FullName -Destination $InstallDir -Recurse -Force
        }

        $installedExe = Join-Path $InstallDir $ExeName
        if (-not (Test-Path -LiteralPath $installedExe)) {
            throw "$ExeName was not copied to $InstallDir."
        }

        Write-UpdateLog "Starting updated app: $installedExe"
        Start-Process -FilePath $installedExe -WorkingDirectory $InstallDir
        if (Test-Path -LiteralPath $backupPath) {
            Remove-Item -LiteralPath $backupPath -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
    catch {
        Write-UpdateLog "Update failed during replace: $_"
        foreach ($item in $sourceItems) {
            $destination = Join-Path $InstallDir $item.Name
            if (Test-Path -LiteralPath $destination) {
                Remove-Item -LiteralPath $destination -Recurse -Force -ErrorAction SilentlyContinue
            }
        }
        if (Test-Path -LiteralPath $backupPath) {
            foreach ($backupItem in Get-ChildItem -LiteralPath $backupPath) {
                Move-Item -LiteralPath $backupItem.FullName -Destination $InstallDir -Force
            }
        }
        $oldExe = Join-Path $InstallDir $ExeName
        if (Test-Path -LiteralPath $oldExe) {
            Start-Process -FilePath $oldExe -WorkingDirectory $InstallDir
        }
        throw
    }
}
catch {
    Write-UpdateLog "Update failed: $_"
}
finally {
    if (Test-Path -LiteralPath $TempRoot) {
        Remove-Item -LiteralPath $TempRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
}
'''
