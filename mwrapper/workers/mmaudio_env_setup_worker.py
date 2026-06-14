from __future__ import annotations

import subprocess
import threading
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from ..services.package_installer import (
    PyTorchInstallSpec,
    build_mmaudio_venv_commands,
    build_uv_bootstrap_commands,
    find_uv,
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
        return_code = 0
        try:
            self.venv_dir.parent.mkdir(parents=True, exist_ok=True)
            uv_path, return_code = self._ensure_uv()
            if return_code != 0 or uv_path is None:
                self.finished_setup.emit(return_code or 1, None)
                return
            commands = self._uv_commands(uv_path, venv_python)
            self.log.emit(
                f"PyTorch構成: {self.pytorch_spec.label} / index: {self.pytorch_spec.index_url}"
            )
            self.log.emit("uvを使ってMMAudio専用venvを構築します。")
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
        return build_mmaudio_venv_commands(
            uv_path=uv_path,
            base_python=self.base_python,
            venv_dir=self.venv_dir,
            venv_python=venv_python,
            mmaudio_dir=self.mmaudio_dir,
            pytorch_spec=self.pytorch_spec,
        )

    def _ensure_uv(self) -> tuple[str | None, int]:
        uv_path = find_uv(self.venv_dir.parent)
        if uv_path:
            self.log.emit(f"uv確認: 利用可能 / {uv_path}")
            return uv_path, 0

        self.log.emit("uv確認: 見つからないため、セットアップ先にuvを導入します。")
        for command, cwd in build_uv_bootstrap_commands(self.base_python, self.venv_dir.parent):
            return_code = self._run_command(command, cwd)
            if return_code != 0:
                self.log.emit(f"uv導入に失敗しました。終了コード: {return_code}")
                return None, return_code

        uv_path = find_uv(self.venv_dir.parent)
        if not uv_path:
            self.log.emit("uv導入後の実行ファイルを確認できませんでした。")
            return None, 1
        self.log.emit(f"uv導入完了: {uv_path}")
        return uv_path, 0

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
