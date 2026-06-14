from pathlib import Path

from mwrapper.services.python_env import PY_LAUNCHER_LINE_RE


def test_py_launcher_line_regex_parses_astral_python() -> None:
    line = (
        r" -V:Astral/CPython3.10.18 "
        r"F:\StabilityMatrix-win-x64\Data\Assets\Python\cpython-3.10.18-windows-x86_64-none\python.exe"
    )

    match = PY_LAUNCHER_LINE_RE.search(line)

    assert match is not None
    assert match.group(1) == "3"
    assert match.group(2) == "10"
    assert match.group(3) == "18"
    assert Path(match.group(4)).name == "python.exe"
