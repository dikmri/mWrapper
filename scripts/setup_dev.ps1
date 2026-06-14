param(
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"

& $Python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
& .\.venv\Scripts\python.exe -m pip install -e ".[dev]"

Write-Host "Development environment is ready."
