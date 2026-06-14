from __future__ import annotations

import shutil
from pathlib import Path

from mwrapper.core.paths import default_temp_dir


def main() -> int:
    temp_dir = default_temp_dir()
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir(parents=True, exist_ok=True)
    print(f"Cleaned {temp_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
