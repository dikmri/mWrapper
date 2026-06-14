from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from ...constants import SUPPORTED_VIDEO_EXTENSIONS


class DropArea(QWidget):
    file_dropped = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMinimumHeight(120)
        self.setObjectName("DropArea")

        self._label = QLabel("ここに動画ファイルをドロップ\nまたはクリックして選択")
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.addWidget(self._label)

    def set_file_name(self, name: str | None) -> None:
        if name:
            self._label.setText(f"入力動画\n{name}")
        else:
            self._label.setText("ここに動画ファイルをドロップ\nまたはクリックして選択")

    def dragEnterEvent(self, event) -> None:  # noqa: N802
        if self._first_supported_file(event.mimeData()):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event) -> None:  # noqa: N802
        if self._first_supported_file(event.mimeData()):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event) -> None:  # noqa: N802
        path = self._first_supported_file(event.mimeData())
        if path is None:
            event.ignore()
            return
        event.acceptProposedAction()
        self.file_dropped.emit(path)

    @staticmethod
    def _first_supported_file(mime_data) -> Path | None:
        if not mime_data.hasUrls():
            return None
        for url in mime_data.urls():
            if not url.isLocalFile():
                continue
            path = Path(url.toLocalFile())
            if path.suffix.lower() in SUPPORTED_VIDEO_EXTENSIONS:
                return path
        return None
