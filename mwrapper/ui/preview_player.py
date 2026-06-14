from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QStyle,
    QVBoxLayout,
    QWidget,
)


class PreviewPlayer(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._player = QMediaPlayer(self)
        self._audio = QAudioOutput(self)
        self._video = QVideoWidget(self)
        self._source_token = 0
        self._pending_autoplay = False
        self._pending_first_frame = False
        self._player.setAudioOutput(self._audio)
        self._player.setVideoOutput(self._video)

        self._play_button = QPushButton()
        self._play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self._play_button.setToolTip("再生/一時停止")
        self._play_button.clicked.connect(self.toggle_playback)

        self._stop_button = QPushButton()
        self._stop_button.setIcon(self.style().standardIcon(QStyle.SP_MediaStop))
        self._stop_button.setToolTip("停止")
        self._stop_button.clicked.connect(self._player.stop)

        self._position = QSlider(Qt.Orientation.Horizontal)
        self._position.setRange(0, 0)
        self._position.sliderMoved.connect(self._player.setPosition)

        self._time_label = QLabel("00:00 / 00:00")
        self._time_label.setMinimumWidth(96)

        self._volume = QSlider(Qt.Orientation.Horizontal)
        self._volume.setRange(0, 100)
        self._volume.setValue(80)
        self._volume.setFixedWidth(110)
        self._volume.valueChanged.connect(lambda value: self._audio.setVolume(value / 100))
        self._audio.setVolume(0.8)

        controls = QHBoxLayout()
        controls.addWidget(self._play_button)
        controls.addWidget(self._stop_button)
        controls.addWidget(self._position, 1)
        controls.addWidget(self._time_label)
        controls.addWidget(QLabel("音量"))
        controls.addWidget(self._volume)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._video, 1)
        layout.addLayout(controls)

        self._player.positionChanged.connect(self._on_position_changed)
        self._player.durationChanged.connect(self._on_duration_changed)
        self._player.playbackStateChanged.connect(self._on_state_changed)
        self._player.mediaStatusChanged.connect(self._on_media_status_changed)

    def set_source(
        self,
        path: Path | None,
        *,
        autoplay: bool = False,
        loop: bool = False,
        show_first_frame: bool = False,
    ) -> None:
        self._source_token += 1
        token = self._source_token
        self._pending_autoplay = autoplay
        self._pending_first_frame = show_first_frame and not autoplay
        self._audio.setMuted(False)
        self._player.stop()
        self._player.setLoops(
            QMediaPlayer.Loops.Infinite if loop else QMediaPlayer.Loops.Once
        )
        if path is None:
            self._pending_autoplay = False
            self._pending_first_frame = False
            self._player.setSource(QUrl())
            self._position.setRange(0, 0)
            self._time_label.setText("00:00 / 00:00")
            return
        self._player.setSource(QUrl.fromLocalFile(str(path)))
        if autoplay:
            QTimer.singleShot(0, lambda: self._start_pending_playback(token))

    def toggle_playback(self) -> None:
        if self._player.source().isEmpty():
            return
        if self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self._player.pause()
        else:
            self._player.play()

    def _on_position_changed(self, position: int) -> None:
        self._position.blockSignals(True)
        self._position.setValue(position)
        self._position.blockSignals(False)
        self._update_time_label(position, self._player.duration())

    def _on_duration_changed(self, duration: int) -> None:
        self._position.setRange(0, duration)
        self._update_time_label(self._player.position(), duration)

    def _on_media_status_changed(self, status: QMediaPlayer.MediaStatus) -> None:
        if status in (
            QMediaPlayer.MediaStatus.LoadedMedia,
            QMediaPlayer.MediaStatus.BufferedMedia,
        ):
            self._start_pending_playback(self._source_token)

    def _on_state_changed(self, state: QMediaPlayer.PlaybackState) -> None:
        icon = QStyle.SP_MediaPause if state == QMediaPlayer.PlaybackState.PlayingState else QStyle.SP_MediaPlay
        self._play_button.setIcon(self.style().standardIcon(icon))

    def _update_time_label(self, position: int, duration: int) -> None:
        self._time_label.setText(f"{_format_ms(position)} / {_format_ms(duration)}")

    def _start_pending_playback(self, token: int) -> None:
        if token != self._source_token or self._player.source().isEmpty():
            return
        if self._pending_autoplay:
            self._pending_autoplay = False
            self._player.setPosition(0)
            self._player.play()
            return
        if self._pending_first_frame:
            if self._player.mediaStatus() not in (
                QMediaPlayer.MediaStatus.LoadedMedia,
                QMediaPlayer.MediaStatus.BufferedMedia,
            ):
                return
            self._pending_first_frame = False
            self._prime_first_frame(token)

    def _prime_first_frame(self, token: int) -> None:
        if token != self._source_token or self._player.source().isEmpty():
            return
        self._player.setPosition(0)
        self._audio.setMuted(True)
        self._player.play()
        QTimer.singleShot(120, lambda: self._pause_after_prime(token))

    def _pause_after_prime(self, token: int) -> None:
        if token != self._source_token or self._player.source().isEmpty():
            return
        self._player.pause()
        self._player.setPosition(0)
        self._audio.setMuted(False)


def _format_ms(value: int) -> str:
    seconds = max(0, value // 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"
