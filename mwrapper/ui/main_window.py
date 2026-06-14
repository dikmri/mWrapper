from __future__ import annotations

import os
import random
import uuid
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QCloseEvent, QDesktopServices, QDragEnterEvent, QDropEvent, QIcon, QTextOption
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
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
    QSpinBox,
    QSizePolicy,
    QSplitter,
    QDoubleSpinBox,
    QStyle,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QApplication,
)

from ..constants import APP_ICON_PATH, APP_NAME, APP_VERSION, SUPPORTED_VIDEO_EXTENSIONS
from ..core.config import AppConfig, ConfigManager
from ..core.jobs import GenerateJob, GenerateResult
from ..services.cuda_environment import format_cuda_info, inspect_python_cuda
from ..services.ffmpeg import FFprobeError, VideoInfo, find_tool
from ..services.hardware import inspect_hardware
from ..services.log_formatter import format_log_line
from ..services.mmaudio_dependencies import (
    format_mmaudio_dependency_info,
    inspect_mmaudio_dependencies,
)
from ..services.mmaudio_demo_patch import patch_mmaudio_demo
from ..services.mmaudio_downloader import default_mmaudio_install_dir
from ..services.model_assets import (
    MODEL_CHOICES,
    nsfw_mmaudio_model_path,
    normalize_model_id,
)
from ..services.output_manager import save_generated_video
from ..services.package_installer import (
    PYTORCH_CUDA_LABEL,
    build_cuda_torch_install_command,
    build_mmaudio_dependency_repair_command,
    find_uv,
)
from ..services.python_env import choose_mmaudio_base_python
from ..services.setup_storage import (
    estimate_required_setup_bytes,
    format_bytes,
    free_bytes_for_path,
    inspect_setup_readiness,
    setup_paths_for_root,
)
from ..services.setup_chime import play_setup_complete_chime
from ..services.video_service import UnsupportedVideoError, VideoService
from ..workers.auto_setup_worker import AutoSetupWorker
from ..workers.command_worker import CommandWorker
from ..workers.generate_worker import GenerateWorker
from ..workers.mmaudio_env_setup_worker import MMAudioEnvSetupWorker
from ..workers.mmaudio_download_worker import MMAudioDownloadWorker
from ..workers.update_worker import UpdateWorker, UpdateWorkerResult
from .preview_player import PreviewPlayer


