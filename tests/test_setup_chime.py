from mwrapper.services.setup_chime import build_setup_complete_chime_wav


def test_setup_complete_chime_is_wav_data() -> None:
    data = build_setup_complete_chime_wav()

    assert data.startswith(b"RIFF")
    assert b"WAVE" in data[:16]
    assert len(data) > 10_000
