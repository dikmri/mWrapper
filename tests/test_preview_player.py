from PySide6.QtMultimedia import QMediaPlayer

from mwrapper.ui.preview_player import PreviewPlayer


def test_preview_player_input_mode_uses_loop(qtbot, tmp_path) -> None:
    player = PreviewPlayer()
    qtbot.addWidget(player)
    video = tmp_path / "input.mp4"
    video.write_bytes(b"")

    player.set_source(video, autoplay=True, loop=True)

    assert player._pending_autoplay is True
    assert player._pending_first_frame is False
    assert player._player.loops() == QMediaPlayer.Loops.Infinite


def test_preview_player_result_mode_waits_for_first_frame(qtbot, tmp_path) -> None:
    player = PreviewPlayer()
    qtbot.addWidget(player)
    video = tmp_path / "result.mp4"
    video.write_bytes(b"")

    player.set_source(video, show_first_frame=True)

    assert player._pending_autoplay is False
    assert player._pending_first_frame is True
    assert player._player.loops() == QMediaPlayer.Loops.Once
