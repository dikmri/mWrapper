from mwrapper.services.log_formatter import format_log_line, strip_ansi_sequences


def test_strip_ansi_sequences_removes_color_codes() -> None:
    assert strip_ansi_sequences("\x1b[32mINFO\x1b[0m") == "INFO"


def test_format_log_line_translates_colored_mmaudio_log() -> None:
    line = "[\x1b[32mINFO    \x1b[0m]: \x1b[32mNegative prompt: \x1b[0m"

    assert format_log_line(line) == "[情報]: ネガティブプロンプト:"


def test_format_log_line_translates_plain_app_log() -> None:
    assert format_log_line("Loaded video: C:/input.mp4") == "動画を読み込みました: C:/input.mp4"


def test_format_log_line_does_not_translate_cli_arguments() -> None:
    line = (
        r"python C:\Users\Daiki\AppData\Local\mWrapper\tools\MMAudio\demo.py "
        r"--duration=5.06 --video=H:\input.mp4 --prompt=test"
    )

    assert format_log_line(line) == line


def test_format_log_line_does_not_break_exception_class_names() -> None:
    line = "ImportError: Numba needs NumPy 2.3 or less."

    assert format_log_line(line) == line
