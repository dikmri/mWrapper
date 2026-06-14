from __future__ import annotations

import shutil


PYTORCH_CUDA_LABEL = "CUDA 12.8"
PYTORCH_CUDA_INDEX_URL = "https://download.pytorch.org/whl/cu128"
MMAUDIO_NUMPY_SPEC = "numpy<2.1,>=1.21"
MMAUDIO_SOUNDFILE_SPEC = "soundfile>=0.12"


def build_cuda_torch_install_command(python_executable: str) -> list[str]:
    uv_path = shutil.which("uv")
    if uv_path:
        return [
            uv_path,
            "pip",
            "install",
            "--python",
            python_executable,
            "--reinstall",
            "torch",
            "torchvision",
            "torchaudio",
            "--index-url",
            PYTORCH_CUDA_INDEX_URL,
        ]

    return [
        python_executable,
        "-m",
        "pip",
        "install",
        "--upgrade",
        "--force-reinstall",
        "torch",
        "torchvision",
        "torchaudio",
        "--index-url",
        PYTORCH_CUDA_INDEX_URL,
    ]


def build_mmaudio_dependency_repair_command(python_executable: str) -> list[str]:
    uv_path = shutil.which("uv")
    if uv_path:
        return [
            uv_path,
            "pip",
            "install",
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
        "--upgrade",
        "-e",
        ".",
        MMAUDIO_NUMPY_SPEC,
        MMAUDIO_SOUNDFILE_SPEC,
    ]
