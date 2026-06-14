from datetime import datetime
from pathlib import Path

from mwrapper.core.jobs import GenerateJob
from mwrapper.services.cuda_environment import PythonCudaInfo
from mwrapper.services.mmaudio_runner import MMAudioRunner


def test_build_command_uses_cli_shape(tmp_path: Path) -> None:
    script = tmp_path / "demo.py"
    video = tmp_path / "input.mp4"
    job = GenerateJob(
        job_id="job",
        input_video_path=video,
        japanese_prompt="",
        english_prompt="rain and footsteps",
        seed=None,
        duration=8,
        model_id="NSFW_MMaudio",
        output_dir=tmp_path / "job",
        created_at=datetime.now(),
        python_executable="python",
        mmaudio_script_path=script,
        mmaudio_working_dir=tmp_path,
        mmaudio_output_dir=None,
        search_dirs=[],
        extra_args=["--variant=test"],
    )

    command = MMAudioRunner().build_command(job)

    assert command == [
        "python",
        str(script),
        "--duration=8",
        f"--video={video}",
        "--prompt=rain and footsteps",
        "--variant=test",
    ]


def test_run_aborts_when_cuda_is_required_but_unavailable(tmp_path: Path, monkeypatch) -> None:
    script = tmp_path / "demo.py"
    script.write_text("print('should not run')", encoding="utf-8")
    video = tmp_path / "input.mp4"
    video.write_bytes(b"input")
    job = GenerateJob(
        job_id="job",
        input_video_path=video,
        japanese_prompt="",
        english_prompt="rain and footsteps",
        seed=None,
        duration=8,
        model_id="NSFW_MMaudio",
        output_dir=tmp_path / "job",
        created_at=datetime.now(),
        python_executable="python",
        mmaudio_script_path=script,
        mmaudio_working_dir=tmp_path,
        mmaudio_output_dir=None,
        search_dirs=[],
        extra_args=[],
        require_cuda=True,
    )
    monkeypatch.setattr(
        "mwrapper.services.mmaudio_runner.inspect_python_cuda",
        lambda *_args, **_kwargs: PythonCudaInfo(
            executable="python",
            torch_version="2.10.0+cpu",
            cuda_available=False,
        ),
    )

    result = MMAudioRunner().run(job, lambda _message: None)

    assert not result.success
    assert "CUDA対応PyTorch" in (result.error_message or "")


def test_run_aborts_when_cuda_arch_is_incompatible(tmp_path: Path, monkeypatch) -> None:
    script = tmp_path / "demo.py"
    script.write_text("print('should not run')", encoding="utf-8")
    video = tmp_path / "input.mp4"
    video.write_bytes(b"input")
    job = GenerateJob(
        job_id="job",
        input_video_path=video,
        japanese_prompt="",
        english_prompt="rain and footsteps",
        seed=None,
        duration=8,
        model_id="NSFW_MMaudio",
        output_dir=tmp_path / "job",
        created_at=datetime.now(),
        python_executable="python",
        mmaudio_script_path=script,
        mmaudio_working_dir=tmp_path,
        mmaudio_output_dir=None,
        search_dirs=[],
        extra_args=[],
        require_cuda=True,
    )
    monkeypatch.setattr(
        "mwrapper.services.mmaudio_runner.inspect_python_cuda",
        lambda *_args, **_kwargs: PythonCudaInfo(
            executable="python",
            torch_version="2.7.1+cu118",
            torch_cuda_version="11.8",
            cuda_available=True,
            device_capabilities=["sm_120"],
            supported_architectures=["sm_37", "sm_80", "sm_90"],
            compatibility_error="PyTorchがこのGPU世代(sm_120)に対応していません。",
        ),
    )

    result = MMAudioRunner().run(job, lambda _message: None)

    assert not result.success
    assert "CUDA対応PyTorch" in (result.error_message or "")
