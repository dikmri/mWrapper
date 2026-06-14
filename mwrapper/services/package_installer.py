from __future__ import annotations

import shutil
from dataclasses import dataclass

from .hardware import HardwareInfo


PYTORCH_CUDA_LABEL = "CUDA 12.8"
PYTORCH_CUDA_INDEX_URL = "https://download.pytorch.org/whl/cu128"
PYTORCH_CPU_LABEL = "CPU"
PYTORCH_CPU_INDEX_URL = "https://download.pytorch.org/whl/cpu"
MMAUDIO_NUMPY_SPEC = "numpy<2.1,>=1.21"
MMAUDIO_SOUNDFILE_SPEC = "soundfile>=0.12"


@dataclass(frozen=True, slots=True)
class PyTorchInstallSpec:
    label: str
    index_url: str
    requires_cuda: bool = True


def select_pytorch_install_spec(hardware: HardwareInfo | None = None) -> PyTorchInstallSpec:
    if hardware is not None and not hardware.has_nvidia_gpu:
        return PyTorchInstallSpec(PYTORCH_CPU_LABEL, PYTORCH_CPU_INDEX_URL, requires_cuda=False)
    return PyTorchInstallSpec(PYTORCH_CUDA_LABEL, PYTORCH_CUDA_INDEX_URL, requires_cuda=True)


def build_cuda_torch_install_command(
    python_executable: str,
    spec: PyTorchInstallSpec | None = None,
) -> list[str]:
    spec = spec or select_pytorch_install_spec()
    uv_path = shutil.which("uv")
    if uv_path:
        return [
            uv_path,
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

    return [
        python_executable,
        "-m",
        "pip",
        "install",
        "--no-cache-dir",
        "--upgrade",
        "--force-reinstall",
        "torch",
        "torchvision",
        "torchaudio",
        "--index-url",
        spec.index_url,
    ]


def build_mmaudio_dependency_repair_command(python_executable: str) -> list[str]:
    uv_path = shutil.which("uv")
    if uv_path:
        return [
            uv_path,
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

    return [
        python_executable,
        "-m",
        "pip",
        "install",
        "--no-cache-dir",
        "--upgrade",
        "-e",
        ".",
        MMAUDIO_NUMPY_SPEC,
        MMAUDIO_SOUNDFILE_SPEC,
    ]
