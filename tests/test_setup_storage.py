from pathlib import Path

from mwrapper.services.setup_storage import (
    NSFW_MODEL_ESTIMATE_BYTES,
    SETUP_WORKING_MARGIN_BYTES,
    SetupReadiness,
    estimate_required_setup_bytes,
    setup_paths_for_root,
)


def test_setup_paths_for_root(tmp_path: Path) -> None:
    paths = setup_paths_for_root(tmp_path)

    assert paths.tools_dir == tmp_path / "tools"
    assert paths.venvs_dir == tmp_path / "venvs"


def test_estimate_required_setup_bytes_counts_missing_parts() -> None:
    required = estimate_required_setup_bytes(
        SetupReadiness(demo_ready=True, venv_ready=True, nsfw_ready=False)
    )

    assert required >= NSFW_MODEL_ESTIMATE_BYTES + SETUP_WORKING_MARGIN_BYTES


def test_estimate_required_setup_bytes_returns_zero_when_ready() -> None:
    required = estimate_required_setup_bytes(
        SetupReadiness(demo_ready=True, venv_ready=True, nsfw_ready=True)
    )

    assert required == 0
