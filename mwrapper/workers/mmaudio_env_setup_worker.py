from __future__ import annotations

import subprocess
import threading
import shutil
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from ..services.package_installer import (
    MMAUDIO_NUMPY_SPEC,
    MMAUDIO_SOUNDFILE_SPEC,
    PyTorchInstallSpec,
    select_pytorch_install_spec,
)
from ..services.subprocess_utils import hidden_subprocess_kwargs


class MMAudioEnvSetupWorker(QThread):
    log = Signal(str)
    finished_setup = Signal(int, object)

    def __init__(
        self,
        base_python: Path,
        venv_dir: Path,
        mmaudio_dir: Path,
        pytorch_spec: PyTorchInstallSpec | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.base_python = base_python
        self.venv_dir = venv_dir
        self.mmaudio_dir = mmaudio_dir
        self.pytorch_spec = pytorch_spec or select_pytorch_install_spec()
        self._process: subprocess.Popen[str] | None = None
        self._lock = threading.Lock()

    def run(self) -> None:
        venv_python = self.venv_dir / "Scripts" / "python.exe"
        uv_path = shutil.which("uv")
        commands = self._uv_commands(uv_path, venv_python) if uv_path else self._pip_commands(venv_python)
        self.log.emit(
            f"PyTorch構成: {self.pytorch_spec.label} / index: {self.pytorch_spec.index_url}"
        )
        self.log.emit(
            "uvを使ってMMAudio専用venvを構築します。"
            if uv_path
            else "uvが見つからないため、python -m venv と pip にフォールバックします。"
        )

        return_code = 0
        try:
            self.venv_dir.parent.mkdir(parents=True, exist_ok=True)
            for command, cwd in commands:
                return_code = self._run_command(command, cwd)
                if return_code != 0:
                    break
        except Exception as exc:
            self.log.emit(f"エラー: {exc}")
            return_code = 1
        finally:
            with self._lock:
                self._process = None

        self.finished_setup.emit(return_code, venv_python if return_code == 0 else None)

    def _uv_commands(self, uv_path: str, venv_python: Path) -> list[tuple[list[str], Path | None]]:
        return [
            (
                [
                    uv_path,
                    "venv",
                    "--no-cache",
                    "--python",
                    str(self.base_python),
                    "--clear",
                    "--seed",
                    str(self.venv_dir),
                ],
                None,
            ),
            (
                [
                    uv_path,
                    "pip",
                    "install",
                    "--no-cache",
                    "--python",
                    str(venv_python),
                    "--reinstall",
                    "torch",
                    "torchvision",
                    "torchaudio",
                    "--index-url",
                    self.pytorch_spec.index_url,
                ],
                None,
            ),
            (
                [
                    uv_path,
                    "pip",
                    "install",
                    "--no-cache",
                    "--python",
                    str(venv_python),
                    "--upgrade",
                    "-e",
                    ".",
                    MMAUDIO_NUMPY_SPEC,
                    MMAUDIO_SOUNDFILE_SPEC,
                ],
                self.mmaudio_dir,
            ),
        ]

    def _pip_commands(self, venv_python: Path) -> list[tuple[list[str], Path | None]]:
        return [
            ([str(self.base_python), "-m", "venv", "--clear", str(self.venv_dir)], None),
            ([str(venv_python), "-m", "pip", "install", "--no-cache-dir", "--upgrade", "pip"], None),
            (
                [
                    str(venv_python),
                    "-m",
                    "pip",
                    "install",
                    "--no-cache-dir",
                    "--upgrade",
                    "--force-reinstall",
                    "torch",
                    "torchvision",
                    "torchaudio",
                    "--index-url",
                    self.pytorch_spec.index_url,
                ],
                None,
            ),
            (
                [
                    str(venv_python),
                    "-m",
                    "pip",
                    "install",
                    "--no-cache-dir",
                    "--upgrade",
                    "-e",
                    ".",
                    MMAUDIO_NUMPY_SPEC,
                    MMAUDIO_SOUNDFILE_SPEC,
                ],
                self.mmaudio_dir,
            ),
        ]

    def cancel(self) -> None:
        with self._lock:
            process = self._process
        if process is None or process.poll() is not None:
            return
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()

    def _run_command(self, command: list[str], cwd: Path | None) -> int:
        self.log.emit(subprocess.list2cmdline(command))
        with self._lock:
            self._process = subprocess.Popen(
                command,
                cwd=str(cwd) if cwd else None,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                shell=False,
                **hidden_subprocess_kwargs(),
            )
        assert self._process.stdout is not None
        for line in self._process.stdout:
            cleaned = line.rstrip()
            if cleaned:
                self.log.emit(cleaned)
        return self._process.wait()
