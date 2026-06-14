from __future__ import annotations

import subprocess
import threading
import os
from datetime import datetime
from pathlib import Path
from typing import Callable

from ..core.jobs import GenerateJob, GenerateResult
from .cuda_environment import format_cuda_info, inspect_python_cuda
from .log_formatter import format_log_line
from .mmaudio_dependencies import (
    format_mmaudio_dependency_info,
    inspect_mmaudio_dependencies,
)
from .mmaudio_demo_patch import patch_mmaudio_demo
from .output_manager import detect_newest_output, snapshot_media_files
from .process_log_guard import ProcessLogGuard, diagnose_fatal_log_line


LogCallback = Callable[[str], None]


class MMAudioRunner:
    def __init__(self) -> None:
        self._process: subprocess.Popen[str] | None = None
        self._lock = threading.Lock()

    def build_command(self, job: GenerateJob) -> list[str]:
        duration = job.duration if job.duration is not None else 8.0
        command = [
            job.python_executable or "python",
            str(job.mmaudio_script_path),
            f"--variant={job.model_id}",
            f"--duration={duration:g}",
            f"--video={job.input_video_path}",
            f"--prompt={job.english_prompt}",
        ]
        if job.negative_prompt.strip():
            command.append(f"--negative_prompt={job.negative_prompt}")
        if job.seed is not None:
            command.append(f"--seed={job.seed}")
        command.extend(job.extra_args)
        return command

    def run(self, job: GenerateJob, on_log: LogCallback) -> GenerateResult:
        started_at = datetime.now()
        log_path = job.output_dir / "generation.log"
        job.output_dir.mkdir(parents=True, exist_ok=True)

        try:
            self._validate_job(job)
            cuda_info = inspect_python_cuda(job.python_executable, job.mmaudio_working_dir)
            on_log(format_cuda_info(cuda_info))
            if job.require_cuda and not cuda_info.cuda_usable:
                return GenerateResult(
                    job_id=job.job_id,
                    success=False,
                    output_video_path=None,
                    output_audio_path=None,
                    log_path=log_path,
                    error_message=(
                        "CUDA対応PyTorchがこのGPUで利用できないため生成を開始しませんでした。"
                        "MMAudio PythonにCUDA版PyTorchを導入するか、CUDA必須をオフにしてください。"
                    ),
                    started_at=started_at,
                    finished_at=datetime.now(),
                )

            dependency_info = inspect_mmaudio_dependencies(
                job.python_executable,
                job.mmaudio_working_dir,
            )
            on_log(format_mmaudio_dependency_info(dependency_info))
            if not dependency_info.ok:
                return GenerateResult(
                    job_id=job.job_id,
                    success=False,
                    output_video_path=None,
                    output_audio_path=None,
                    log_path=log_path,
                    error_message=(
                        "MMAudioのPython依存関係に問題があります。"
                        "MMAudio依存修復を実行してから再試行してください。"
                    ),
                    started_at=started_at,
                    finished_at=datetime.now(),
                )

            patch_result = patch_mmaudio_demo(job.mmaudio_script_path)
            if patch_result.changed:
                on_log(patch_result.message)

            search_dirs = self._existing_or_creatable_search_dirs(job)
            before = snapshot_media_files(search_dirs)
            command = self.build_command(job)

            on_log(format_log_line("Starting MMAudio CLI"))
            on_log(subprocess.list2cmdline(command))

            log_guard = ProcessLogGuard(on_log)
            fatal_error: str | None = None
            with log_path.open("w", encoding="utf-8") as log_file:
                log_file.write(subprocess.list2cmdline(command) + "\n")
                log_file.flush()

                with self._lock:
                    self._process = subprocess.Popen(
                        command,
                        cwd=str(job.mmaudio_working_dir),
                        env=self._runtime_env(job),
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        shell=False,
                    )

                assert self._process.stdout is not None
                for line in self._process.stdout:
                    cleaned = format_log_line(line)
                    if not cleaned:
                        continue
                    log_file.write(cleaned + "\n")
                    fatal_error = diagnose_fatal_log_line(cleaned)
                    log_guard.emit(cleaned)
                    if fatal_error:
                        log_guard.emit(f"致命的エラーを検出したためMMAudioを停止しました: {fatal_error}")
                        self._terminate_process(timeout_seconds=2)
                        break

                return_code = self._process.wait()
                log_guard.finish()

            with self._lock:
                self._process = None

            if fatal_error:
                return GenerateResult(
                    job_id=job.job_id,
                    success=False,
                    output_video_path=None,
                    output_audio_path=None,
                    log_path=log_path,
                    error_message=fatal_error,
                    started_at=started_at,
                    finished_at=datetime.now(),
                )

            if return_code != 0:
                return GenerateResult(
                    job_id=job.job_id,
                    success=False,
                    output_video_path=None,
                    output_audio_path=None,
                    log_path=log_path,
                    error_message=f"MMAudio exited with code {return_code}",
                    started_at=started_at,
                    finished_at=datetime.now(),
                )

            output_video, output_audio = detect_newest_output(search_dirs, before)
            if output_video is None:
                return GenerateResult(
                    job_id=job.job_id,
                    success=False,
                    output_video_path=None,
                    output_audio_path=output_audio,
                    log_path=log_path,
                    error_message="MMAudio output mp4 was not found.",
                    started_at=started_at,
                    finished_at=datetime.now(),
                )

            return GenerateResult(
                job_id=job.job_id,
                success=True,
                output_video_path=output_video,
                output_audio_path=output_audio,
                log_path=log_path,
                error_message=None,
                started_at=started_at,
                finished_at=datetime.now(),
            )
        except Exception as exc:
            with self._lock:
                self._process = None
            on_log(format_log_line(f"Error: {exc}"))
            return GenerateResult(
                job_id=job.job_id,
                success=False,
                output_video_path=None,
                output_audio_path=None,
                log_path=log_path,
                error_message=str(exc),
                started_at=started_at,
                finished_at=datetime.now(),
            )

    def cancel(self) -> None:
        self._terminate_process(timeout_seconds=5)

    def _terminate_process(self, timeout_seconds: int) -> None:
        with self._lock:
            process = self._process

        if process is None or process.poll() is not None:
            return

        process.terminate()
        try:
            process.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            process.kill()

    @staticmethod
    def _validate_job(job: GenerateJob) -> None:
        if not job.input_video_path.exists():
            raise FileNotFoundError(f"Input video not found: {job.input_video_path}")
        if not job.mmaudio_script_path.exists():
            raise FileNotFoundError(
                "MMAudio demo.py is not configured or does not exist."
            )
        if not job.english_prompt.strip():
            raise ValueError("Positive prompt is required.")

    @staticmethod
    def _existing_or_creatable_search_dirs(job: GenerateJob) -> list[Path]:
        dirs = list(job.search_dirs)
        if job.mmaudio_output_dir is not None:
            dirs.append(job.mmaudio_output_dir)
        dirs.append(job.mmaudio_working_dir / "output")
        dirs.append(job.mmaudio_script_path.parent / "output")

        result: list[Path] = []
        seen: set[Path] = set()
        for directory in dirs:
            resolved = directory.resolve()
            if resolved in seen:
                continue
            if not resolved.exists():
                try:
                    resolved.mkdir(parents=True, exist_ok=True)
                except OSError:
                    continue
            seen.add(resolved)
            result.append(resolved)
        return result

    @staticmethod
    def _runtime_env(job: GenerateJob) -> dict[str, str]:
        env = os.environ.copy()
        if job.runtime_cache_dir is None:
            return env

        cache_root = job.runtime_cache_dir
        hf_home = cache_root / "huggingface"
        env["HF_HOME"] = str(hf_home)
        env["HUGGINGFACE_HUB_CACHE"] = str(hf_home / "hub")
        env["TORCH_HOME"] = str(cache_root / "torch")
        env["XDG_CACHE_HOME"] = str(cache_root)
        return env
