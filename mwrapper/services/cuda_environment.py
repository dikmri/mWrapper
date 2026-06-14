from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from .subprocess_utils import hidden_subprocess_kwargs


@dataclass(slots=True)
class PythonCudaInfo:
    executable: str
    python_version: str = ""
    torch_version: str | None = None
    torch_cuda_version: str | None = None
    cuda_available: bool = False
    device_count: int = 0
    device_names: list[str] = field(default_factory=list)
    device_capabilities: list[str] = field(default_factory=list)
    supported_architectures: list[str] = field(default_factory=list)
    compatibility_error: str | None = None
    error: str | None = None

    @property
    def cuda_usable(self) -> bool:
        return self.cuda_available and self.compatibility_error is None and self.error is None


def inspect_python_cuda(
    python_executable: str,
    cwd: Path | None = None,
    timeout_seconds: int = 30,
) -> PythonCudaInfo:
    code = r"""
import json
import sys

data = {
    "executable": sys.executable,
    "python_version": sys.version.split()[0],
    "torch_version": None,
    "torch_cuda_version": None,
    "cuda_available": False,
    "device_count": 0,
    "device_names": [],
    "device_capabilities": [],
    "supported_architectures": [],
    "compatibility_error": None,
    "error": None,
}

try:
    import torch
    data["torch_version"] = getattr(torch, "__version__", None)
    data["torch_cuda_version"] = getattr(torch.version, "cuda", None)
    data["cuda_available"] = bool(torch.cuda.is_available())
    data["device_count"] = int(torch.cuda.device_count())
    data["device_names"] = [
        torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())
    ]
    try:
        data["supported_architectures"] = list(torch.cuda.get_arch_list())
    except Exception:
        data["supported_architectures"] = []
    for i in range(torch.cuda.device_count()):
        try:
            major, minor = torch.cuda.get_device_capability(i)
            data["device_capabilities"].append(f"sm_{major}{minor}")
        except Exception:
            data["device_capabilities"].append("")
except Exception as exc:
    data["error"] = str(exc)

print(json.dumps(data, ensure_ascii=False))
"""
    executable = python_executable.strip() or "python"
    try:
        completed = subprocess.run(
            [executable, "-c", code],
            cwd=str(cwd) if cwd else None,
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
        return PythonCudaInfo(executable=executable, error=str(exc))

    if completed.returncode != 0:
        details = completed.stderr.strip() or completed.stdout.strip()
        return PythonCudaInfo(executable=executable, error=details or "Python check failed")

    try:
        data = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        return PythonCudaInfo(executable=executable, error=f"Invalid Python check output: {exc}")

    return PythonCudaInfo(
        executable=str(data.get("executable") or executable),
        python_version=str(data.get("python_version") or ""),
        torch_version=data.get("torch_version"),
        torch_cuda_version=data.get("torch_cuda_version"),
        cuda_available=bool(data.get("cuda_available")),
        device_count=int(data.get("device_count") or 0),
        device_names=list(data.get("device_names") or []),
        device_capabilities=list(data.get("device_capabilities") or []),
        supported_architectures=list(data.get("supported_architectures") or []),
        compatibility_error=_detect_compatibility_error(
            list(data.get("device_capabilities") or []),
            list(data.get("supported_architectures") or []),
        ),
        error=data.get("error"),
    )


def format_cuda_info(info: PythonCudaInfo) -> str:
    if info.error:
        return f"CUDA確認: 失敗 / Python: {info.executable} / 詳細: {info.error}"

    torch_version = info.torch_version or "未検出"
    torch_cuda = info.torch_cuda_version or "なし"
    devices = ", ".join(info.device_names) if info.device_names else "なし"
    capabilities = ", ".join(filter(None, info.device_capabilities))
    supported_arches = ", ".join(info.supported_architectures)
    if info.compatibility_error:
        status = "互換性エラー"
    else:
        status = "利用可能" if info.cuda_available else "利用不可"
    message = (
        f"CUDA確認: {status} / Python: {info.executable} / "
        f"PyTorch: {torch_version} / PyTorch CUDA: {torch_cuda} / GPU: {devices}"
    )
    if capabilities:
        message += f" / GPU Capability: {capabilities}"
    if supported_arches:
        message += f" / PyTorch対応: {supported_arches}"

    if info.compatibility_error:
        message += f" / {info.compatibility_error}"
    elif not info.cuda_available:
        if info.torch_version and "+cpu" in info.torch_version.lower():
            message += " / CPU版PyTorchが使われています"
        elif not info.torch_cuda_version:
            message += " / CUDA対応PyTorchではありません"

    return message


def _detect_compatibility_error(
    device_capabilities: list[str],
    supported_architectures: list[str],
) -> str | None:
    device_values = [_arch_value(value) for value in device_capabilities]
    supported_values = [_arch_value(value) for value in supported_architectures if value.startswith("sm_")]
    device_values = [value for value in device_values if value is not None]
    supported_values = [value for value in supported_values if value is not None]
    if not device_values or not supported_values:
        return None

    highest_device = max(device_values)
    highest_supported = max(supported_values)
    if highest_device <= highest_supported:
        return None
    return (
        f"PyTorchがこのGPU世代(sm_{highest_device})に対応していません。"
        f"対応上限はsm_{highest_supported}です。CUDA 12.8版など新しいPyTorchを導入してください。"
    )


def _arch_value(value: str) -> int | None:
    match = re.search(r"sm_(\d+)", value)
    if not match:
        return None
    return int(match.group(1))
