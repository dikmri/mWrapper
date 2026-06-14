from mwrapper.services.mmaudio_dependencies import (
    MMAudioDependencyInfo,
    format_mmaudio_dependency_info,
)


def test_format_mmaudio_dependency_info_reports_ok() -> None:
    info = MMAudioDependencyInfo(
        executable="python",
        versions={
            "numpy": "2.3.5",
            "numba": "0.62.1",
            "librosa": "0.11.0",
            "soundfile": "0.14.0",
        },
    )

    assert "MMAudio依存確認: OK" in format_mmaudio_dependency_info(info)


def test_format_mmaudio_dependency_info_reports_numpy_24_conflict() -> None:
    info = MMAudioDependencyInfo(
        executable="python",
        versions={
            "numpy": "2.4.4",
            "numba": "0.62.1",
            "librosa": "0.11.0",
            "soundfile": "0.14.0",
        },
        import_errors={"numba": "ImportError: Numba needs NumPy 2.3 or less. Got NumPy 2.4."},
    )

    message = format_mmaudio_dependency_info(info)

    assert "MMAudio依存確認: エラー" in message
    assert "NumPy 2.4系" in message
