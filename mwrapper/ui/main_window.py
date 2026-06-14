from __future__ import annotations

import os
import uuid
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QCloseEvent, QDesktopServices, QIcon, QTextOption
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QProgressBar,
    QSizePolicy,
    QSplitter,
    QDoubleSpinBox,
    QStyle,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ..constants import APP_ICON_PATH, APP_NAME, DEFAULT_MODEL_ID
from ..core.config import AppConfig, ConfigManager
from ..core.jobs import GenerateJob, GenerateResult
from ..core.paths import default_venvs_dir
from ..services.cuda_environment import format_cuda_info, inspect_python_cuda
from ..services.ffmpeg import FFprobeError, VideoInfo, find_tool
from ..services.log_formatter import format_log_line
from ..services.mmaudio_dependencies import (
    format_mmaudio_dependency_info,
    inspect_mmaudio_dependencies,
)
from ..services.output_manager import save_generated_video
from ..services.package_installer import (
    PYTORCH_CUDA_LABEL,
    build_cuda_torch_install_command,
    build_mmaudio_dependency_repair_command,
)
from ..services.python_env import choose_mmaudio_base_python
from ..services.video_service import UnsupportedVideoError, VideoService
from ..workers.command_worker import CommandWorker
from ..workers.generate_worker import GenerateWorker
from ..workers.mmaudio_env_setup_worker import MMAudioEnvSetupWorker
from ..workers.mmaudio_download_worker import MMAudioDownloadWorker
from .preview_player import PreviewPlayer
from .widgets.drop_area import DropArea


