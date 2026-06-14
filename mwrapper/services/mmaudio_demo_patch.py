from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


AUDIO_PATCH_MARKER = "# mWrapper patch: save audio with soundfile to avoid TorchCodec runtime DLL issues"
NSFW_VARIANT_PATCH_MARKER = "# mWrapper patch: register NSFW_MMaudio local model variant"
PATCH_MARKER = AUDIO_PATCH_MARKER


@dataclass(slots=True)
class MMAudioDemoPatchResult:
    changed: bool
    message: str


def patch_mmaudio_demo(demo_path: Path) -> MMAudioDemoPatchResult:
    if not demo_path.exists():
        raise FileNotFoundError(f"MMAudio demo.py was not found: {demo_path}")

    patched = demo_path.read_text(encoding="utf-8")
    changed = False

    if AUDIO_PATCH_MARKER not in patched:
        if "torchaudio.save(save_path, audio, seq_cfg.sampling_rate)" not in patched:
            if "torchaudio.save" in patched:
                raise RuntimeError("MMAudio demo.py のtorchaudio保存処理を自動パッチできませんでした。")
        else:
            patched = _replace_torchaudio_import(patched)
            patched = _insert_save_helper(patched)
            patched = patched.replace(
                "    torchaudio.save(save_path, audio, seq_cfg.sampling_rate)",
                "    _mwrapper_save_audio(save_path, audio, seq_cfg.sampling_rate)",
            )
            changed = True

    if NSFW_VARIANT_PATCH_MARKER not in patched:
        patched = _insert_nsfw_variant(patched)
        changed = True

    if not changed:
        return MMAudioDemoPatchResult(False, "MMAudio demo.py はすでに互換パッチ適用済みです。")

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

{AUDIO_PATCH_MARKER}
def _mwrapper_save_audio(save_path: Path, audio: torch.Tensor, sampling_rate: int) -> None:
    audio_np = audio.detach().cpu().numpy()
    if audio_np.ndim == 2 and audio_np.shape[0] <= audio_np.shape[1]:
        audio_np = audio_np.T
    sf.write(save_path, audio_np, sampling_rate)
'''
    return source.replace(anchor, anchor + helper, 1)


def _insert_nsfw_variant(source: str) -> str:
    anchor = "log = logging.getLogger()\n"
    if anchor not in source:
        raise RuntimeError("MMAudio demo.py のNSFWモデルパッチ挿入位置を見つけられませんでした。")
    helper = f'''

{NSFW_VARIANT_PATCH_MARKER}
class _MWrapperLocalModelConfig(ModelConfig):
    def download_if_needed(self):
        from mmaudio.utils.download_utils import download_model_if_needed

        if not self.model_path.exists():
            raise FileNotFoundError(f'Model weights not found: {{self.model_path}}')
        download_model_if_needed(self.vae_path)
        if self.bigvgan_16k_path is not None:
            download_model_if_needed(self.bigvgan_16k_path)
        download_model_if_needed(self.synchformer_ckpt)


all_model_cfg['nsfw_mmaudio'] = _MWrapperLocalModelConfig(model_name='large_44k',
                                                          model_path=Path('./weights/nsfw_gold_8.5k_final.pth'),
                                                          vae_path=Path('./ext_weights/v1-44.pth'),
                                                          bigvgan_16k_path=None,
                                                          mode='44k')
'''
    return source.replace(anchor, anchor + helper, 1)
