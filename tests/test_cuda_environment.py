from mwrapper.services.cuda_environment import PythonCudaInfo, format_cuda_info


def test_format_cuda_info_reports_available_gpu() -> None:
    info = PythonCudaInfo(
        executable="python",
        python_version="3.11",
        torch_version="2.5.1+cu118",
        torch_cuda_version="11.8",
        cuda_available=True,
        device_count=1,
        device_names=["NVIDIA GeForce RTX"],
    )

    message = format_cuda_info(info)

    assert "CUDA確認: 利用可能" in message
    assert "NVIDIA GeForce RTX" in message


def test_format_cuda_info_reports_cpu_torch() -> None:
    info = PythonCudaInfo(
        executable="python",
        python_version="3.13",
        torch_version="2.10.0+cpu",
        torch_cuda_version=None,
        cuda_available=False,
    )

    message = format_cuda_info(info)

    assert "CUDA確認: 利用不可" in message
    assert "CPU版PyTorch" in message


def test_format_cuda_info_reports_arch_incompatibility() -> None:
    info = PythonCudaInfo(
        executable="python",
        python_version="3.11",
        torch_version="2.7.1+cu118",
        torch_cuda_version="11.8",
        cuda_available=True,
        device_count=1,
        device_names=["NVIDIA GeForce RTX 5060 Ti"],
        device_capabilities=["sm_120"],
        supported_architectures=["sm_37", "sm_80", "sm_90"],
        compatibility_error="PyTorchがこのGPU世代(sm_120)に対応していません。",
    )

    message = format_cuda_info(info)

    assert not info.cuda_usable
    assert "CUDA確認: 互換性エラー" in message
    assert "sm_120" in message
