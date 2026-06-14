from pathlib import Path

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


def test_cuda_torch_install_requires_uv_command_when_not_found(monkeypatch) -> None:
    monkeypatch.setattr(package_installer.shutil, "which", lambda name: None)

    command = package_installer.build_cuda_torch_install_command("python.exe")

    assert command[:6] == ["uv", "pip", "install", "--no-cache", "--python", "python.exe"]
    assert "--reinstall" in command
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


def test_mmaudio_dependency_repair_requires_uv_command_when_not_found(monkeypatch) -> None:
    monkeypatch.setattr(package_installer.shutil, "which", lambda name: None)

    command = package_installer.build_mmaudio_dependency_repair_command("python.exe")

    assert command[:6] == ["uv", "pip", "install", "--no-cache", "--python", "python.exe"]
    assert "-e" in command
    assert package_installer.MMAUDIO_NUMPY_SPEC in command
    assert package_installer.MMAUDIO_SOUNDFILE_SPEC in command


def test_uv_bootstrap_commands_install_local_uv(tmp_path: Path) -> None:
    commands = package_installer.build_uv_bootstrap_commands(
        tmp_path / "base" / "python.exe",
        tmp_path / "venvs",
    )

    assert commands[0][0] == [
        str(tmp_path / "base" / "python.exe"),
        "-m",
        "venv",
        "--clear",
        str(tmp_path / "venvs" / "_uv"),
    ]
    assert commands[1][0][-2:] == ["ensurepip", "--upgrade"]
    assert commands[2][0][-2:] == ["pip", "uv"]


def test_mmaudio_venv_commands_reinstall_torch_last(tmp_path: Path) -> None:
    commands = package_installer.build_mmaudio_venv_commands(
        uv_path="uv",
        base_python=tmp_path / "base" / "python.exe",
        venv_dir=tmp_path / "venv",
        venv_python=tmp_path / "venv" / "Scripts" / "python.exe",
        mmaudio_dir=tmp_path / "MMAudio",
        pytorch_spec=package_installer.select_pytorch_install_spec(),
    )

    assert commands[0][0][0:2] == ["uv", "venv"]
    assert commands[1][0][0:3] == ["uv", "pip", "install"]
    assert commands[1][1] == tmp_path / "MMAudio"
    assert commands[2][0][0:3] == ["uv", "pip", "install"]
    assert "--reinstall" in commands[2][0]
    assert "torch" in commands[2][0]
