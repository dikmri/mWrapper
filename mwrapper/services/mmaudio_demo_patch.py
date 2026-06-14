from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


PATCH_MARKER = "# mWrapper patch: save audio with soundfile to avoid TorchCodec runtime DLL issues"


@dataclass(slots=True)
class MMAudioDemoPatchResult:
    changed: bool
    message: str


def patch_mmaudio_demo(demo_path: Path) -> MMAudioDemoPatchResult:
    if not demo_path.exists():
        raise FileNotFoundError(f"MMAudio demo.py was not found: {demo_path}")

    source = demo_path.read_text(encoding="utf-8")
    if PATCH_MARKER in source:
        return MMAudioDemoPatchResult(False, "MMAudio demo.py はすでに互換パッチ適用済みです。")

    if "torchaudio.save(save_path, audio, seq_cfg.sampling_rate)" not in source:
        if "torchaudio.save" not in source:
            return MMAudioDemoPatchResult(False, "MMAudio demo.py にtorchaudio保存処理は見つかりませんでした。")
        raise RuntimeError("MMAudio demo.py のtorchaudio保存処理を自動パッチできませんでした。")

    patched = _replace_torchaudio_import(source)
    patched = _insert_save_helper(patched)
    patched = patched.replace(
        "    torchaudio.save(save_path, audio, seq_cfg.sampling_rate)",
        "    _mwrapper_save_audio(save_path, audio, seq_cfg.sampling_rate)",
    )

    demo_path.write_text(patched, encoding="utf-8")
    return MMAudioDemoPatchResult(
        True,
        "MMAudio demo.py に音声保存互換パッチを適用しました。",
    )


def _replace_torchaudio_import(source: str) -> str:
    if "import torchaudio" not in source:
        if "import soundfile as sf" in source:
            return source
        raise RuntimeError("MMAudio demo.py のtorchaudio importを自動パッチできませんでした。")
    return source.replace("import torchaudio", "import soundfile as sf", 1)


def _insert_save_helper(source: str) -> str:
    anchor = "log = logging.getLogger()\n"
    if anchor not in source:
        raise RuntimeError("MMAudio demo.py のパッチ挿入位置を見つけられませんでした。")
    helper = f'''

{PATCH_MARKER}
def _mwrapper_save_audio(save_path: Path, audio: torch.Tensor, sampling_rate: int) -> None:
    audio_np = audio.detach().cpu().numpy()
    if audio_np.ndim == 2 and audio_np.shape[0] <= audio_np.shape[1]:
        audio_np = audio_np.T
    sf.write(save_path, audio_np, sampling_rate)
'''
    return source.replace(anchor, anchor + helper, 1)
