from __future__ import annotations

import re
import shutil
from pathlib import Path


WINDOWS_INVALID_CHARS = r'<>:"/\|?*'


def sanitize_filename_stem(stem: str) -> str:
    cleaned = re.sub(f"[{re.escape(WINDOWS_INVALID_CHARS)}]", "_", stem).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = cleaned.rstrip(". ")
    return cleaned or "video"


def numbered_output_path(directory: Path, original_video_path: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    base_stem = sanitize_filename_stem(original_video_path.stem)
    first = directory / f"{base_stem}_mmaudio.mp4"
    if not first.exists():
        return first

    for index in range(1, 1000):
        candidate = directory / f"{base_stem}_mmaudio_{index:03d}.mp4"
        if not candidate.exists():
            return candidate

    raise FileExistsError("連番の保存先を作成できませんでした。")


def save_generated_video(
    generated_video_path: Path,
    original_video_path: Path,
    destination_dir: Path,
) -> Path:
    if not generated_video_path.exists():
        raise FileNotFoundError(f"生成済み動画が見つかりません: {generated_video_path}")
    destination = numbered_output_path(destination_dir, original_video_path)
    shutil.copy2(generated_video_path, destination)
    return destination


def snapshot_media_files(directories: list[Path]) -> set[Path]:
    files: set[Path] = set()
    for directory in _existing_dirs(directories):
        files.update(directory.glob("*.mp4"))
        files.update(directory.glob("*.flac"))
        files.update(directory.glob("*.wav"))
    return {path.resolve() for path in files if path.is_file()}


def detect_newest_output(
    directories: list[Path],
    before: set[Path] | None = None,
) -> tuple[Path | None, Path | None]:
    before = before or set()
    candidates = [
        path.resolve()
        for directory in _existing_dirs(directories)
        for path in directory.glob("*")
        if path.is_file() and path.suffix.lower() in {".mp4", ".flac", ".wav"}
    ]
    new_candidates = [path for path in candidates if path not in before]
    pool = new_candidates or candidates

    def newest(paths: list[Path], suffixes: set[str]) -> Path | None:
        filtered = [path for path in paths if path.suffix.lower() in suffixes]
        if not filtered:
            return None
        return max(filtered, key=lambda path: path.stat().st_mtime)

    return newest(pool, {".mp4"}), newest(pool, {".flac", ".wav"})


def _existing_dirs(directories: list[Path]) -> list[Path]:
    seen: set[Path] = set()
    result: list[Path] = []
    for directory in directories:
        resolved = directory.resolve()
        if resolved in seen or not resolved.exists() or not resolved.is_dir():
            continue
        seen.add(resolved)
        result.append(resolved)
    return result
