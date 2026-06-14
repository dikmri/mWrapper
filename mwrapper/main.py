from __future__ import annotations

import sys


def main() -> int:
    try:
        from .app import run
    except ImportError as exc:
        print(
            "mWrapper requires PySide6. Install dependencies with:\n"
            "  python -m pip install -r requirements.txt\n\n"
            f"Import error: {exc}",
            file=sys.stderr,
        )
        return 1

    return run(sys.argv)
