from mwrapper.services import package_installer


def test_cuda_torch_install_prefers_uv(monkeypatch) -> None:
    monkeypatch.setattr(package_installer.shutil, "which", lambda name: "uv" if name == "uv" else None)

    command = package_installer.build_cuda_torch_install_command("python.exe")

    assert command[:6] == ["uv", "pip", "install", "--no-cache", "--python", "python.exe"]
    assert "--no-cache" in command
    assert "--reinstall" in command
    assert "torch" in command
    assert package_installer.PYTORCH_CUDA_INDEX_URL in command
    assert package_installer.PYTORCH_CUDA_INDEX_URL.endswith("/cu128")


def test_cuda_torch_install_falls_back_to_pip(monkeypatch) -> None:
    monkeypatch.setattr(package_installer.shutil, "which", lambda name: None)

    command = package_installer.build_cuda_torch_install_command("python.exe")

    assert command[:4] == ["python.exe", "-m", "pip", "install"]
    assert "--no-cache-dir" in command
    assert "--force-reinstall" in command
    assert package_installer.PYTORCH_CUDA_INDEX_URL in command
    assert package_installer.PYTORCH_CUDA_INDEX_URL.endswith("/cu128")


def test_mmaudio_dependency_repair_prefers_uv(monkeypatch) -> None:
    monkeypatch.setattr(package_installer.shutil, "which", lambda name: "uv" if name == "uv" else None)

    command = package_installer.build_mmaudio_dependency_repair_command("python.exe")

    assert command[:6] == ["uv", "pip", "install", "--no-cache", "--python", "python.exe"]
    assert "--no-cache" in command
    assert "-e" in command
    assert package_installer.MMAUDIO_NUMPY_SPEC in command
    assert package_installer.MMAUDIO_SOUNDFILE_SPEC in command


def test_mmaudio_dependency_repair_falls_back_to_pip(monkeypatch) -> None:
    monkeypatch.setattr(package_installer.shutil, "which", lambda name: None)

    command = package_installer.build_mmaudio_dependency_repair_command("python.exe")

    assert command[:4] == ["python.exe", "-m", "pip", "install"]
    assert "--no-cache-dir" in command
    assert "-e" in command
    assert package_installer.MMAUDIO_NUMPY_SPEC in command
    assert package_installer.MMAUDIO_SOUNDFILE_SPEC in command
