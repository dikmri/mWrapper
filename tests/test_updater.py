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
