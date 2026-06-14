from mwrapper.services import updater


def test_parse_version_ignores_v_prefix() -> None:
    assert updater.parse_version("v1.2.3") == (1, 2, 3)
    assert updater.parse_version("1.2.3") == (1, 2, 3)


def test_is_newer_version_compares_numeric_parts() -> None:
    assert updater.is_newer_version("v0.1.10", "0.1.9")
    assert not updater.is_newer_version("v0.1.2", "0.1.2")
    assert not updater.is_newer_version("v0.1.2", "0.1.3")


def test_select_windows_asset_prefers_release_zip() -> None:
    asset = updater._select_windows_asset(
        [
            {"name": "mwrapper-0.1.3.tar.gz", "browser_download_url": "source", "size": 1},
            {
                "name": "mWrapper-v0.1.3-windows.zip",
                "browser_download_url": "windows",
                "size": 100,
            },
        ]
    )

    assert asset is not None
    assert asset.name == "mWrapper-v0.1.3-windows.zip"
    assert asset.download_url == "windows"


def test_updater_script_replaces_app_items_not_install_dir() -> None:
    script = updater._updater_script()

    assert 'Set-Location -LiteralPath $TempRoot' in script
    assert 'Replacing app files in $InstallDir' in script
    assert 'Move-Item -LiteralPath $InstallDir -Destination' not in script
    assert 'Join-Path $TempRoot "backup"' in script


def test_launch_update_replacer_runs_from_temp_root(monkeypatch, tmp_path) -> None:
    captured = {}

    class FakeProcess:
        pass

    def fake_popen(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        return FakeProcess()

    monkeypatch.setattr(updater.subprocess, "Popen", fake_popen)

    updater.launch_update_replacer(
        zip_path=tmp_path / "update.zip",
        install_dir=tmp_path / "app",
        exe_name="mWrapper.exe",
        wait_pid=123,
        temp_root=tmp_path / "temp",
    )

    assert captured["kwargs"]["cwd"] == str(tmp_path / "temp")
    assert "-LogPath" in captured["command"]
    assert str(tmp_path / "app" / "update.log") in captured["command"]
