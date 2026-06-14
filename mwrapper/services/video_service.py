from __future__ import annotations

from pathlib import Path

from ..constants import SUPPORTED_VIDEO_EXTENSIONS
from .ffmpeg import VideoInfo, probe_video


class UnsupportedVideoError(ValueError):
    pass


def is_supported_video_path(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_VIDEO_EXTENSIONS


class VideoService:
    def __init__(self, ffprobe_path: str = "ffprobe") -> None:
        self.ffprobe_path = ffprobe_path

    def validate_path(self, path: Path) -> None:
        if not path.exists():
            raise UnsupportedVideoError("ファイルが存在しません。")
        if not path.is_file():
            raise UnsupportedVideoError("ファイルを選択してください。")
        if not is_supported_video_path(path):
            allowed = ", ".join(sorted(SUPPORTED_VIDEO_EXTENSIONS))
            raise UnsupportedVideoError(f"対応していない形式です。対応形式: {allowed}")

    def probe(self, path: Path) -> VideoInfo:
        self.validate_path(path)
        return probe_video(path, self.ffprobe_path)
