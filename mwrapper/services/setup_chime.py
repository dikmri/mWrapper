from __future__ import annotations

import io
import math
import struct
import threading
import wave


SAMPLE_RATE = 44_100


def play_setup_complete_chime() -> None:
    thread = threading.Thread(target=_play_setup_complete_chime, daemon=True)
    thread.start()


def build_setup_complete_chime_wav() -> bytes:
    notes = [
        (523.25, 0.16),
        (659.25, 0.16),
        (783.99, 0.20),
        (1046.50, 0.34),
    ]
    samples: list[int] = []
    for frequency, duration in notes:
        samples.extend(_tone_samples(frequency, duration))
    samples.extend([0] * int(SAMPLE_RATE * 0.06))

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(b"".join(struct.pack("<h", sample) for sample in samples))
    return buffer.getvalue()


def _play_setup_complete_chime() -> None:
    try:
        import winsound

        winsound.PlaySound(build_setup_complete_chime_wav(), winsound.SND_MEMORY)
    except Exception:
        try:
            print("\a", end="", flush=True)
        except Exception:
            pass


def _tone_samples(frequency: float, duration: float) -> list[int]:
    count = int(SAMPLE_RATE * duration)
    attack = max(1, int(SAMPLE_RATE * 0.012))
    release = max(1, int(SAMPLE_RATE * 0.05))
    samples: list[int] = []
    for i in range(count):
        envelope = 1.0
        if i < attack:
            envelope = i / attack
        elif i > count - release:
            envelope = max(0.0, (count - i) / release)

        t = i / SAMPLE_RATE
        fundamental = math.sin(2 * math.pi * frequency * t)
        overtone = 0.22 * math.sin(2 * math.pi * frequency * 2 * t)
        samples.append(int(19_000 * envelope * (fundamental + overtone) / 1.22))
    return samples
