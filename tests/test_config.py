from pathlib import Path

from mwrapper.core.config import ConfigManager


def test_config_manager_creates_default_config(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    manager = ConfigManager(path)

    config = manager.load()

    assert path.exists()
    assert config.version == 1
    assert config.paths.output_dir
    assert config.paths.tools_dir
    assert config.mmaudio.python_executable
    assert config.generation.require_cuda is True


def test_config_manager_round_trips_mmaudio_script_path(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    manager = ConfigManager(path)
    config = manager.load()
    config.mmaudio.demo_script_path = "C:/MMAudio/demo.py"

    manager.save(config)
    loaded = manager.load()

    assert loaded.mmaudio.demo_script_path == "C:/MMAudio/demo.py"
