from pathlib import Path

from mwrapper.services.model_assets import (
    MMAUDIO_MODEL_ID,
    NSFW_MMAUDIO_MODEL_ID,
    normalize_model_id,
    nsfw_mmaudio_model_path,
)


def test_normalize_model_id_accepts_legacy_names() -> None:
    assert normalize_model_id("NSFW_MMaudio") == NSFW_MMAUDIO_MODEL_ID
    assert normalize_model_id("MMAudio") == MMAUDIO_MODEL_ID


def test_nsfw_mmaudio_model_path(tmp_path: Path) -> None:
    assert nsfw_mmaudio_model_path(tmp_path) == tmp_path / "weights" / "nsfw_gold_8.5k_final.pth"
