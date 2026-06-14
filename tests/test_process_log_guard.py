from mwrapper.services.process_log_guard import ProcessLogGuard, diagnose_fatal_log_line


def test_process_log_guard_suppresses_repeated_lines() -> None:
    messages: list[str] = []
    guard = ProcessLogGuard(messages.append, repeat_limit=2)

    for _ in range(6):
        guard.emit("same fatal line")
    guard.finish()

    assert messages[:3] == [
        "same fatal line",
        "same fatal line",
        "同じログが連続しているため、以降の同一行は表示を省略します。",
    ]
    assert any("ログ表示を" in message for message in messages)


def test_process_log_guard_caps_ui_lines() -> None:
    messages: list[str] = []
    guard = ProcessLogGuard(messages.append, max_ui_lines=3)

    for index in range(10):
        guard.emit(f"line {index}")
    guard.finish()

    assert messages[:3] == ["line 0", "line 1", "line 2"]
    assert any("ログ表示を" in message for message in messages)


def test_diagnose_fatal_log_line_detects_torch_arch_warning() -> None:
    message = diagnose_fatal_log_line(
        "NVIDIA GeForce RTX 5060 Ti with CUDA capability sm_120 "
        "is not compatible with the current PyTorch installation."
    )

    assert message is not None
    assert "PyTorch" in message


def test_diagnose_fatal_log_line_detects_kernel_fatal() -> None:
    message = diagnose_fatal_log_line(
        "FATAL: kernel `fmha` is for sm80-sm100, but was built for sm37"
    )

    assert message is not None
    assert "CUDA" in message


def test_diagnose_fatal_log_line_detects_torchcodec_error() -> None:
    message = diagnose_fatal_log_line("RuntimeError: Could not load libtorchcodec.")

    assert message is not None
    assert "TorchCodec" in message
