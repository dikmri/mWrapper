from __future__ import annotations

import subprocess
import threading
from pathlib import Path

from PySide6.QtCore import QThread, Signal


class CommandWorker(QThread):
    log = Signal(str)
    finished_command = Signal(int)

    def __init__(self, command: list[str], cwd: Path | None = None, parent=None) -> None:
        super().__init__(parent)
        self.command = command
        self.cwd = cwd
        self._process: subprocess.Popen[str] | None = None
        self._lock = threading.Lock()

    def run(self) -> None:
        try:
            self.log.emit(subprocess.list2cmdline(self.command))
            with self._lock:
                self._process = subprocess.Popen(
                    self.command,
                    cwd=str(self.cwd) if self.cwd else None,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    shell=False,
                )
            assert self._process.stdout is not None
            for line in self._process.stdout:
                cleaned = line.rstrip()
                if cleaned:
                    self.log.emit(cleaned)
            return_code = self._process.wait()
        except Exception as exc:
            self.log.emit(f"エラー: {exc}")
            return_code = 1
        finally:
            with self._lock:
                self._process = None
        self.finished_command.emit(return_code)

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
