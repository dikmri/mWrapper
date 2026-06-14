from pathlib import Path

from mwrapper.ui.preview_player import _supported_video_from_event


def test_supported_video_from_event_accepts_video_file(tmp_path: Path) -> None:
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"")

    assert _supported_video_from_event(_FakeDropEvent([video])) == video


def test_supported_video_from_event_ignores_non_video_file(tmp_path: Path) -> None:
    text = tmp_path / "clip.txt"
    text.write_text("not video", encoding="utf-8")

    assert _supported_video_from_event(_FakeDropEvent([text])) is None


class _FakeDropEvent:
    def __init__(self, paths: list[Path]) -> None:
        self._mime_data = _FakeMimeData(paths)

    def mimeData(self) -> "_FakeMimeData":  # noqa: N802
        return self._mime_data


class _FakeMimeData:
    def __init__(self, paths: list[Path]) -> None:
        self._paths = paths

    def hasUrls(self) -> bool:  # noqa: N802
        return bool(self._paths)

    def urls(self) -> list["_FakeUrl"]:
        return [_FakeUrl(path) for path in self._paths]


class _FakeUrl:
    def __init__(self, path: Path) -> None:
        self._path = path

    def isLocalFile(self) -> bool:  # noqa: N802
        return True

    def toLocalFile(self) -> str:  # noqa: N802
        return str(self._path)
