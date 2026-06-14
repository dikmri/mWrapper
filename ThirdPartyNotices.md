# Third Party Notices

mWrapper does not vendor model weights, MMAudio, FFmpeg binaries, PyTorch, or generated media.

| Component | Purpose | License / Notice |
|---|---|---|
| MMAudio | Audio generation backend | Upstream code is reported as MIT. Model weights may have separate terms. |
| NSFW_MMaudio | Model repository | Hugging Face page reports MIT. Weights are not bundled. |
| PySide6 | GUI | Qt for Python licensing includes LGPLv3/GPL/commercial options. |
| PyTorch | Inference runtime | Governed by PyTorch license terms. Not required by mWrapper core unless MMAudio uses it. |
| huggingface_hub | Future model download support | Apache-2.0 style license. Optional for setup flows. |
| Google Cloud Translation API | Future Japanese-to-English translation | Governed by Google Cloud terms. |
| FFmpeg / ffprobe | Video metadata and media processing | LGPL/GPL configuration matters. Binaries are not bundled. |
| PyInstaller | Windows executable packaging | Packaging output is subject to bundled dependency licenses. |

Users are responsible for complying with all licenses and laws that apply to their local models, tools, and media.
