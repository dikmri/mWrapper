from pathlib import Path

from mwrapper.services.output_manager import numbered_output_path, sanitize_filename_stem


def test_sanitize_filename_stem_replaces_windows_invalid_chars() -> None:
    assert sanitize_filename_stem('a<b>c:d"e/f\\g|h?i*j') == "a_b_c_d_e_f_g_h_i_j"


def test_numbered_output_path_uses_base_name_first(tmp_path: Path) -> None:
    original = tmp_path / "sample.mp4"
    original.write_bytes(b"input")

    assert numbered_output_path(tmp_path, original) == tmp_path / "sample_mmaudio.mp4"


def test_numbered_output_path_adds_sequence_on_conflict(tmp_path: Path) -> None:
    original = tmp_path / "sample.mp4"
    original.write_bytes(b"input")
    (tmp_path / "sample_mmaudio.mp4").write_bytes(b"existing")
    (tmp_path / "sample_mmaudio_001.mp4").write_bytes(b"existing")

    assert numbered_output_path(tmp_path, original) == tmp_path / "sample_mmaudio_002.mp4"
