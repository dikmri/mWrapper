import subprocess

from mwrapper.services import hardware
from mwrapper.services.hardware import HardwareInfo, format_hardware_info
from mwrapper.services.package_installer import PYTORCH_CPU_INDEX_URL, PYTORCH_CUDA_INDEX_URL, select_pytorch_install_spec


def test_select_pytorch_install_spec_prefers_cuda_for_nvidia() -> None:
    spec = select_pytorch_install_spec(HardwareInfo(nvidia_gpus=["NVIDIA RTX"], nvidia_driver="555.55"))

    assert spec.requires_cuda
    assert spec.index_url == PYTORCH_CUDA_INDEX_URL


def test_select_pytorch_install_spec_uses_cpu_without_nvidia() -> None:
    spec = select_pytorch_install_spec(HardwareInfo())

    assert not spec.requires_cuda
    assert spec.index_url == PYTORCH_CPU_INDEX_URL


def test_format_hardware_info_reports_gpu() -> None:
    message = format_hardware_info(HardwareInfo(nvidia_gpus=["NVIDIA RTX"], nvidia_driver="555.55"))

    assert "NVIDIA GPUあり" in message
    assert "NVIDIA RTX" in message


def test_windows_video_controller_fallback_detects_nvidia(monkeypatch) -> None:
    monkeypatch.setattr(hardware.os, "name", "nt", raising=False)

    def fake_run(command, **kwargs):
        return subprocess.CompletedProcess(
            command,
            0,
            stdout="NVIDIA GeForce RTX 5060 Ti,596.49\nIntel Graphics,1.0\n",
            stderr="",
        )

    monkeypatch.setattr(hardware.subprocess, "run", fake_run)

    info = hardware._inspect_with_windows_video_controller(10)

    assert info.nvidia_gpus == ["NVIDIA GeForce RTX 5060 Ti"]
    assert info.nvidia_driver == "596.49"