MIN_GENERATION_DURATION = 0.1
MAX_GENERATION_DURATION = 24 * 60 * 60.0


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        if APP_ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(APP_ICON_PATH)))
        self.setAcceptDrops(True)

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
        self.auto_setup_worker: AutoSetupWorker | None = None
        self.update_worker: UpdateWorker | None = None

        self._build_ui()
        self._load_config_to_ui()
        self._append_log("mWrapperを起動しました。自動アップデートを確認します。")
        self._update_button_state()
        QTimer.singleShot(300, self._check_for_updates)

    def _build_ui(self) -> None:
        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setSpacing(10)

        content_splitter = QSplitter(Qt.Orientation.Horizontal)
        preview_group = QGroupBox("プレビュー")
        preview_layout = QVBoxLayout(preview_group)
        self.preview = PreviewPlayer()
        preview_layout.addWidget(self.preview)
        preview_group.setMinimumWidth(640)

        side = QWidget()
        side_layout = QVBoxLayout(side)
        side_layout.setContentsMargins(0, 0, 0, 0)
        side_layout.addWidget(self._build_environment_group())
        side_layout.addWidget(self._build_prompt_group(), 2)
        side_layout.addWidget(self._build_generation_group())
        side_layout.addWidget(self._build_log_group(), 1)

        content_splitter.addWidget(preview_group)
        content_splitter.addWidget(side)
        content_splitter.setStretchFactor(0, 5)
        content_splitter.setStretchFactor(1, 2)
        root_layout.addWidget(content_splitter, 1)

        self.setCentralWidget(root)
        self.statusBar().showMessage("Ready")

    def _build_environment_group(self) -> QGroupBox:
        group = QGroupBox("環境")
        layout = QGridLayout(group)

        self.demo_script_edit = QLineEdit()
        self.python_executable_edit = QLineEdit()
        self.mmaudio_output_edit = QLineEdit()

        self.save_dir_edit = QLineEdit()
        browse_save = self._tool_button(QStyle.SP_DirOpenIcon, "保存先フォルダを選択")
        browse_save.clicked.connect(lambda: self._choose_directory(self.save_dir_edit))
        self.reset_environment_button = QPushButton("初期化")
        self.reset_environment_button.setToolTip("セットアップ先を選択し、専用環境を自動で再構築します")
        self.reset_environment_button.clicked.connect(self.reset_environment)

        layout.addWidget(QLabel("保存先"), 0, 0)
        layout.addWidget(self.save_dir_edit, 0, 1)
        layout.addWidget(browse_save, 0, 2)
        layout.addWidget(self.reset_environment_button, 0, 3)
        layout.setColumnStretch(1, 1)
        return group

    def _build_prompt_group(self) -> QGroupBox:
        group = QGroupBox("プロンプト")
        layout = QVBoxLayout(group)
        layout.addWidget(QLabel("ポジティブプロンプト"))
        self.prompt_edit = QPlainTextEdit()
        self.prompt_edit.setPlaceholderText("例: breathing, bed creaks, cloth rustling, room ambience")
        self.prompt_edit.setFixedHeight(96)
        self.prompt_edit.textChanged.connect(self._update_button_state)
        layout.addWidget(self.prompt_edit)
        layout.addWidget(QLabel("ネガティブプロンプト"))
        self.negative_prompt_edit = QPlainTextEdit()
        self.negative_prompt_edit.setPlaceholderText("例: music, speech, distorted audio")
        self.negative_prompt_edit.setFixedHeight(64)
        layout.addWidget(self.negative_prompt_edit)
        return group

    def _build_generation_group(self) -> QGroupBox:
        group = QGroupBox("生成")
        layout = QVBoxLayout(group)
        settings_layout = QHBoxLayout()
        self.model_combo = QComboBox()
        for model_id, label in MODEL_CHOICES.items():
            self.model_combo.addItem(label, model_id)
        settings_layout.addWidget(QLabel("model"))
        settings_layout.addWidget(self.model_combo)
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
        self.fixed_seed_checkbox = QCheckBox("seed固定")
        settings_layout.addWidget(self.fixed_seed_checkbox)
        self.seed_spin = QSpinBox()
        self.seed_spin.setRange(0, 2_147_483_647)
        settings_layout.addWidget(self.seed_spin)
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
        self.fixed_seed_checkbox.setChecked(self.config.generation.default_seed_mode == "fixed")
        self.seed_spin.setValue(int(self.config.generation.fixed_seed))
        self.prompt_edit.setPlainText(self.config.generation.last_positive_prompt)
        self.negative_prompt_edit.setPlainText(self.config.generation.last_negative_prompt)
        model_id = normalize_model_id(self.config.model.default_model)
        index = self.model_combo.findData(model_id)
        self.model_combo.setCurrentIndex(index if index >= 0 else 0)

    def _save_ui_to_config(self) -> None:
        self.config.mmaudio.demo_script_path = self.demo_script_edit.text().strip()
        self.config.mmaudio.python_executable = self.python_executable_edit.text().strip() or "python"
        self.config.mmaudio.output_dir = self.mmaudio_output_edit.text().strip()
        self.config.paths.output_dir = self.save_dir_edit.text().strip()
        self.config.generation.default_duration = float(self.duration_spin.value())
        self.config.generation.require_cuda = self.require_cuda_checkbox.isChecked()
        self.config.generation.default_seed_mode = (
            "fixed" if self.fixed_seed_checkbox.isChecked() else "random"
        )
        self.config.generation.fixed_seed = int(self.seed_spin.value())
        self.config.generation.last_positive_prompt = self.prompt_edit.toPlainText()
        self.config.generation.last_negative_prompt = self.negative_prompt_edit.toPlainText()
        self.config.model.default_model = normalize_model_id(str(self.model_combo.currentData()))
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
        self.preview.set_source(path)
        self._sync_duration_to_video(info.duration)
        self.statusBar().showMessage(f"入力動画: {path.name}")
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
        if self.auto_setup_worker is not None and self.auto_setup_worker.isRunning():
            return

        self._save_ui_to_config()
        self.log_view.clear()
        self._set_downloading(True)

        self.download_worker = MMAudioDownloadWorker(Path(self.config.paths.tools_dir), self)
        self.download_worker.log.connect(self._append_log)
        self.download_worker.finished_download.connect(self._mmaudio_download_finished)
        self.download_worker.finished.connect(lambda: self._set_downloading(False))
        self.download_worker.start()

    def _ensure_initial_environment(self) -> None:
        if self.auto_setup_worker is not None and self.auto_setup_worker.isRunning():
            return
        if self.download_worker is not None and self.download_worker.isRunning():
            return
        if self.env_setup_worker is not None and self.env_setup_worker.isRunning():
            return

        self._append_log("自動セットアップ確認: セットアップ先と必要ファイルを確認しています。")
        setup_paths = setup_paths_for_root(Path(self.config.paths.setup_dir))
        readiness = inspect_setup_readiness(setup_paths)
        if not readiness.ready and not self.config.paths.setup_dir_confirmed:
            self._append_log("自動セットアップ確認: 初回セットアップ先の選択が必要です。")
            selected = self._choose_setup_root_for_initial_setup(setup_paths.root)
            if selected is None:
                self._append_log("初回自動セットアップをキャンセルしました。")
                return
            self._append_log(f"自動セットアップ確認: セットアップ先を設定しました: {selected}")
            self._apply_setup_root(selected)
            setup_paths = setup_paths_for_root(selected)
            readiness = inspect_setup_readiness(setup_paths)

        tools_dir = setup_paths.tools_dir
        install_dir = default_mmaudio_install_dir(tools_dir)
        demo_path = install_dir / "demo.py"
        venv_dir = setup_paths.venvs_dir / "mmaudio"
        venv_python = venv_dir / "Scripts" / "python.exe"
        nsfw_weights = nsfw_mmaudio_model_path(install_dir)

        demo_ready = demo_path.exists()
        venv_ready = venv_python.exists()
        nsfw_ready = nsfw_weights.exists() and nsfw_weights.stat().st_size > 0

        if demo_ready:
            try:
                self._append_log("自動セットアップ確認: MMAudio demo.py の互換パッチを確認しています。")
                patch_mmaudio_demo(demo_path)
            except Exception as exc:
                self._append_log(f"MMAudio demo.py の互換パッチ確認に失敗しました: {exc}")

        if demo_ready and venv_ready and nsfw_ready:
            changed = False
            if self.demo_script_edit.text().strip() != str(demo_path):
                self.demo_script_edit.setText(str(demo_path))
                changed = True
            if self.python_executable_edit.text().strip() != str(venv_python):
                self.python_executable_edit.setText(str(venv_python))
                changed = True
            if not self.mmaudio_output_edit.text().strip():
                self.mmaudio_output_edit.setText(str(install_dir / "output"))
                changed = True
            if changed:
                self._save_ui_to_config()
            self._append_log("自動セットアップ確認: 専用環境は準備済みです。")
            cuda_ok = self._check_cuda_environment(show_message=False)
            dependencies_ok = self._check_mmaudio_dependencies(show_message=False)
            hardware = inspect_hardware()
            if self.config.generation.require_cuda and hardware.has_nvidia_gpu and not cuda_ok:
                base_python = choose_mmaudio_base_python()
                if base_python is None:
                    self._append_log("CUDA自動修復を開始できません: Python 3.10-3.12 が見つかりません。")
                    return
                self._append_log(
                    "CUDA対応PyTorchではないため、MMAudio専用Python環境を自動で再構築します。"
                )
                self._start_auto_setup(setup_paths, base_python.path, True)
                return
            if not dependencies_ok:
                base_python = choose_mmaudio_base_python()
                if base_python is None:
                    self._append_log("依存関係の自動修復を開始できません: Python 3.10-3.12 が見つかりません。")
                    return
                self._append_log("MMAudio依存関係に問題があるため、専用Python環境を自動で再構築します。")
                self._start_auto_setup(setup_paths, base_python.path, True)
                return
            return

        base_python = None if venv_ready else choose_mmaudio_base_python()
        if not venv_ready and base_python is None:
            self._append_log("自動セットアップを開始できません: Python 3.10-3.12 が見つかりません。")
            return

        self.log_view.clear()
        self._append_log("初回自動セットアップを開始します。")
        if base_python is not None:
            self._append_log(f"セットアップ: 使用するPython: {base_python.path}")
        self._append_log(f"セットアップ: 構築先: {setup_paths.root}")
        self._start_auto_setup(setup_paths, base_python.path if base_python else None, not venv_ready)

    def _check_for_updates(self) -> None:
        if self.update_worker is not None and self.update_worker.isRunning():
            return
        self.update_worker = UpdateWorker(self)
        self.update_worker.log.connect(self._append_log)
        self.update_worker.progress.connect(self._update_download_progress)
        self.update_worker.finished_update.connect(self._auto_update_finished)
        self.update_worker.finished.connect(lambda: self._set_updating(False))
        self._set_updating(True)
        self.update_worker.start()

    def reset_environment(self) -> None:
        if self._is_busy():
            return

        selected = self._choose_setup_root_for_initial_setup(Path(self.config.paths.setup_dir))
        if selected is None:
            self._append_log("初期化をキャンセルしました。")
            return

        self._apply_setup_root(selected)
        base_python = choose_mmaudio_base_python()
        if base_python is None:
            self._append_log("初期化を開始できません: Python 3.10-3.12 が見つかりません。")
            return

        self.log_view.clear()
        self._append_log("初期化を開始します。")
        self._start_auto_setup(setup_paths_for_root(selected), base_python.path, True)

    def _start_auto_setup(
        self,
        setup_paths,
        base_python_path: Path | None,
        rebuild_venv: bool,
    ) -> None:
        self.auto_setup_worker = AutoSetupWorker(
            setup_paths.tools_dir,
            setup_paths.venvs_dir / "mmaudio",
            base_python_path,
            rebuild_venv=rebuild_venv,
            parent=self,
        )
        self.auto_setup_worker.log.connect(self._append_log)
        self.auto_setup_worker.finished_auto_setup.connect(self._auto_setup_finished)
        self.auto_setup_worker.finished.connect(lambda: self._set_installing(False))
        self._set_installing(True)
        self.auto_setup_worker.start()

    def _choose_setup_root_for_initial_setup(self, initial_root: Path) -> Path | None:
        QMessageBox.information(
            self,
            "初回セットアップ先",
            "MMAudio、NSFW_MMaudio、専用Python環境を構築するフォルダを選択してください。\n"
            "20GBほどの空き容量が必要です。",
        )
        while True:
            directory = QFileDialog.getExistingDirectory(
                self,
                "初回セットアップ先フォルダを選択",
                str(initial_root),
            )
            if not directory:
                return None
            root = Path(directory)
            paths = setup_paths_for_root(root)
            readiness = inspect_setup_readiness(paths)
            required = estimate_required_setup_bytes(readiness)
            free = free_bytes_for_path(root)
            if free >= required:
                return root
            QMessageBox.warning(
                self,
                "空き容量不足",
                "選択したドライブの空き容量が不足しています。\n\n"
                f"必要見込み: {format_bytes(required)}\n"
                f"空き容量: {format_bytes(free)}\n\n"
                "別のフォルダを選択してください。",
            )

    def _apply_setup_root(self, root: Path) -> None:
        paths = setup_paths_for_root(root)
        self.config.paths.setup_dir = str(paths.root)
        self.config.paths.setup_dir_confirmed = True
        self.config.paths.tools_dir = str(paths.tools_dir)
        self.config.paths.temp_dir = str(paths.temp_dir)
        self.config.paths.models_dir = str(paths.models_dir)
        self.config.paths.logs_dir = str(paths.logs_dir)
        self.config.paths.venvs_dir = str(paths.venvs_dir)
        self.demo_script_edit.setText(str(default_mmaudio_install_dir(paths.tools_dir) / "demo.py"))
        self.python_executable_edit.setText(str(paths.venvs_dir / "mmaudio" / "Scripts" / "python.exe"))
        self.mmaudio_output_edit.setText(str(default_mmaudio_install_dir(paths.tools_dir) / "output"))
        self._save_ui_to_config()
        self._append_log(f"初回セットアップ先を設定しました: {paths.root}")

    def start_generation(self) -> None:
        if self.worker is not None and self.worker.isRunning():
            return
        if self.command_worker is not None and self.command_worker.isRunning():
            return
        if self.env_setup_worker is not None and self.env_setup_worker.isRunning():
            return
        if self.auto_setup_worker is not None and self.auto_setup_worker.isRunning():
            return
        if self.current_video_path is None:
            self._show_error("入力エラー", "動画を選択してください。")
            return

        prompt = self.prompt_edit.toPlainText().strip()
        if not prompt:
            self._show_error("入力エラー", "ポジティブプロンプトを入力してください。")
            return
        negative_prompt = self.negative_prompt_edit.toPlainText().strip()
        model_id = normalize_model_id(str(self.model_combo.currentData()))
        seed = self._current_seed()
        self.seed_spin.setValue(seed)

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
            negative_prompt=negative_prompt,
            seed=seed,
            duration=float(self.duration_spin.value()),
            model_id=model_id,
            output_dir=temp_dir,
            created_at=datetime.now(),
            python_executable=self.config.mmaudio.python_executable or "python",
            mmaudio_script_path=demo_script,
            mmaudio_working_dir=demo_script.parent,
            mmaudio_output_dir=mmaudio_output,
            runtime_cache_dir=Path(self.config.paths.models_dir) / "runtime_cache",
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
        if self.auto_setup_worker is not None and self.auto_setup_worker.isRunning():
            self._append_log("自動セットアップを停止しています...")
            self.auto_setup_worker.cancel()

    def install_cuda_pytorch(self) -> None:
        if self.worker is not None and self.worker.isRunning():
            return
        if self.download_worker is not None and self.download_worker.isRunning():
            return
        if self.command_worker is not None and self.command_worker.isRunning():
            return
        if self.env_setup_worker is not None and self.env_setup_worker.isRunning():
            return
        if self.auto_setup_worker is not None and self.auto_setup_worker.isRunning():
            return

        self._save_ui_to_config()
        python_executable = self.config.mmaudio.python_executable or "python"
        uv_path = find_uv(Path(self.config.paths.venvs_dir))
        command = build_cuda_torch_install_command(python_executable, uv_path=uv_path)
        answer = QMessageBox.question(
            self,
            "CUDA PyTorch導入",
            f"選択中のMMAudio Python環境に{PYTORCH_CUDA_LABEL}版PyTorchを導入します。\n"
            "既存のtorch/torchvision/torchaudioは再インストールされます。\n\n"
            "uvで導入します。初回セットアップ済み環境ではローカルuvを使用します。\n"
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
        if self.auto_setup_worker is not None and self.auto_setup_worker.isRunning():
            return

        self._save_ui_to_config()
        python_executable = self.config.mmaudio.python_executable or "python"
        working_dir = self._mmaudio_working_dir_or_none()
        if working_dir is None:
            self._show_error("MMAudio依存修復エラー", "MMAudio の demo.py を先に指定してください。")
            return

        uv_path = find_uv(Path(self.config.paths.venvs_dir))
        command = build_mmaudio_dependency_repair_command(python_executable, uv_path=uv_path)
        answer = QMessageBox.question(
            self,
            "MMAudio依存修復",
            "選択中のMMAudio Python環境で依存関係を修復します。\n"
            "MMAudioをeditable installし、NumPyをMMAudio互換の <2.1 に調整します。\n\n"
            "uvで導入します。初回セットアップ済み環境ではローカルuvを使用します。\n"
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
        if self.auto_setup_worker is not None and self.auto_setup_worker.isRunning():
            return
        if self.env_setup_worker is not None and self.env_setup_worker.isRunning():
            return
        if self.auto_setup_worker is not None and self.auto_setup_worker.isRunning():
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

        venv_dir = Path(self.config.paths.venvs_dir) / "mmaudio"
        answer = QMessageBox.question(
            self,
            "MMAudio専用venv作成",
            "MMAudio専用の仮想環境を作成し、CUDA版PyTorchとMMAudio依存関係を導入します。\n"
            "uvがない場合はセットアップ先にuvを導入してから構築します。\n"
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

    def _current_seed(self) -> int:
        if self.fixed_seed_checkbox.isChecked():
            return int(self.seed_spin.value())
        return random.randint(0, 2_147_483_647)

    def _is_busy(self) -> bool:
        return (
            (self.worker is not None and self.worker.isRunning())
            or (self.download_worker is not None and self.download_worker.isRunning())
            or (self.command_worker is not None and self.command_worker.isRunning())
            or (self.env_setup_worker is not None and self.env_setup_worker.isRunning())
            or (self.auto_setup_worker is not None and self.auto_setup_worker.isRunning())
            or (self.update_worker is not None and self.update_worker.isRunning())
        )

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

    def _set_updating(self, updating: bool) -> None:
        if updating:
            self.progress.setRange(0, 0)
            self.statusBar().showMessage("Checking for updates...")
        else:
            self.progress.setRange(0, 1)
            self.progress.setValue(0)
            self.statusBar().showMessage("Ready")
        self._update_button_state()

    def _update_download_progress(self, downloaded: int, total: int) -> None:
        if total <= 0:
            self.progress.setRange(0, 0)
            return
        percent = min(100, max(0, int(downloaded * 100 / total)))
        self.progress.setRange(0, 100)
        self.progress.setValue(percent)
        self.statusBar().showMessage(f"Downloading update... {percent}%")

    def _update_button_state(self, running: bool | None = None) -> None:
        if running is None:
            running = self.worker is not None and self.worker.isRunning()
        downloading = self.download_worker is not None and self.download_worker.isRunning()
        installing = self.command_worker is not None and self.command_worker.isRunning()
        setting_up_env = self.env_setup_worker is not None and self.env_setup_worker.isRunning()
        auto_setting_up = self.auto_setup_worker is not None and self.auto_setup_worker.isRunning()
        updating = self.update_worker is not None and self.update_worker.isRunning()
        busy = running or downloading or installing or setting_up_env or auto_setting_up or updating
        has_video = self.current_video_path is not None
        has_prompt = bool(self.prompt_edit.toPlainText().strip())
        has_result = self.generated_video_path is not None
        self.generate_button.setEnabled(has_video and has_prompt and not busy)
        self.stop_button.setEnabled(running or installing or setting_up_env or auto_setting_up)
        self.save_button.setEnabled(has_result and not busy)
        self.open_save_dir_button.setEnabled(not busy)
        self.reset_environment_button.setEnabled(not busy)

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

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        if self._first_supported_video_from_event(event) is not None:
            event.acceptProposedAction()
            return
        event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        path = self._first_supported_video_from_event(event)
        if path is None:
            event.ignore()
            return
        event.acceptProposedAction()
        self.load_video(path)

    @staticmethod
    def _first_supported_video_from_event(event: QDragEnterEvent | QDropEvent) -> Path | None:
        urls = event.mimeData().urls() if event.mimeData().hasUrls() else []
        for url in urls:
            if not url.isLocalFile():
                continue
            path = Path(url.toLocalFile())
            if path.is_file() and path.suffix.lower() in SUPPORTED_VIDEO_EXTENSIONS:
                return path
        return None

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

    def _auto_setup_finished(self, return_code: int, demo_path: object, venv_python: object) -> None:
        if return_code == 0 and demo_path and venv_python:
            demo = Path(str(demo_path))
            python = Path(str(venv_python))
            self.demo_script_edit.setText(str(demo))
            self.python_executable_edit.setText(str(python))
            self.mmaudio_output_edit.setText(str(demo.parent / "output"))
            self._save_ui_to_config()
            self._append_log("初回自動セットアップが完了しました。")
            play_setup_complete_chime()
            self._check_cuda_environment(show_message=False)
            self._check_mmaudio_dependencies(show_message=False)
            return

        self._append_log(f"初回自動セットアップに失敗しました。終了コード: {return_code}")
        QMessageBox.warning(
            self,
            "初回自動セットアップエラー",
            "初回自動セットアップに失敗しました。ログを確認してください。",
        )

    def _auto_update_finished(self, result: object) -> None:
        update_result = result if isinstance(result, UpdateWorkerResult) else None
        if update_result is None:
            self._append_log("自動アップデート確認: 結果を取得できませんでした。現在のバージョンで起動します。")
            self._ensure_initial_environment()
            return

        if update_result.should_quit:
            self._append_log("自動アップデート: 更新適用のため mWrapper を終了します。")
            app = QApplication.instance()
            if app is not None:
                QTimer.singleShot(500, app.quit)
            return

        if update_result.error:
            self._append_log(
                "自動アップデート確認: アップデートに失敗したため、現在のバージョンで起動します。"
            )
            self._append_log(f"自動アップデートエラー: {update_result.error}")
        elif update_result.skipped:
            self._append_log("自動アップデート確認: スキップしました。")
        else:
            self._append_log("自動アップデート確認: 現在のバージョンが最新版です。")
        self._ensure_initial_environment()

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
        if self.auto_setup_worker is not None and self.auto_setup_worker.isRunning():
            QMessageBox.information(
                self,
                "初回自動セットアップ中",
                "初回自動セットアップ中です。完了してから終了してください。",
            )
            event.ignore()
            return
        if self.update_worker is not None and self.update_worker.isRunning():
            QMessageBox.information(
                self,
                "自動アップデート中",
                "自動アップデート中です。完了してから終了してください。",
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


def _generation_duration_value(value: float | None) -> float:
    if value is None or value <= 0:
        return 8.0
    return round(min(max(float(value), MIN_GENERATION_DURATION), MAX_GENERATION_DURATION), 2)
