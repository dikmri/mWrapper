from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from ..constants import APP_VERSION
from ..services.updater import (
    auto_update_enabled,
    current_exe_name,
    current_install_dir,
    download_update_asset,
    fetch_latest_update_info,
    is_frozen_app,
    launch_update_replacer,
    make_update_temp_dir,
)


@dataclass(frozen=True, slots=True)
class UpdateWorkerResult:
    should_quit: bool
    update_started: bool = False
    update_available: bool = False
    skipped: bool = False
    error: str | None = None
    latest_tag: str | None = None


class UpdateWorker(QThread):
    log = Signal(str)
    progress = Signal(int, int)
    finished_update = Signal(object)

    def run(self) -> None:
        if not auto_update_enabled():
            self.finished_update.emit(UpdateWorkerResult(should_quit=False, skipped=True))
            return

        if not is_frozen_app():
            self.finished_update.emit(UpdateWorkerResult(should_quit=False, skipped=True))
            return

        temp_root: Path | None = None
        try:
            self.log.emit("自動アップデート確認: 最新リリースを確認しています。")
            update = fetch_latest_update_info(APP_VERSION)
            if update is None:
                self.finished_update.emit(UpdateWorkerResult(should_quit=False))
                return

            temp_root = make_update_temp_dir()
            zip_path = temp_root / update.asset.name
            self.log.emit(f"自動アップデート確認: {update.tag_name} が見つかりました。")
            self.log.emit("自動アップデート: 更新ファイルをダウンロードしています。")

            next_report = 0

            def on_progress(downloaded: int, total: int) -> None:
                nonlocal next_report
                self.progress.emit(downloaded, total)
                if total <= 0:
                    return
                percent = int(downloaded * 100 / total)
                if percent >= next_report:
                    self.log.emit(f"自動アップデート進捗: {percent}%")
                    next_report += 10

            download_update_asset(update, zip_path, on_progress)
            self.log.emit("自動アップデート: ダウンロードが完了しました。")
            self.log.emit("自動アップデート: アプリを終了し、更新後に自動で再起動します。")

            launch_update_replacer(
                zip_path=zip_path,
                install_dir=current_install_dir(),
                exe_name=current_exe_name(),
                wait_pid=os.getpid(),
                temp_root=temp_root,
            )
            temp_root = None
            self.finished_update.emit(
                UpdateWorkerResult(
                    should_quit=True,
                    update_started=True,
                    update_available=True,
                    latest_tag=update.tag_name,
                )
            )
        except Exception as exc:
            if temp_root is not None:
                shutil.rmtree(temp_root, ignore_errors=True)
            self.finished_update.emit(
                UpdateWorkerResult(
                    should_quit=False,
                    update_available=True,
                    error=str(exc),
                )
            )
