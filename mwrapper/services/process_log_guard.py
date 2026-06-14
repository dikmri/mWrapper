from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


LogCallback = Callable[[str], None]

DEFAULT_MAX_UI_LOG_LINES = 1200
DEFAULT_REPEAT_LIMIT = 3


@dataclass(slots=True)
class ProcessLogGuard:
    on_log: LogCallback
    max_ui_lines: int = DEFAULT_MAX_UI_LOG_LINES
    repeat_limit: int = DEFAULT_REPEAT_LIMIT
    emitted_count: int = 0
    suppressed_count: int = 0
    _last_line: str | None = None
    _repeat_count: int = 0

    def emit(self, line: str) -> None:
        if not line:
            return

        if line == self._last_line:
            self._repeat_count += 1
            if self._repeat_count <= self.repeat_limit:
                self._emit_or_suppress(line)
            elif self._repeat_count == self.repeat_limit + 1:
                self._emit_or_suppress(
                    "同じログが連続しているため、以降の同一行は表示を省略します。"
                )
                self.suppressed_count += 1
            else:
                self.suppressed_count += 1
            return

        self._flush_repeat_summary()
        self._last_line = line
        self._repeat_count = 1
        self._emit_or_suppress(line)

    def finish(self) -> None:
        self._flush_repeat_summary()
        if self.suppressed_count:
            self._emit_even_if_full(
                f"ログ表示を {self.suppressed_count} 行省略しました。詳細は generation.log を確認してください。"
            )

    def _flush_repeat_summary(self) -> None:
        if self._last_line is None or self._repeat_count <= self.repeat_limit + 1:
            return
        omitted = self._repeat_count - self.repeat_limit - 1
        self._emit_or_suppress(f"同一ログ {omitted} 行を省略しました。")

    def _emit_or_suppress(self, line: str) -> None:
        if self.emitted_count < self.max_ui_lines:
            self.on_log(line)
            self.emitted_count += 1
            return
        self.suppressed_count += 1

    def _emit_even_if_full(self, line: str) -> None:
        self.on_log(line)
        self.emitted_count += 1


def diagnose_fatal_log_line(line: str) -> str | None:
    lowered = line.lower()
    if "not compatible with the current pytorch installation" in lowered:
        return (
            "GPU世代に対してPyTorchのCUDA版が古すぎます。"
            "CUDA 12.8版など、このGPUに対応したPyTorchを導入してください。"
        )
    if lowered.startswith("fatal: kernel ") and "was built for" in lowered:
        return (
            "CUDAカーネルのGPU世代互換性エラーを検出しました。"
            "現在のPyTorch/CUDA wheelがこのGPUに対応していません。"
        )
    if "could not load libtorchcodec" in lowered:
        return (
            "TorchCodecの実行時DLLを読み込めません。"
            "mWrapperのMMAudio互換パッチを適用してtorchaudio.saveを回避してください。"
        )
    return None
