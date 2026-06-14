from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(slots=True)
class GenerateJob:
    job_id: str
    input_video_path: Path
    japanese_prompt: str
    english_prompt: str
    seed: int | None
    duration: float | None
    model_id: str
    output_dir: Path
    created_at: datetime
    python_executable: str
    mmaudio_script_path: Path
    mmaudio_working_dir: Path
    mmaudio_output_dir: Path | None
    search_dirs: list[Path]
    extra_args: list[str]
    require_cuda: bool = True


@dataclass(slots=True)
class GenerateResult:
    job_id: str
    success: bool
    output_video_path: Path | None
    output_audio_path: Path | None
    log_path: Path
    error_message: str | None
    started_at: datetime
    finished_at: datetime
