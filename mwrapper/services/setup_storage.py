from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from .mmaudio_downloader import default_mmaudio_install_dir
from .model_assets import nsfw_mmaudio_model_path


GIB = 1024**3
MMAUDIO_SOURCE_ESTIMATE_BYTES = int(0.5 * GIB)
MMAUDIO_VENV_ESTIMATE_BYTES = int(8.0 * GIB)
NSFW_MODEL_ESTIMATE_BYTES = int(4.5 * GIB)
RUNTIME_CACHE_ESTIMATE_BYTES = int(6.0 * GIB)
SETUP_WORKING_MARGIN_BYTES = int(4.0 * GIB)


@dataclass(frozen=True, slots=True)
class SetupPaths:
    root: Path
    tools_dir: Path
    temp_dir: Path
    models_dir: Path
    logs_dir: Path
    venvs_dir: Path


@dataclass(frozen=True, slots=True)
class SetupReadiness:
    demo_ready: bool
    venv_ready: bool
    nsfw_ready: bool

    @property
    def ready(self) -> bool:
        return self.demo_ready and self.venv_ready and self.nsfw_ready


def setup_paths_for_root(root: Path) -> SetupPaths:
    resolved = root.expanduser()
    return SetupPaths(
        root=resolved,
        tools_dir=resolved / "tools",
        temp_dir=resolved / "temp",
        models_dir=resolved / "models",
        logs_dir=resolved / "logs",
        venvs_dir=resolved / "venvs",
    )


def inspect_setup_readiness(paths: SetupPaths) -> SetupReadiness:
    install_dir = default_mmaudio_install_dir(paths.tools_dir)
    demo_path = install_dir / "demo.py"
    venv_python = paths.venvs_dir / "mmaudio" / "Scripts" / "python.exe"
    nsfw_weights = nsfw_mmaudio_model_path(install_dir)
    return SetupReadiness(
        demo_ready=demo_path.exists(),
        venv_ready=venv_python.exists(),
        nsfw_ready=nsfw_weights.exists() and nsfw_weights.stat().st_size > 0,
    )


def estimate_required_setup_bytes(readiness: SetupReadiness) -> int:
    if readiness.ready:
        return 0

    total = SETUP_WORKING_MARGIN_BYTES
    if not readiness.demo_ready:
        total += MMAUDIO_SOURCE_ESTIMATE_BYTES
    if not readiness.venv_ready:
        total += MMAUDIO_VENV_ESTIMATE_BYTES
    if not readiness.nsfw_ready:
        total += NSFW_MODEL_ESTIMATE_BYTES
    total += RUNTIME_CACHE_ESTIMATE_BYTES
    return total


def free_bytes_for_path(path: Path) -> int:
    candidate = path
    while not candidate.exists() and candidate.parent != candidate:
        candidate = candidate.parent
    usage = shutil.disk_usage(candidate)
    return int(usage.free)


def format_bytes(value: int) -> str:
    if value >= GIB:
        return f"{value / GIB:.1f} GB"
    return f"{value / (1024**2):.0f} MB"
