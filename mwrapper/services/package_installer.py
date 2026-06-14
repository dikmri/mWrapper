from __future__ import annotations

import shutil
import os
from dataclasses import dataclass
from pathlib import Path

from .hardware import HardwareInfo


PYTORCH_CUDA_LABEL = "CUDA 12.8"
PYTORCH_CUDA_INDEX_URL = "https://download.pytorch.org/whl/cu128"
PYTORCH_CPU_LABEL = "CPU"
PYTORCH_CPU_INDEX_URL = "https://download.pytorch.org/whl/cpu"
MMAUDIO_NUMPY_SPEC = "numpy<2.1,>=1.21"
MMAUDIO_SOUNDFILE_SPEC = "soundfile>=0.12"
UV_BOOTSTRAP_VENV_NAME = "_uv"


@dataclass(frozen=True, slots=True)
class PyTorchInstallSpec:
    label: str
    index_url: str
    requires_cuda: bool = True


def select_pytorch_install_spec(hardware: HardwareInfo | None = None) -> PyTorchInstallSpec:
    if hardware is not None and not hardware.has_nvidia_gpu:
        return PyTorchInstallSpec(PYTORCH_CPU_LABEL, PYTORCH_CPU_INDEX_URL, requires_cuda=False)
    return PyTorchInstallSpec(PYTORCH_CUDA_LABEL, PYTORCH_CUDA_INDEX_URL, requires_cuda=True)


def uv_bootstrap_venv_dir(venvs_dir: Path) -> Path:
    return venvs_dir / UV_BOOTSTRAP_VENV_NAME


def uv_executable_for_venvs_dir(venvs_dir: Path) -> Path:
    uv_venv = uv_bootstrap_venv_dir(venvs_dir)
    if _is_windows_path():
        return uv_venv / "Scripts" / "uv.exe"
    return uv_venv / "bin" / "uv"


def find_uv(venvs_dir: Path | None = None) -> str | None:
    if venvs_dir is not None:
        local_uv = uv_executable_for_venvs_dir(venvs_dir)
        if local_uv.exists():
            return str(local_uv)
    return shutil.which("uv")


def build_uv_bootstrap_commands(base_python: Path, venvs_dir: Path) -> list[tuple[list[str], Path | None]]:
    uv_venv = uv_bootstrap_venv_dir(venvs_dir)
    uv_python = uv_venv / "Scripts" / "python.exe" if _is_windows_path() else uv_venv / "bin" / "python"
    return [
        ([str(base_python), "-m", "venv", "--clear", str(uv_venv)], None),
        ([str(uv_python), "-m", "ensurepip", "--upgrade"], None),
        (
            [
                str(uv_python),
                "-m",
                "pip",
                "install",
                "--no-cache-dir",
                "--upgrade",
                "pip",
                "uv",
            ],
            None,
        ),
    ]


def build_mmaudio_venv_commands(
    *,
    uv_path: str,
    base_python: Path,
    venv_dir: Path,
    venv_python: Path,
    mmaudio_dir: Path,
    pytorch_spec: PyTorchInstallSpec,
) -> list[tuple[list[str], Path | None]]:
    torch_install_command = [
        uv_path,
        "pip",
        "install",
        "--no-cache",
        "--python",
        str(venv_python),
        "--reinstall",
        "torch",
        "torchvision",
        "torchaudio",
        "--index-url",
        pytorch_spec.index_url,
    ]
    return [
        (
            [
                uv_path,
                "venv",
                "--no-cache",
                "--python",
                str(base_python),
                "--clear",
                "--seed",
                str(venv_dir),
            ],
            None,
        ),
        (
            [
                uv_path,
                "pip",
                "install",
                "--no-cache",
                "--python",
                str(venv_python),
                "--upgrade",
                "-e",
                ".",
                MMAUDIO_NUMPY_SPEC,
                MMAUDIO_SOUNDFILE_SPEC,
            ],
            mmaudio_dir,
        ),
        (torch_install_command, None),
    ]


def build_cuda_torch_install_command(
    python_executable: str,
    spec: PyTorchInstallSpec | None = None,
    uv_path: str | None = None,
) -> list[str]:
    spec = spec or select_pytorch_install_spec()
    resolved_uv = uv_path or find_uv()
    return [
        resolved_uv or "uv",
        "pip",
        "install",
        "--no-cache",
        "--python",
        python_executable,
        "--reinstall",
        "torch",
        "torchvision",
        "torchaudio",
        "--index-url",
        spec.index_url,
    ]


def build_mmaudio_dependency_repair_command(
    python_executable: str,
    uv_path: str | None = None,
) -> list[str]:
    resolved_uv = uv_path or find_uv()
    return [
        resolved_uv or "uv",
        "pip",
        "install",
        "--no-cache",
        "--python",
        python_executable,
        "--upgrade",
        "-e",
        ".",
        MMAUDIO_NUMPY_SPEC,
        MMAUDIO_SOUNDFILE_SPEC,
    ]


def _is_windows_path() -> bool:
    return os.name == "nt"
