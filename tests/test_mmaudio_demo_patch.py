from pathlib import Path

from mwrapper.services.mmaudio_demo_patch import PATCH_MARKER, patch_mmaudio_demo


def test_patch_mmaudio_demo_replaces_torchaudio_save(tmp_path: Path) -> None:
    demo_path = tmp_path / "demo.py"
    demo_path.write_text(
        "\n".join(
            [
                "from pathlib import Path",
                "import torch",
                "import torchaudio",
                "",
                "log = logging.getLogger()",
                "",
                "def main():",
                "    torchaudio.save(save_path, audio, seq_cfg.sampling_rate)",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = patch_mmaudio_demo(demo_path)
    patched = demo_path.read_text(encoding="utf-8")

    assert result.changed
    assert PATCH_MARKER in patched
    assert "import soundfile as sf" in patched
    assert "torchaudio.save" not in patched
    assert "_mwrapper_save_audio(save_path, audio, seq_cfg.sampling_rate)" in patched


def test_patch_mmaudio_demo_is_idempotent(tmp_path: Path) -> None:
    demo_path = tmp_path / "demo.py"
    demo_path.write_text(
        "\n".join(
            [
                "from pathlib import Path",
                "import torch",
                "import torchaudio",
                "",
                "log = logging.getLogger()",
                "",
                "def main():",
                "    torchaudio.save(save_path, audio, seq_cfg.sampling_rate)",
                "",
            ]
        ),
        encoding="utf-8",
    )

    first = patch_mmaudio_demo(demo_path)
    second = patch_mmaudio_demo(demo_path)

    assert first.changed
    assert not second.changed
