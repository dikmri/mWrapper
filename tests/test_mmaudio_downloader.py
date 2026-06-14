from pathlib import Path

from mwrapper.services.mmaudio_downloader import default_mmaudio_install_dir


def test_default_mmaudio_install_dir(tmp_path: Path) -> None:
    assert default_mmaudio_install_dir(tmp_path) == tmp_path / "MMAudio"
