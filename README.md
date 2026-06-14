# mWrapper

mWrapper is a beginner-friendly PySide6 GUI wrapper for MMAudio-based video-to-audio generation.

This repository currently implements the v0.1 MVP from `mWrapper_spec.md`:

- Drag and drop video input
- ffprobe-based video information display
- Positive and negative prompt input
- MMAudio / NSFW_MMaudio model switching
- Random seed by default, with optional fixed seed
- MMAudio `demo.py` CLI execution
- Live stdout/stderr log display
- Generated mp4 detection
- Built-in video preview
- Save as `<original_filename>_mmaudio.mp4`, with numbered names on conflict
- First-run automatic setup for MMAudio, NSFW_MMaudio weights, the dedicated venv, and PyTorch

## Important Safety Notice

Use only with legal, consenting adult content.

Prohibited uses:

- minors or minor-looking sexual content
- non-consensual material
- voyeuristic or leaked material
- revenge pornography
- unauthorized sexual manipulation of real people
- illegal or rights-infringing content

## Installation

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Install FFmpeg separately and make sure `ffmpeg` and `ffprobe` are available on `PATH`.

## Running

```powershell
python -m mwrapper
```

On first launch, mWrapper asks where to build its dedicated setup. It estimates the missing setup size and rejects locations whose drive does not have enough free space. If MMAudio, NSFW_MMaudio weights, or the dedicated venv are missing, setup then starts automatically in the background.

In normal use:

1. Drop a video file.
2. Choose `NSFW_MMaudio` or `MMAudio`.
3. Enter a positive prompt and, optionally, a negative prompt.
4. Leave `seed固定` off for a new random result each run, or turn it on to reuse the displayed seed.
5. Click Generate.
6. Preview the result and save it.

The main window accepts video drag and drop anywhere. Environment controls are intentionally hidden from normal use; use `初期化` only when the dedicated setup is broken or you want to rebuild it in another folder. Prompt text is saved on exit and restored on the next launch.

## MMAudio Setup

mWrapper does not include MMAudio, model weights, FFmpeg binaries, or third-party model files. Configure these separately according to their own instructions and licenses.

The `MMAudio取得` button downloads the official MMAudio source ZIP from GitHub into the local mWrapper tools directory and automatically fills the `demo.py` path. First-run setup also downloads the NSFW_MMaudio checkpoint to `weights/nsfw_gold_8.5k_final.pth` and patches MMAudio's `demo.py` so it can be selected as the `nsfw_mmaudio` variant.

## CUDA / GPU Setup

MMAudio uses GPU only when the Python environment that runs `demo.py` has a CUDA-enabled PyTorch build. If that environment has a CPU-only build such as `torch ... +cpu`, MMAudio will run on CPU even if the machine has an NVIDIA GPU.

Use `CUDA確認` in the app to inspect the selected `MMAudio Python`. The app defaults to `CUDA必須`, so generation is blocked before launch when CUDA is unavailable instead of silently running on CPU.

First-run setup creates a dedicated MMAudio virtual environment with Python 3.10-3.12, PyTorch, and MMAudio dependencies. It checks NVIDIA hardware with `nvidia-smi` and selects the PyTorch wheel index automatically. For NVIDIA GPUs, mWrapper defaults to CUDA 12.8, matching PyTorch's current Windows pip selector and avoiding older wheel/GPU architecture mismatches. This avoids dependency conflicts in a global Python 3.13 environment and keeps MMAudio packages out of other Python environments.

mWrapper does not build a full ComfyUI environment. The large pieces are the CUDA PyTorch wheel set, MMAudio/NSFW_MMaudio model weights, and runtime model caches such as Hugging Face/OpenCLIP assets. To reduce C: drive pressure, setup uses no-cache pip/uv installs and routes runtime Hugging Face/Torch caches under the selected setup folder.

When `uv` is available, `専用venv作成` uses `uv venv --clear --seed` and `uv pip install --python <venv_python>`. If a dedicated venv already exists, it is rebuilt so stale CPU-only or older CUDA PyTorch installs are removed. If `uv` is not installed, it falls back to Python's built-in `venv --clear` plus pip inside that venv.

The `CUDA PyTorch導入` button modifies the selected `MMAudio Python` environment directly. Prefer `専用venv作成` unless you intentionally want to change that selected environment. When `uv` is available, it runs without requiring pip inside the selected environment:

```powershell
uv pip install --python <MMAudio Python> --reinstall torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128
```

Without `uv`, it falls back to:

```powershell
python -m pip install --upgrade --force-reinstall torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128
```

MMAudio's README recommends installing PyTorch first and choosing a CUDA build that matches the GPU/driver. PyTorch's official installer currently lists CUDA 12.8 for pip installs, which is the default used by mWrapper. See the official PyTorch installation selector if CUDA 12.8 is not suitable for your environment: https://pytorch.org/get-started/locally/

`CUDA確認` also checks the GPU compute capability against the architectures supported by the selected PyTorch wheel. For example, RTX 50 series GPUs report `sm_120`; older CUDA 11.8 wheels may report CUDA as available but still fail at runtime because they only support older architectures.

## MMAudio Dependency Repair

If generation fails with an error like:

```text
ImportError: Numba needs NumPy 2.3 or less. Got NumPy 2.4.
```

the selected Python environment has an incompatible NumPy/numba combination. Use `専用venv作成` first. `MMAudio依存修復` modifies the selected `MMAudio Python` environment directly and should only be used intentionally.

When `uv` is available, `MMAudio依存修復` runs:

```powershell
uv pip install --python <MMAudio Python> --upgrade -e . "numpy<2.1,>=1.21" "soundfile>=0.12"
```

from the MMAudio repository directory, matching MMAudio's own `numpy >= 1.21, <2.1` requirement. Without `uv`, it falls back to `python -m pip install --upgrade -e . "numpy<2.1,>=1.21" "soundfile>=0.12"`.

On Windows, recent `torchaudio.save()` versions use TorchCodec internally. TorchCodec requires compatible FFmpeg shared DLLs, not just an `ffmpeg.exe` command on PATH. mWrapper avoids that fragile path by patching MMAudio's `demo.py` to save audio with `soundfile` before launching generation.

The v0.1 runner calls MMAudio in this shape:

```powershell
python demo.py --duration=8 --video="<input_video>" --prompt="<english_prompt>"
```

Current mWrapper calls MMAudio with explicit variant and seed values:

```powershell
python demo.py --variant=nsfw_mmaudio --duration=8 --video="<input_video>" --prompt="<positive_prompt>" --negative_prompt="<negative_prompt>" --seed=123
```

If your local MMAudio checkout uses different arguments, update the runner configuration or code before generation.

## License

mWrapper itself is licensed under the MIT License.

This repository does not include MMAudio model weights, NSFW_MMaudio model weights, FFmpeg binaries, or third-party model files. These components are downloaded or configured separately by the user and are governed by their respective licenses.

Users are responsible for ensuring that their use of third-party models and tools complies with all applicable licenses and laws.
