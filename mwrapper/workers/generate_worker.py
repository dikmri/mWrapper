from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from ..core.jobs import GenerateJob, GenerateResult
from ..services.mmaudio_runner import MMAudioRunner


class GenerateWorker(QThread):
    log = Signal(str)
    finished_result = Signal(object)

    def __init__(self, job: GenerateJob, parent=None) -> None:
        super().__init__(parent)
        self.job = job
        self.runner = MMAudioRunner()

    def run(self) -> None:
        result: GenerateResult = self.runner.run(self.job, self.log.emit)
        self.finished_result.emit(result)

    def cancel(self) -> None:
        self.runner.cancel()
