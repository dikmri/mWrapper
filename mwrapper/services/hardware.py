from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field

from .subprocess_utils import hidden_subprocess_kwargs


@dataclass(frozen=True, slots=True)
class HardwareInfo:
    nvidia_gpus: list[str] = field(default_factory=list)
    nvidia_driver: str = ""
    error: str | None = None

    @property
    def has_nvidia_gpu(self) -> bool:
        return bool(self.nvidia_gpus)


def inspect_hardware(timeout_seconds: int = 10) -> HardwareInfo:
    nvidia_smi_info = _inspect_with_nvidia_smi(timeout_seconds)
    if nvidia_smi_info.has_nvidia_gpu:
        return nvidia_smi_info

    windows_info = _inspect_with_windows_video_controller(timeout_seconds)
    if windows_info.has_nvidia_gpu:
        return windows_info

    return nvidia_smi_info


def _inspect_with_nvidia_smi(timeout_seconds: int) -> HardwareInfo:
    try:
        completed = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,driver_version",
                "--format=csv,noheader",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            check=False,
            shell=False,
            **hidden_subprocess_kwargs(),
        )
    except Exception as exc:
        return HardwareInfo(error=str(exc))

    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        return HardwareInfo(error=detail or "nvidia-smi failed")

    gpus: list[str] = []
    driver = ""
    for line in completed.stdout.splitlines():
        parts = [part.strip() for part in line.split(",")]
        if not parts or not parts[0]:
            continue
        gpus.append(parts[0])
        if len(parts) > 1 and parts[1]:
            driver = parts[1]
    return HardwareInfo(nvidia_gpus=gpus, nvidia_driver=driver)


def _inspect_with_windows_video_controller(timeout_seconds: int) -> HardwareInfo:
    if os.name != "nt":
        return HardwareInfo()

    command = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        "Get-CimInstance Win32_VideoController | "
        "ForEach-Object { \"$($_.Name),$($_.DriverVersion)\" }",
    ]
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            check=False,
            shell=False,
            **hidden_subprocess_kwargs(),
        )
    except Exception as exc:
        return HardwareInfo(error=str(exc))

    if completed.returncode != 0:
        return HardwareInfo(error=completed.stderr.strip() or completed.stdout.strip())

    gpus: list[str] = []
    driver = ""
    for line in completed.stdout.splitlines():
        name, _, raw_driver = line.partition(",")
        name = name.strip()
        if not name or "nvidia" not in name.lower():
            continue
        gpus.append(name)
        if raw_driver.strip():
            driver = raw_driver.strip()
    return HardwareInfo(nvidia_gpus=gpus, nvidia_driver=driver)


def format_hardware_info(info: HardwareInfo) -> str:
    if not info.nvidia_gpus:
        if info.error:
            return f"ハードウェア確認: NVIDIA GPUを検出できませんでした / 詳細: {info.error}"
        return "ハードウェア確認: NVIDIA GPUなし"
    gpus = ", ".join(info.nvidia_gpus)
    driver = info.nvidia_driver or "不明"
    return f"ハードウェア確認: NVIDIA GPUあり / GPU: {gpus} / Driver: {driver}"
