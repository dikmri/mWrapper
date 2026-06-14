from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any


class FFprobeError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class VideoInfo:
    path: Path
    duration: float | None
    width: int | None
    height: int | None
    fps: float | None
    video_codec: str | None
    audio_codec: str | None
    audio_stream_count: int
    bitrate: int | None
    file_size: int


def find_tool(configured_path: str, executable_name: str) -> str:
    if configured_path:
        path = Path(configured_path)
        if path.exists():
            return str(path)
    found = shutil.which(executable_name)
    if found:
        return found
    return executable_name


def parse_fps(value: str | None) -> float | None:
    if not value or value == "0/0":
        return None
    try:
        fraction = Fraction(value)
    except (ValueError, ZeroDivisionError):
        return None
    if fraction.denominator == 0:
        return None
    result = float(fraction)
    return result if result > 0 else None


def _first_stream(data: dict[str, Any], codec_type: str) -> dict[str, Any] | None:
    for stream in data.get("streams", []):
        if stream.get("codec_type") == codec_type:
            return stream
    return None


def probe_video(path: Path, ffprobe_path: str = "ffprobe") -> VideoInfo:
    if not path.exists():
        raise FFprobeError(f"File does not exist: {path}")

    command = [
        ffprobe_path,
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]

    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except OSError as exc:
        raise FFprobeError(f"Failed to start ffprobe: {exc}") from exc

    if completed.returncode != 0:
        details = completed.stderr.strip() or completed.stdout.strip()
        raise FFprobeError(details or "ffprobe failed")

    try:
        data = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise FFprobeError("ffprobe returned invalid JSON") from exc

    video = _first_stream(data, "video")
    if video is None:
        raise FFprobeError("No video stream found")

    audio_streams = [
        stream for stream in data.get("streams", []) if stream.get("codec_type") == "audio"
    ]
    first_audio = audio_streams[0] if audio_streams else None
    fmt = data.get("format", {})

    duration = _to_float(fmt.get("duration") or video.get("duration"))
    bitrate = _to_int(fmt.get("bit_rate"))

    return VideoInfo(
        path=path,
        duration=duration,
        width=_to_int(video.get("width")),
        height=_to_int(video.get("height")),
        fps=parse_fps(video.get("avg_frame_rate") or video.get("r_frame_rate")),
        video_codec=video.get("codec_name"),
        audio_codec=first_audio.get("codec_name") if first_audio else None,
        audio_stream_count=len(audio_streams),
        bitrate=bitrate,
        file_size=path.stat().st_size,
    )


def _to_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
