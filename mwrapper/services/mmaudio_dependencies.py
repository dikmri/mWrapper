from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class MMAudioDependencyInfo:
    executable: str
    versions: dict[str, str | None] = field(default_factory=dict)
    import_errors: dict[str, str] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.import_errors


def inspect_mmaudio_dependencies(
    python_executable: str,
    cwd: Path | None = None,
    timeout_seconds: int = 30,
) -> MMAudioDependencyInfo:
    code = r"""
import importlib
import importlib.metadata as md
import json
import sys

packages = ["numpy", "numba", "librosa", "soundfile"]
data = {
    "executable": sys.executable,
    "versions": {},
    "import_errors": {},
}

for package in packages:
    try:
        data["versions"][package] = md.version(package)
    except Exception:
        data["versions"][package] = None

for module in packages:
    try:
        importlib.import_module(module)
    except Exception as exc:
        data["import_errors"][module] = f"{type(exc).__name__}: {exc}"

print(json.dumps(data, ensure_ascii=False))
"""
    executable = python_executable.strip() or "python"
    try:
        completed = subprocess.run(
            [executable, "-c", code],
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            check=False,
            shell=False,
        )
    except Exception as exc:
        return MMAudioDependencyInfo(
            executable=executable,
            import_errors={"python": str(exc)},
        )

    if completed.returncode != 0:
        details = completed.stderr.strip() or completed.stdout.strip()
        return MMAudioDependencyInfo(
            executable=executable,
            import_errors={"python": details or "Dependency check failed"},
        )

    try:
        data = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        return MMAudioDependencyInfo(
            executable=executable,
            import_errors={"python": f"Invalid dependency check output: {exc}"},
        )

    return MMAudioDependencyInfo(
        executable=str(data.get("executable") or executable),
        versions=dict(data.get("versions") or {}),
        import_errors=dict(data.get("import_errors") or {}),
    )


def format_mmaudio_dependency_info(info: MMAudioDependencyInfo) -> str:
    versions = ", ".join(
        f"{name}={version or '未導入'}" for name, version in info.versions.items()
    )
    if info.ok:
        return f"MMAudio依存確認: OK / Python: {info.executable} / {versions}"

    errors = "; ".join(f"{name}: {error}" for name, error in info.import_errors.items())
    message = (
        f"MMAudio依存確認: エラー / Python: {info.executable} / "
        f"{versions} / 詳細: {errors}"
    )
    numpy_version = info.versions.get("numpy")
    if numpy_version and numpy_version.startswith("2.4"):
        message += " / NumPy 2.4系はnumbaと互換性がありません。MMAudio依存修復を実行してください。"
    return message
