from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, Signal

from ..services.mmaudio_downloader import download_mmaudio_repository


class MMAudioDownloadWorker(QThread):
    log = Signal(str)
    finished_download = Signal(object, object)

    def __init__(self, tools_dir: Path, parent=None) -> None:
        super().__init__(parent)
        self.tools_dir = tools_dir

    def run(self) -> None:
        try:
            demo_path = download_mmaudio_repository(self.tools_dir, self.log.emit)
        except Exception as exc:
            self.finished_download.emit(None, str(exc))
            return
        self.finished_download.emit(demo_path, None)
