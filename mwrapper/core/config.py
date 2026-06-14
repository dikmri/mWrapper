from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from ..constants import DEFAULT_MODEL_ID, GOOGLE_API_KEY_ENV
from .paths import (
    config_path,
    default_logs_dir,
    default_models_dir,
    default_output_dir,
    default_temp_dir,
    default_tools_dir,
    ensure_dir,
)


@dataclass(slots=True)
class PathSettings:
    output_dir: str = ""
    temp_dir: str = ""
    models_dir: str = ""
    tools_dir: str = ""
    logs_dir: str = ""
    ffmpeg_path: str = ""
    ffprobe_path: str = ""


@dataclass(slots=True)
class TranslationSettings:
    provider: str = "google"
    api_key_env: str = GOOGLE_API_KEY_ENV


@dataclass(slots=True)
class ModelSettings:
    default_model: str = DEFAULT_MODEL_ID
    models: dict[str, dict[str, str]] = field(
        default_factory=lambda: {
            DEFAULT_MODEL_ID: {
                "repo_id": "phazei/NSFW_MMaudio",
                "local_dir": "",
            }
        }
    )


@dataclass(slots=True)
class GenerationSettings:
    default_duration: float = 8.0
    default_seed_mode: str = "random"
    keep_temp_files: bool = False
    require_cuda: bool = True


@dataclass(slots=True)
class MMAudioSettings:
    python_executable: str = ""
    demo_script_path: str = ""
    working_dir: str = ""
    output_dir: str = ""
    extra_args: list[str] = field(default_factory=list)


@dataclass(slots=True)
class SafetySettings:
    accepted_terms: bool = False
    accepted_terms_at: str | None = None


@dataclass(slots=True)
class AppConfig:
    version: int = 1
    paths: PathSettings = field(default_factory=PathSettings)
    translation: TranslationSettings = field(default_factory=TranslationSettings)
    model: ModelSettings = field(default_factory=ModelSettings)
    generation: GenerationSettings = field(default_factory=GenerationSettings)
    mmaudio: MMAudioSettings = field(default_factory=MMAudioSettings)
    safety: SafetySettings = field(default_factory=SafetySettings)

    @classmethod
    def defaults(cls) -> "AppConfig":
        cfg = cls()
        cfg.paths.output_dir = str(default_output_dir())
        cfg.paths.temp_dir = str(default_temp_dir())
        cfg.paths.models_dir = str(default_models_dir())
        cfg.paths.tools_dir = str(default_tools_dir())
        cfg.paths.logs_dir = str(default_logs_dir())
        cfg.paths.ffmpeg_path = shutil.which("ffmpeg") or ""
        cfg.paths.ffprobe_path = shutil.which("ffprobe") or ""
        cfg.mmaudio.python_executable = "python"
        return cfg

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AppConfig":
        defaults = cls.defaults()

        paths = {**asdict(defaults.paths), **data.get("paths", {})}
        translation = {**asdict(defaults.translation), **data.get("translation", {})}
        model = {**asdict(defaults.model), **data.get("model", {})}
        generation = {**asdict(defaults.generation), **data.get("generation", {})}
        mmaudio = {**asdict(defaults.mmaudio), **data.get("mmaudio", {})}
        safety = {**asdict(defaults.safety), **data.get("safety", {})}

        return cls(
            version=int(data.get("version", defaults.version)),
            paths=PathSettings(**paths),
            translation=TranslationSettings(**translation),
            model=ModelSettings(**model),
            generation=GenerationSettings(**generation),
            mmaudio=MMAudioSettings(**mmaudio),
            safety=SafetySettings(**safety),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ConfigManager:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or config_path()

    def load(self) -> AppConfig:
        if not self.path.exists():
            config = AppConfig.defaults()
            self.save(config)
            return config

        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            config = AppConfig.defaults()
            self.save(config)
            return config

        return AppConfig.from_dict(data)

    def save(self, config: AppConfig) -> None:
        ensure_dir(self.path.parent)
        self.path.write_text(
            json.dumps(config.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @staticmethod
    def ensure_runtime_dirs(config: AppConfig) -> None:
        for raw in (
            config.paths.output_dir,
            config.paths.temp_dir,
            config.paths.models_dir,
            config.paths.tools_dir,
            config.paths.logs_dir,
        ):
            if raw:
                ensure_dir(Path(raw))
