from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class PythonCandidate:
    version: tuple[int, int, int]
    path: Path


PY_LAUNCHER_LINE_RE = re.compile(r"-V:[^\d]*(\d+)\.(\d+)(?:\.(\d+))?.*?\s+(.+python\.exe)$", re.I)


def list_python_candidates() -> list[PythonCandidate]:
    candidates: list[PythonCandidate] = []
    try:
        completed = subprocess.run(
            ["py", "-0p"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            check=False,
            shell=False,
        )
    except Exception:
        completed = None

    if completed and completed.returncode == 0:
        for line in completed.stdout.splitlines():
            match = PY_LAUNCHER_LINE_RE.search(line.strip())
            if not match:
                continue
            major, minor, patch, raw_path = match.groups()
            path = Path(raw_path.strip())
            if path.exists():
                candidates.append(
                    PythonCandidate(
                        version=(int(major), int(minor), int(patch or 0)),
                        path=path,
                    )
                )

    current = Path(sys.executable)
    if current.exists():
        version = sys.version_info
        current_candidate = PythonCandidate(
            version=(version.major, version.minor, version.micro),
            path=current,
        )
        if all(candidate.path != current for candidate in candidates):
            candidates.append(current_candidate)

    return candidates


def choose_mmaudio_base_python() -> PythonCandidate | None:
    candidates = list_python_candidates()
    supported = [
        candidate
        for candidate in candidates
        if candidate.version >= (3, 10, 0) and candidate.version < (3, 13, 0)
    ]
    if not supported:
        return None

    # Prefer 3.10/3.11 for wider scientific-package wheel compatibility.
    preferred_minors = {10: 0, 11: 1, 12: 2}
    return sorted(
        supported,
        key=lambda candidate: (
            preferred_minors.get(candidate.version[1], 99),
            -candidate.version[2],
        ),
    )[0]
