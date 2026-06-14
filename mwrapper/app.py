from __future__ import annotations

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from .constants import APP_ICON_PATH, APP_NAME
from .ui.main_window import MainWindow


def run(argv: list[str]) -> int:
    app = QApplication(argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("mWrapper")
    if APP_ICON_PATH.exists():
        app.setWindowIcon(QIcon(str(APP_ICON_PATH)))

    window = MainWindow()
    window.resize(1180, 780)
    window.show()

    return app.exec()