MIN_GENERATION_DURATION = 0.1
MAX_GENERATION_DURATION = 24 * 60 * 60.0


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v0.1")
        if APP_ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(APP_ICON_PATH)))

        self.config_manager = ConfigManager()
        self.config = self.config_manager.load()
        ConfigManager.ensure_runtime_dirs(self.config)

        self.current_video_path: Path | None = None
        self.current_video_info: VideoInfo | None = None
        self.generated_video_path: Path | None = None
        self.worker: GenerateWorker | None = None
        self.download_worker: MMAudioDownloadWorker | None = None
        self.command_worker: CommandWorker | None = None
        self.env_setup_worker: MMAudioEnvSetupWorker | None = None

        self._build_ui()
        self._load_config_to_ui()
        self._update_button_state()

    def _build_ui(self) -> None:
        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setSpacing(10)

        root_layout.addWidget(self._build_paths_group())

        content_splitter = QSplitter(Qt.Orientation.Horizontal)
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self.drop_area = DropArea()
        self.drop_area.file_dropped.connect(self.load_video)
        self.drop_area.mousePressEvent = lambda event: self._choose_video()
        left_layout.addWidget(self.drop_area)
        left_layout.addWidget(self._build_video_info_group())
        left_layout.addWidget(self._build_prompt_group())
        left_layout.addWidget(self._build_generation_group())

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        preview_group = QGroupBox("プレビュー")
        preview_layout = QVBoxLayout(preview_group)
        self.preview = PreviewPlayer()
        preview_layout.addWidget(self.preview)
        right_layout.addWidget(preview_group, 2)
        right_layout.addWidget(self._build_log_group(), 1)

        content_splitter.addWidget(left)
        content_splitter.addWidget(right)
        content_splitter.setStretchFactor(0, 2)
        content_splitter.setStretchFactor(1, 3)
        root_layout.addWidget(content_splitter, 1)

        self.setCentralWidget(root)
        self.statusBar().showMessage("Ready")

    def _build_paths_group(self) -> QGroupBox:
        group = QGroupBox("実行設定")
        layout = QGridLayout(group)

        self.demo_script_edit = QLineEdit()
        self.demo_script_edit.setPlaceholderText("MMAudio の demo.py を指定")
        browse_script = self._tool_button(QStyle.SP_DirOpenIcon, "demo.py を選択")
        browse_script.clicked.connect(self._choose_demo_script)
        self.download_mmaudio_button = QPushButton("MMAudio取得")
        self.download_mmaudio_button.setToolTip("公式GitHubからMMAudio本体を取得して demo.py を設定")
        self.download_mmaudio_button.clicked.connect(self.start_mmaudio_download)

        self.python_executable_edit = QLineEdit()
        self.python_executable_edit.setPlaceholderText("CUDA版PyTorchを入れた Python を指定")
        browse_python = self._tool_button(QStyle.SP_DirOpenIcon, "Python 実行ファイルを選択")
        browse_python.clicked.connect(self._choose_python_executable)

        self.check_cuda_button = QPushButton("CUDA確認")
        self.check_cuda_button.clicked.connect(lambda: self._check_cuda_environment(show_message=True))

        self.install_cuda_torch_button = QPushButton("CUDA PyTorch導入")
        self.install_cuda_torch_button.setToolTip(
            f"uv優先で、選択中のMMAudio Pythonへ{PYTORCH_CUDA_LABEL}版PyTorchを導入"
        )
        self.install_cuda_torch_button.clicked.connect(self.install_cuda_pytorch)

        self.check_dependencies_button = QPushButton("MMAudio依存確認")
        self.check_dependencies_button.clicked.connect(
            lambda: self._check_mmaudio_dependencies(show_message=True)
        )

        self.repair_dependencies_button = QPushButton("MMAudio依存修復")
        self.repair_dependencies_button.setToolTip(
            "uv優先でMMAudioをeditable installし、NumPyをMMAudio互換の <2.1 に調整します"
        )
        self.repair_dependencies_button.clicked.connect(self.repair_mmaudio_dependencies)

        self.create_venv_button = QPushButton("専用venv作成")
        self.create_venv_button.setToolTip(
            "uv優先でMMAudio専用venvを作成し、CUDA版PyTorchと依存関係を導入します"
        )
        self.create_venv_button.clicked.connect(self.create_mmaudio_venv)

        self.mmaudio_output_edit = QLineEdit()
        self.mmaudio_output_edit.setPlaceholderText("空欄なら demo.py と作業フォルダ配下の output を検索")
        browse_mmaudio_output = self._tool_button(QStyle.SP_DirOpenIcon, "MMAudio 出力フォルダを選択")
        browse_mmaudio_output.clicked.connect(
            lambda: self._choose_directory(self.mmaudio_output_edit)
        )

        self.save_dir_edit = QLineEdit()
        browse_save = self._tool_button(QStyle.SP_DirOpenIcon, "保存先フォルダを選択")
        browse_save.clicked.connect(lambda: self._choose_directory(self.save_dir_edit))

        layout.addWidget(QLabel("MMAudio demo.py"), 0, 0)
        layout.addWidget(self.demo_script_edit, 0, 1)
        layout.addWidget(browse_script, 0, 2)
        layout.addWidget(self.download_mmaudio_button, 0, 3)
        layout.addWidget(QLabel("MMAudio Python"), 1, 0)
        layout.addWidget(self.python_executable_edit, 1, 1)
        layout.addWidget(browse_python, 1, 2)
        layout.addWidget(self.check_cuda_button, 1, 3)
        layout.addWidget(self.install_cuda_torch_button, 1, 4)
        layout.addWidget(self.create_venv_button, 1, 5)
        layout.addWidget(QLabel("MMAudio output"), 2, 0)
        layout.addWidget(self.mmaudio_output_edit, 2, 1)
        layout.addWidget(browse_mmaudio_output, 2, 2)
        layout.addWidget(self.check_dependencies_button, 2, 3)
        layout.addWidget(self.repair_dependencies_button, 2, 4)
        layout.addWidget(QLabel("保存先"), 3, 0)
        layout.addWidget(self.save_dir_edit, 3, 1)
        layout.addWidget(browse_save, 3, 2)
        layout.setColumnStretch(1, 1)
        return group

    def _build_video_info_group(self) -> QGroupBox:
        group = QGroupBox("入力動画情報")
        layout = QFormLayout(group)
        self.video_info_labels: dict[str, QLabel] = {}
        for key, caption in (
            ("file_name", "ファイル名"),
            ("path", "フルパス"),
            ("duration", "長さ"),
            ("resolution", "解像度"),
            ("fps", "FPS"),
            ("codec", "コーデック"),
            ("audio", "音声"),
            ("size", "サイズ"),
        ):
            label = QLabel("-")
            label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            label.setWordWrap(True)
            self.video_info_labels[key] = label
            layout.addRow(caption, label)
        return group

    def _build_prompt_group(self) -> QGroupBox:
        group = QGroupBox("英語プロンプト")
        layout = QVBoxLayout(group)
        self.prompt_edit = QPlainTextEdit()
        self.prompt_edit.setPlaceholderText("例: breathing, bed creaks, cloth rustling, room ambience")
        self.prompt_edit.setFixedHeight(96)
        self.prompt_edit.textChanged.connect(self._update_button_state)
        layout.addWidget(self.prompt_edit)
        return group

    def _build_generation_group(self) -> QGroupBox:
        group = QGroupBox("生成")
        layout = QVBoxLayout(group)
        settings_layout = QHBoxLayout()
        self.duration_spin = QDoubleSpinBox()
        self.duration_spin.setRange(MIN_GENERATION_DURATION, MAX_GENERATION_DURATION)
        self.duration_spin.setDecimals(2)
        self.duration_spin.setSingleStep(0.1)
        self.duration_spin.setSuffix(" sec")
        settings_layout.addWidget(QLabel("duration"))
        settings_layout.addWidget(self.duration_spin)
        self.require_cuda_checkbox = QCheckBox("CUDA必須")
        self.require_cuda_checkbox.setToolTip(
            "オンの場合、CUDA版PyTorchが使えない環境ではCPU生成を開始しません"
        )
        settings_layout.addWidget(self.require_cuda_checkbox)
        settings_layout.addStretch(1)
        layout.addLayout(settings_layout)

        button_layout = QHBoxLayout()
        self.generate_button = QPushButton("生成")
        self.generate_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.generate_button.clicked.connect(self.start_generation)

        self.stop_button = QPushButton("停止")
        self.stop_button.setIcon(self.style().standardIcon(QStyle.SP_MediaStop))
        self.stop_button.clicked.connect(self.stop_generation)

        self.save_button = QPushButton("保存")
        self.save_button.setIcon(self.style().standardIcon(QStyle.SP_DialogSaveButton))
        self.save_button.clicked.connect(self.save_result)

        self.open_save_dir_button = QPushButton("保存先を開く")
        self.open_save_dir_button.setIcon(self.style().standardIcon(QStyle.SP_DirOpenIcon))
        self.open_save_dir_button.clicked.connect(self.open_save_dir)

        for button in (
            self.generate_button,
            self.stop_button,
            self.save_button,
            self.open_save_dir_button,
        ):
            button_layout.addWidget(button)
        button_layout.addStretch(1)
        layout.addLayout(button_layout)

        self.progress = QProgressBar()
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        layout.addWidget(self.progress)
        return group

    def _build_log_group(self) -> QGroupBox:
        group = QGroupBox("ログ")
        layout = QVBoxLayout(group)
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.document().setMaximumBlockCount(1200)
        self.log_view.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.log_view.setWordWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        self.log_view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.log_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.log_view)
        return group

    def _load_config_to_ui(self) -> None:
        self.demo_script_edit.setText(self.config.mmaudio.demo_script_path)
        self.python_executable_edit.setText(self.config.mmaudio.python_executable or "python")
        self.mmaudio_output_edit.setText(self.config.mmaudio.output_dir)
        self.save_dir_edit.setText(self.config.paths.output_dir)
        self.duration_spin.setValue(_generation_duration_value(self.config.generation.default_duration))
        self.require_cuda_checkbox.setChecked(self.config.generation.require_cuda)

    def _save_ui_to_config(self) -> None:
        self.config.mmaudio.demo_script_path = self.demo_script_edit.text().strip()
        self.config.mmaudio.python_executable = self.python_executable_edit.text().strip() or "python"
        self.config.mmaudio.output_dir = self.mmaudio_output_edit.text().strip()
        self.config.paths.output_dir = self.save_dir_edit.text().strip()
        self.config.generation.default_duration = float(self.duration_spin.value())
        self.config.generation.require_cuda = self.require_cuda_checkbox.isChecked()
        self.config_manager.save(self.config)
        ConfigManager.ensure_runtime_dirs(self.config)

    def load_video(self, path: Path) -> None:
        ffprobe = find_tool(self.config.paths.ffprobe_path, "ffprobe")
        service = VideoService(ffprobe)

        try:
            info = service.probe(path)
        except (UnsupportedVideoError, FFprobeError) as exc:
            self._show_error("動画を読み込めません", str(exc))
            return

        self.current_video_path = path
        self.current_video_info = info
        self.generated_video_path = None
        self.drop_area.set_file_name(path.name)
        self.preview.set_source(path)
        self._display_video_info(info)
        self._sync_duration_to_video(info.duration)
        self._append_log(f"Loaded video: {path}")
        self._update_button_state()

    def start_mmaudio_download(self) -> None:
        if self.download_worker is not None and self.download_worker.isRunning():
            return
        if self.worker is not None and self.worker.isRunning():
            return
        if self.command_worker is not None and self.command_worker.isRunning():
            return
        if self.env_setup_worker is not None and self.env_setup_worker.isRunning():
            return

        self._save_ui_to_config()
        self.log_view.clear()
        self._set_downloading(True)

        self.download_worker = MMAudioDownloadWorker(Path(self.config.paths.tools_dir), self)
        self.download_worker.log.connect(self._append_log)
        self.download_worker.finished_download.connect(self._mmaudio_download_finished)
        self.download_worker.finished.connect(lambda: self._set_downloading(False))
        self.download_worker.start()

    def start_generation(self) -> None:
        if self.worker is not None and self.worker.isRunning():
            return
        if self.command_worker is not None and self.command_worker.isRunning():
            return
        if self.env_setup_worker is not None and self.env_setup_worker.isRunning():
            return
        if self.current_video_path is None:
            self._show_error("入力エラー", "動画を選択してください。")
            return

        prompt = self.prompt_edit.toPlainText().strip()
        if not prompt:
            self._show_error("入力エラー", "英語プロンプトを入力してください。")
            return

        demo_script = Path(self.demo_script_edit.text().strip())
        if not demo_script.exists():
            self._show_error("設定エラー", "MMAudio の demo.py を指定してください。")
            return

        if self.require_cuda_checkbox.isChecked() and not self._check_cuda_environment(show_message=False):
            self._show_error(
                "CUDA設定エラー",
                "選択中のMMAudio PythonではCUDA版PyTorchを利用できません。\n"
                "CUDA PyTorch導入を実行するか、CUDA対応済みのPythonを指定してください。",
            )
            return
        if not self._check_mmaudio_dependencies(show_message=False):
            self._show_error(
                "MMAudio依存エラー",
                "MMAudioのPython依存関係に問題があります。\n"
                "MMAudio依存修復を実行してから再試行してください。",
            )
            return

        if self.current_video_info and self.current_video_info.duration:
            if self.current_video_info.duration > 8:
                answer = QMessageBox.question(
                    self,
                    "長尺動画の確認",
                    "この動画は8秒を超えています。\n"
                    "MMAudioは8秒前後の生成を基本としているため、"
                    "長尺動画では品質が不安定になる可能性があります。\n"
                    "このまま生成しますか?",
                )
                if answer != QMessageBox.StandardButton.Yes:
                    return

        self._save_ui_to_config()
        self.generated_video_path = None
        self.preview.set_source(self.current_video_path)
        self._set_running(True)
        self.log_view.clear()

        job_id = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:8]
        temp_dir = Path(self.config.paths.temp_dir) / job_id
        mmaudio_output = (
            Path(self.config.mmaudio.output_dir)
            if self.config.mmaudio.output_dir.strip()
            else None
        )
        search_dirs = [temp_dir]
        if mmaudio_output is not None:
            search_dirs.append(mmaudio_output)

        job = GenerateJob(
            job_id=job_id,
            input_video_path=self.current_video_path,
            japanese_prompt="",
            english_prompt=prompt,
            seed=None,
            duration=float(self.duration_spin.value()),
            model_id=DEFAULT_MODEL_ID,
            output_dir=temp_dir,
            created_at=datetime.now(),
            python_executable=self.config.mmaudio.python_executable or "python",
            mmaudio_script_path=demo_script,
            mmaudio_working_dir=demo_script.parent,
            mmaudio_output_dir=mmaudio_output,
            search_dirs=search_dirs,
            extra_args=list(self.config.mmaudio.extra_args),
            require_cuda=self.config.generation.require_cuda,
        )

        self.worker = GenerateWorker(job, self)
        self.worker.log.connect(self._append_log)
        self.worker.finished_result.connect(self._generation_finished)
        self.worker.finished.connect(lambda: self._set_running(False))
        self.worker.start()

    def _mmaudio_download_finished(self, demo_path: object, error: object) -> None:
        if error:
            self._append_log(f"MMAudio download failed: {error}")
            self._show_error("MMAudio取得エラー", str(error))
            return

        path = Path(str(demo_path))
        self.demo_script_edit.setText(str(path))
        self.mmaudio_output_edit.setText(str(path.parent / "output"))
        self._save_ui_to_config()
        self._append_log(f"Configured demo.py: {path}")
        QMessageBox.information(
            self,
            "MMAudio取得完了",
            "MMAudio本体を取得し、demo.py を設定しました。\n"
            "必要なPython依存関係とモデル重みはMMAudio側の手順に従って導入してください。",
        )

    def stop_generation(self) -> None:
        if self.worker is not None and self.worker.isRunning():
            self._append_log("Cancelling generation...")
            self.worker.cancel()
        if self.command_worker is not None and self.command_worker.isRunning():
            self._append_log("実行中のセットアップコマンドを停止しています...")
            self.command_worker.cancel()
        if self.env_setup_worker is not None and self.env_setup_worker.isRunning():
            self._append_log("MMAudio専用venv作成を停止しています...")
            self.env_setup_worker.cancel()

    def install_cuda_pytorch(self) -> None:
        if self.worker is not None and self.worker.isRunning():
            return
        if self.download_worker is not None and self.download_worker.isRunning():
            return
        if self.command_worker is not None and self.command_worker.isRunning():
            return
        if self.env_setup_worker is not None and self.env_setup_worker.isRunning():
            return

        self._save_ui_to_config()
        python_executable = self.config.mmaudio.python_executable or "python"
        command = build_cuda_torch_install_command(python_executable)
        answer = QMessageBox.question(
            self,
            "CUDA PyTorch導入",
            f"選択中のMMAudio Python環境に{PYTORCH_CUDA_LABEL}版PyTorchを導入します。\n"
            "既存のtorch/torchvision/torchaudioは再インストールされます。\n\n"
            "uvが利用できる場合はuvで導入するため、pipが無いvenvでも実行できます。\n"
            "グローバルPythonを選んでいる場合はその環境を変更します。\n"
            "通常は先に「専用venv作成」を使うことを推奨します。\n\n"
            f"Python: {python_executable}\n\n"
            "続行しますか?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        self.command_worker = CommandWorker(command, self._mmaudio_working_dir_or_none(), self)
        self.command_worker.log.connect(self._append_log)
        self.command_worker.finished_command.connect(self._cuda_pytorch_install_finished)
        self.command_worker.finished.connect(lambda: self._set_installing(False))
        self.log_view.clear()
        self._set_installing(True)
        self.command_worker.start()

    def repair_mmaudio_dependencies(self) -> None:
        if self.worker is not None and self.worker.isRunning():
            return
        if self.download_worker is not None and self.download_worker.isRunning():
            return
        if self.command_worker is not None and self.command_worker.isRunning():
            return

        self._save_ui_to_config()
        python_executable = self.config.mmaudio.python_executable or "python"
        working_dir = self._mmaudio_working_dir_or_none()
        if working_dir is None:
            self._show_error("MMAudio依存修復エラー", "MMAudio の demo.py を先に指定してください。")
            return

        command = build_mmaudio_dependency_repair_command(python_executable)
        answer = QMessageBox.question(
            self,
            "MMAudio依存修復",
            "選択中のMMAudio Python環境で依存関係を修復します。\n"
            "MMAudioをeditable installし、NumPyをMMAudio互換の <2.1 に調整します。\n\n"
            "uvが利用できる場合はuvで導入するため、pipが無いvenvでも実行できます。\n"
            "グローバルPythonを選んでいる場合はその環境を変更します。\n"
            "通常は先に「専用venv作成」を使うことを推奨します。\n\n"
            f"Python: {python_executable}\n"
            f"MMAudio: {working_dir}\n\n"
            "続行しますか?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        self.command_worker = CommandWorker(command, working_dir, self)
        self.command_worker.log.connect(self._append_log)
        self.command_worker.finished_command.connect(self._mmaudio_dependency_repair_finished)
        self.command_worker.finished.connect(lambda: self._set_installing(False))
        self.log_view.clear()
        self._set_installing(True)
        self.command_worker.start()

    def create_mmaudio_venv(self) -> None:
        if self.worker is not None and self.worker.isRunning():
            return
        if self.download_worker is not None and self.download_worker.isRunning():
            return
        if self.command_worker is not None and self.command_worker.isRunning():
            return
        if self.env_setup_worker is not None and self.env_setup_worker.isRunning():
            return

        self._save_ui_to_config()
        working_dir = self._mmaudio_working_dir_or_none()
        if working_dir is None:
            self._show_error("専用venv作成エラー", "MMAudio の demo.py を先に指定してください。")
            return

        base_python = choose_mmaudio_base_python()
        if base_python is None:
            self._show_error(
                "専用venv作成エラー",
                "Python 3.10-3.12 が見つかりませんでした。\n"
                "MMAudio用にPython 3.10/3.11/3.12を導入してください。",
            )
            return

        venv_dir = default_venvs_dir() / "mmaudio"
        answer = QMessageBox.question(
            self,
            "MMAudio専用venv作成",
            "MMAudio専用の仮想環境を作成し、CUDA版PyTorchとMMAudio依存関係を導入します。\n"
            "uvが利用できる場合はuvを使い、なければvenv+pipにフォールバックします。\n"
            "既存の専用venvがある場合はクリアして作り直します。\n"
            "他のPython環境を汚さないため、この方法を推奨します。\n\n"
            f"Base Python: {base_python.path}\n"
            f"venv: {venv_dir}\n"
            f"MMAudio: {working_dir}\n\n"
            "続行しますか?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        self.env_setup_worker = MMAudioEnvSetupWorker(base_python.path, venv_dir, working_dir, self)
        self.env_setup_worker.log.connect(self._append_log)
        self.env_setup_worker.finished_setup.connect(self._mmaudio_venv_setup_finished)
        self.env_setup_worker.finished.connect(lambda: self._set_installing(False))
        self.log_view.clear()
        self._set_installing(True)
        self.env_setup_worker.start()

    def save_result(self) -> None:
        if self.generated_video_path is None or self.current_video_path is None:
            return
        try:
            saved = save_generated_video(
                self.generated_video_path,
                self.current_video_path,
                Path(self.save_dir_edit.text().strip()),
            )
        except OSError as exc:
            self._show_error("保存エラー", str(exc))
            return
        self._append_log(f"Saved: {saved}")
        QMessageBox.information(self, "保存完了", f"保存しました。\n{saved}")

    def open_save_dir(self) -> None:
        path = Path(self.save_dir_edit.text().strip())
        path.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def _generation_finished(self, result: GenerateResult) -> None:
        if result.success and result.output_video_path is not None:
            self.generated_video_path = result.output_video_path
            self.preview.set_source(result.output_video_path)
            self._append_log(f"Generation completed: {result.output_video_path}")
            QMessageBox.information(
                self,
                "生成完了",
                "生成が完了しました。\nプレビューで確認し、問題なければ保存してください。",
            )
        else:
            self.generated_video_path = None
            self._append_log(f"Generation failed: {result.error_message}")
            self._show_error(
                "生成エラー",
                result.error_message or "生成に失敗しました。ログを確認してください。",
            )
        self._update_button_state()

    def _set_running(self, running: bool) -> None:
        if running:
            self.progress.setRange(0, 0)
            self.statusBar().showMessage("Generating...")
        else:
            self.progress.setRange(0, 1)
            self.progress.setValue(0)
            self.statusBar().showMessage("Ready")
        self._update_button_state(running)

    def _set_downloading(self, downloading: bool) -> None:
        if downloading:
            self.progress.setRange(0, 0)
            self.statusBar().showMessage("Downloading MMAudio...")
        else:
            self.progress.setRange(0, 1)
            self.progress.setValue(0)
            self.statusBar().showMessage("Ready")
        self._update_button_state()

    def _set_installing(self, installing: bool) -> None:
        if installing:
            self.progress.setRange(0, 0)
            self.statusBar().showMessage("Running setup command...")
        else:
            self.progress.setRange(0, 1)
            self.progress.setValue(0)
            self.statusBar().showMessage("Ready")
        self._update_button_state()

    def _update_button_state(self, running: bool | None = None) -> None:
        if running is None:
            running = self.worker is not None and self.worker.isRunning()
        downloading = self.download_worker is not None and self.download_worker.isRunning()
        installing = self.command_worker is not None and self.command_worker.isRunning()
        setting_up_env = self.env_setup_worker is not None and self.env_setup_worker.isRunning()
        busy = running or downloading or installing or setting_up_env
        has_video = self.current_video_path is not None
        has_prompt = bool(self.prompt_edit.toPlainText().strip())
        has_result = self.generated_video_path is not None
        self.generate_button.setEnabled(has_video and has_prompt and not busy)
        self.stop_button.setEnabled(running or installing or setting_up_env)
        self.save_button.setEnabled(has_result and not busy)
        self.open_save_dir_button.setEnabled(not busy)
        self.download_mmaudio_button.setEnabled(not busy)
        self.check_cuda_button.setEnabled(not busy)
        self.install_cuda_torch_button.setEnabled(not busy)
        self.check_dependencies_button.setEnabled(not busy)
        self.repair_dependencies_button.setEnabled(not busy)
        self.create_venv_button.setEnabled(not busy)

    def _display_video_info(self, info: VideoInfo) -> None:
        self.video_info_labels["file_name"].setText(info.path.name)
        self.video_info_labels["path"].setText(str(info.path))
        self.video_info_labels["duration"].setText(_format_seconds(info.duration))
        resolution = "-"
        if info.width and info.height:
            resolution = f"{info.width} x {info.height}"
        self.video_info_labels["resolution"].setText(resolution)
        self.video_info_labels["fps"].setText(
            f"{info.fps:.3f}" if info.fps is not None else "-"
        )
        video_codec = info.video_codec or "-"
        audio_codec = info.audio_codec or "なし"
        self.video_info_labels["codec"].setText(f"video: {video_codec} / audio: {audio_codec}")
        self.video_info_labels["audio"].setText(
            f"{info.audio_stream_count} track(s)" if info.audio_stream_count else "なし"
        )
        self.video_info_labels["size"].setText(_format_bytes(info.file_size))

    def _sync_duration_to_video(self, duration: float | None) -> None:
        if duration is None or duration <= 0:
            return
        generation_duration = _generation_duration_value(duration)
        self.duration_spin.setValue(generation_duration)
        self._append_log(
            f"動画の長さに合わせて duration を設定しました: {generation_duration:g} sec"
        )

    def _choose_video(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "動画を選択",
            "",
            "Video Files (*.mp4 *.mov *.mkv *.webm *.avi)",
        )
        if path:
            self.load_video(Path(path))

    def _choose_demo_script(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "MMAudio demo.py を選択",
            "",
            "Python Files (*.py)",
        )
        if path:
            self.demo_script_edit.setText(path)

    def _choose_python_executable(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Python 実行ファイルを選択",
            "",
            "Python Executable (python.exe python*.exe *.bat *.cmd);;All Files (*)",
        )
        if path:
            self.python_executable_edit.setText(path)

    def _choose_directory(self, target: QLineEdit) -> None:
        directory = QFileDialog.getExistingDirectory(
            self,
            "フォルダを選択",
            target.text().strip() or os.getcwd(),
        )
        if directory:
            target.setText(directory)

    def _append_log(self, message: str) -> None:
        formatted = format_log_line(message)
        if not formatted:
            return
        self.log_view.append(formatted)
        vertical_scrollbar = self.log_view.verticalScrollBar()
        vertical_scrollbar.setValue(vertical_scrollbar.maximum())

    def _check_cuda_environment(self, show_message: bool) -> bool:
        self._save_ui_to_config()
        info = inspect_python_cuda(
            self.config.mmaudio.python_executable or "python",
            self._mmaudio_working_dir_or_none(),
        )
        message = format_cuda_info(info)
        self._append_log(message)
        if show_message:
            QMessageBox.information(self, "CUDA確認", message)
        return info.cuda_usable

    def _check_mmaudio_dependencies(self, show_message: bool) -> bool:
        self._save_ui_to_config()
        info = inspect_mmaudio_dependencies(
            self.config.mmaudio.python_executable or "python",
            self._mmaudio_working_dir_or_none(),
        )
        message = format_mmaudio_dependency_info(info)
        self._append_log(message)
        if show_message:
            QMessageBox.information(self, "MMAudio依存確認", message)
        return info.ok

    def _cuda_pytorch_install_finished(self, return_code: int) -> None:
        if return_code == 0:
            self._append_log("CUDA PyTorch導入が完了しました。CUDA確認を実行します。")
            self._check_cuda_environment(show_message=True)
        else:
            self._append_log(f"CUDA PyTorch導入に失敗しました。終了コード: {return_code}")
            QMessageBox.warning(
                self,
                "CUDA PyTorch導入エラー",
                "CUDA版PyTorchの導入に失敗しました。ログを確認してください。",
            )

    def _mmaudio_dependency_repair_finished(self, return_code: int) -> None:
        if return_code == 0:
            self._append_log("MMAudio依存修復が完了しました。依存確認を実行します。")
            self._check_mmaudio_dependencies(show_message=True)
        else:
            self._append_log(f"MMAudio依存修復に失敗しました。終了コード: {return_code}")
            QMessageBox.warning(
                self,
                "MMAudio依存修復エラー",
                "MMAudio依存修復に失敗しました。ログを確認してください。",
            )

    def _mmaudio_venv_setup_finished(self, return_code: int, venv_python: object) -> None:
        if return_code == 0 and venv_python:
            path = Path(str(venv_python))
            self.python_executable_edit.setText(str(path))
            self._save_ui_to_config()
            self._append_log(f"MMAudio専用venvを設定しました: {path}")
            self._check_cuda_environment(show_message=False)
            self._check_mmaudio_dependencies(show_message=False)
            QMessageBox.information(
                self,
                "MMAudio専用venv作成完了",
                f"MMAudio専用venvを作成し、MMAudio Pythonに設定しました。\n{path}",
            )
        else:
            self._append_log(f"MMAudio専用venv作成に失敗しました。終了コード: {return_code}")
            QMessageBox.warning(
                self,
                "MMAudio専用venv作成エラー",
                "MMAudio専用venvの作成に失敗しました。ログを確認してください。",
            )

    def _mmaudio_working_dir_or_none(self) -> Path | None:
        raw = self.demo_script_edit.text().strip()
        if not raw:
            return None
        path = Path(raw)
        return path.parent if path.exists() else None

    def _show_error(self, title: str, message: str) -> None:
        QMessageBox.warning(self, title, message)

    def _tool_button(self, icon: QStyle.StandardPixmap, tooltip: str) -> QToolButton:
        button = QToolButton()
        button.setIcon(self.style().standardIcon(icon))
        button.setToolTip(tooltip)
        return button

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        if self.env_setup_worker is not None and self.env_setup_worker.isRunning():
            QMessageBox.information(
                self,
                "MMAudio専用venv作成中",
                "MMAudio専用venvの作成中です。完了してから終了してください。",
            )
            event.ignore()
            return
        if self.command_worker is not None and self.command_worker.isRunning():
            QMessageBox.information(
                self,
                "セットアップコマンド実行中",
                "セットアップコマンドの実行中です。完了してから終了してください。",
            )
            event.ignore()
            return
        if self.download_worker is not None and self.download_worker.isRunning():
            QMessageBox.information(
                self,
                "MMAudio取得中",
                "MMAudioの取得中です。完了してから終了してください。",
            )
            event.ignore()
            return
        if self.worker is not None and self.worker.isRunning():
            answer = QMessageBox.question(
                self,
                "生成中",
                "生成が実行中です。停止して終了しますか?",
            )
            if answer != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self.worker.cancel()
            self.worker.wait(5000)
        self._save_ui_to_config()
        event.accept()


def _format_seconds(value: float | None) -> str:
    if value is None:
        return "-"
    minutes, seconds = divmod(int(round(value)), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def _generation_duration_value(value: float | None) -> float:
    if value is None or value <= 0:
        return 8.0
    return round(min(max(float(value), MIN_GENERATION_DURATION), MAX_GENERATION_DURATION), 2)


def _format_bytes(value: int) -> str:
    size = float(value)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024
    return f"{value} B"
