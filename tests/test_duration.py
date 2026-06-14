from mwrapper.ui.main_window import (
    MAX_GENERATION_DURATION,
    MIN_GENERATION_DURATION,
    _generation_duration_value,
)


def test_generation_duration_uses_video_duration() -> None:
    assert _generation_duration_value(3.456) == 3.46


def test_generation_duration_falls_back_for_missing_duration() -> None:
    assert _generation_duration_value(None) == 8.0
    assert _generation_duration_value(0) == 8.0


def test_generation_duration_is_clamped_to_ui_range() -> None:
    assert _generation_duration_value(0.01) == MIN_GENERATION_DURATION
    assert _generation_duration_value(MAX_GENERATION_DURATION + 1) == MAX_GENERATION_DURATION
