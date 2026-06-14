from pathlib import Path

from mwrapper.services.ffmpeg import parse_fps
from mwrapper.services.video_service import is_supported_video_path


def test_supported_video_extension_is_case_insensitive() -> None:
    assert is_supported_video_path(Path("movie.MP4"))
    assert is_supported_video_path(Path("movie.webm"))
    assert not is_supported_video_path(Path("movie.txt"))


def test_parse_fps() -> None:
    assert parse_fps("30000/1001") == 30000 / 1001
    assert parse_fps("0/0") is None
    assert parse_fps("bad") is None
