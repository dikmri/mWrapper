from pathlib import Path

from mwrapper.workers.mmaudio_env_setup_worker import MMAudioEnvSetupWorker


def test_uv_commands_target_dedicated_venv_python(tmp_path: Path) -> None:
    worker = MMAudioEnvSetupWorker(
        tmp_path / "base" / "python.exe",
        tmp_path / "venv",
        tmp_path / "MMAudio",
    )
    venv_python = tmp_path / "venv" / "Scripts" / "python.exe"

    commands = worker._uv_commands("uv", venv_python)

    assert commands[0][0] == [
        "uv",
        "venv",
        "--python",
        str(tmp_path / "base" / "python.exe"),
        "--clear",
        "--seed",
        str(tmp_path / "venv"),
    ]
    assert commands[1][0][:5] == [
        "uv",
        "pip",
        "install",
        "--python",
        str(venv_python),
    ]
    assert "--reinstall" in commands[1][0]
    assert "--index-url" in commands[1][0]
    assert commands[2][0][:5] == [
        "uv",
        "pip",
        "install",
        "--python",
        str(venv_python),
    ]


def test_pip_fallback_commands_install_inside_venv(tmp_path: Path) -> None:
    worker = MMAudioEnvSetupWorker(
        tmp_path / "base" / "python.exe",
        tmp_path / "venv",
        tmp_path / "MMAudio",
    )
    venv_python = tmp_path / "venv" / "Scripts" / "python.exe"

    commands = worker._pip_commands(venv_python)

    assert commands[0][0] == [
        str(tmp_path / "base" / "python.exe"),
        "-m",
        "venv",
        "--clear",
        str(tmp_path / "venv"),
    ]
    assert commands[1][0][:4] == [str(venv_python), "-m", "pip", "install"]
    assert commands[2][0][:4] == [str(venv_python), "-m", "pip", "install"]
    assert "--force-reinstall" in commands[2][0]
    assert commands[3][0][:4] == [str(venv_python), "-m", "pip", "install"]
