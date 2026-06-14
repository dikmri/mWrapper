from __future__ import annotations

import subprocess
import threading
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from ..services.hardware import format_hardware_info, inspect_hardware
from ..services.mmaudio_downloader import download_mmaudio_repository
from ..services.model_assets import download_nsfw_mmaudio_model
from ..services.package_installer import (
    PyTorchInstallSpec,
    build_mmaudio_venv_commands,
    build_uv_bootstrap_commands,
    find_uv,
    select_pytorch_install_spec,
)
from ..services.subprocess_utils import hidden_subprocess_kwargs


class AutoSetupWorker(QThread):
    log = Signal(str)
    finished_auto_setup = Signal(int, object, object)

    def __init__(
        self,
        tools_dir: Path,
        venv_dir: Path,
        base_python: Path | None,
        *,
        rebuild_venv: bool,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.tools_dir = tools_dir
        self.venv_dir = venv_dir
        self.base_python = base_python
        self.rebuild_venv = rebuild_venv
        self._process: subprocess.Popen[str] | None = None
        self._lock = threading.Lock()
        self._cancelled = False

    def run(self) -> None:
        venv_python = self.venv_dir / "Scripts" / "python.exe"
        try:
            self.log.emit("セットアップ: ハードウェア情報を確認しています。")
            hardware = inspect_hardware()
            self.log.emit(format_hardware_info(hardware))
            pytorch_spec = select_pytorch_install_spec(hardware)
            self.log.emit(
                f"PyTorch構成選択: {pytorch_spec.label} / index: {pytorch_spec.index_url}"
            )

            self.log.emit("セットアップ: MMAudio本体を確認しています。")
            demo_path = download_mmaudio_repository(self.tools_dir, self.log.emit)
            mmaudio_dir = demo_path.parent
            self.log.emit("セットアップ: NSFW_MMaudioモデルを確認しています。")
            download_nsfw_mmaudio_model(mmaudio_dir, self.log.emit)

            if self.rebuild_venv:
                if self.base_python is None:
                    raise RuntimeError("Python 3.10-3.12 が見つかりませんでした。")
                self.log.emit("セットアップ: MMAudio専用Python環境を構築しています。")
                return_code = self._setup_venv(self.base_python, mmaudio_dir, pytorch_spec)
                if return_code != 0:
                    self.finished_auto_setup.emit(return_code, None, None)
                    return
            elif not venv_python.exists():
                raise RuntimeError(f"専用venvのPythonが見つかりません: {venv_python}")

            self.log.emit("セットアップ: 完了しました。")
            self.finished_auto_setup.emit(0, demo_path, venv_python)
        except Exception as exc:
            self.log.emit(f"自動セットアップエラー: {exc}")
            self.finished_auto_setup.emit(1, None, None)
        finally:
            with self._lock:
                self._process = None

    def cancel(self) -> None:
        self._cancelled = True
        with self._lock:
            process = self._process
        if process is None or process.poll() is not None:
            return
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()

    def _setup_venv(
        self,
        base_python: Path,
        mmaudio_dir: Path,
        pytorch_spec: PyTorchInstallSpec,
    ) -> int:
        venv_python = self.venv_dir / "Scripts" / "python.exe"
        self.venv_dir.parent.mkdir(parents=True, exist_ok=True)
        uv_path, return_code = self._ensure_uv(base_python)
        if return_code != 0 or uv_path is None:
            return return_code or 1

        self.log.emit("uvを使ってMMAudio専用venvを構築します。")
        commands = build_mmaudio_venv_commands(
            uv_path=uv_path,
            base_python=base_python,
            venv_dir=self.venv_dir,
            venv_python=venv_python,
            mmaudio_dir=mmaudio_dir,
            pytorch_spec=pytorch_spec,
        )
        for command, cwd in commands:
            if self._cancelled:
                return 1
            return_code = self._run_command(command, cwd)
            if return_code != 0:
                return return_code
        return 0

    def _ensure_uv(self, base_python: Path) -> tuple[str | None, int]:
        uv_path = find_uv(self.venv_dir.parent)
        if uv_path:
            self.log.emit(f"uv確認: 利用可能 / {uv_path}")
            return uv_path, 0

        self.log.emit("uv確認: 見つからないため、セットアップ先にuvを導入します。")
        for command, cwd in build_uv_bootstrap_commands(base_python, self.venv_dir.parent):
            if self._cancelled:
                return None, 1
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
