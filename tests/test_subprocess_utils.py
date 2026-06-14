import os
import subprocess

from mwrapper.services.subprocess_utils import hidden_subprocess_kwargs


def test_hidden_subprocess_kwargs_hide_console_on_windows() -> None:
    kwargs = hidden_subprocess_kwargs()

    if os.name != "nt":
        assert kwargs == {}
        return

    assert kwargs["creationflags"] == subprocess.CREATE_NO_WINDOW
    startupinfo = kwargs["startupinfo"]
    assert startupinfo.dwFlags & subprocess.STARTF_USESHOWWINDOW
    assert startupinfo.wShowWindow == subprocess.SW_HIDE
