from __future__ import annotations

import re


ANSI_ESCAPE_RE = re.compile(r"\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
BRACKETED_LEVEL_RE = re.compile(
    r"\[\s*(INFO|WARNING|WARN|ERROR|DEBUG|CRITICAL)\s*\]\s*:",
    re.IGNORECASE,
)
PLAIN_LEVEL_RE = re.compile(
    r"^(INFO|WARNING|WARN|ERROR|DEBUG|CRITICAL)\s*:",
    re.IGNORECASE,
)

LOG_LEVELS = {
    "INFO": "情報",
    "WARNING": "警告",
    "WARN": "警告",
    "ERROR": "エラー",
    "DEBUG": "デバッグ",
    "CRITICAL": "重大エラー",
}

PHRASE_TRANSLATIONS = (
    ("Starting MMAudio CLI", "MMAudio CLIを開始しています"),
    ("Negative prompt", "ネガティブプロンプト"),
    ("Positive prompt", "ポジティブプロンプト"),
    ("Loading model", "モデルを読み込んでいます"),
    ("Loaded model", "モデルを読み込みました"),
    ("Loading weights", "重みを読み込んでいます"),
    ("Generating audio", "音声を生成しています"),
    ("Generating video", "動画を生成しています"),
    ("CUDA/MPS are not available, running on CPU", "CUDA/MPSを利用できないためCPUで実行しています"),
    ("Generation completed", "生成が完了しました"),
    ("Generation failed", "生成に失敗しました"),
    ("MMAudio exited with code", "MMAudioが終了コード付きで失敗しました"),
    ("MMAudio output mp4 was not found", "MMAudioの出力mp4が見つかりません"),
    ("MMAudio already exists", "MMAudioはすでに存在します"),
    ("Downloading MMAudio from", "MMAudioをダウンロードしています:"),
    ("Download progress", "ダウンロード進捗"),
    ("Extracting MMAudio archive", "MMAudioアーカイブを展開しています"),
    ("MMAudio installed", "MMAudioをインストールしました"),
    ("MMAudio download failed", "MMAudio取得に失敗しました"),
    ("Configured demo.py", "demo.pyを設定しました"),
    ("Loaded video", "動画を読み込みました"),
    ("Cancelling generation", "生成を停止しています"),
    ("Saved", "保存しました"),
    ("Saving", "保存しています"),
    ("Output", "出力"),
    ("Duration", "長さ"),
    ("Seed", "シード"),
    ("Prompt", "プロンプト"),
)


def strip_ansi_sequences(text: str) -> str:
    without_ansi = ANSI_ESCAPE_RE.sub("", text)
    return CONTROL_CHAR_RE.sub("", without_ansi)


def format_log_line(text: str) -> str:
    cleaned = strip_ansi_sequences(text).strip()
    if not cleaned:
        return ""

    cleaned = BRACKETED_LEVEL_RE.sub(_replace_bracketed_level, cleaned)
    cleaned = PLAIN_LEVEL_RE.sub(_replace_plain_level, cleaned)
    if _looks_like_command_line(cleaned):
        return cleaned
    return _translate_known_phrases(cleaned)


def _replace_bracketed_level(match: re.Match[str]) -> str:
    level = LOG_LEVELS.get(match.group(1).upper(), match.group(1))
    return f"[{level}]:"


def _replace_plain_level(match: re.Match[str]) -> str:
    level = LOG_LEVELS.get(match.group(1).upper(), match.group(1))
    return f"{level}:"


def _translate_known_phrases(text: str) -> str:
    translated = text
    for english, japanese in PHRASE_TRANSLATIONS:
        translated = re.sub(re.escape(english), japanese, translated, flags=re.IGNORECASE)
    return translated


def _looks_like_command_line(text: str) -> bool:
    lowered = text.lower()
    return (
        "demo.py" in lowered
        and ("--duration" in lowered or "--prompt" in lowered or "--video" in lowered)
    )
