param(
    [string]$ZipName = "mWrapper-windows.zip",
    [string]$ReleaseDir = "release"
)

$ErrorActionPreference = "Stop"

$Root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$ReleasePath = Join-Path $Root $ReleaseDir
$DistPath = Join-Path $Root "dist"
$WorkPath = Join-Path $Root "build\pyinstaller"
$IconPath = Join-Path $Root "mwrapper\resources\icons\icon.png"
$BuildIconPath = Join-Path $Root "build\icon.ico"
$LauncherPath = Join-Path $Root "mwrapper_launcher.py"
$AppDir = Join-Path $DistPath "mWrapper"
$ZipPath = Join-Path $ReleasePath $ZipName

New-Item -ItemType Directory -Force -Path $ReleasePath | Out-Null
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $BuildIconPath) | Out-Null

Add-Type -AssemblyName System.Drawing
$bitmap = [System.Drawing.Bitmap]::new($IconPath)
try {
    $icon = [System.Drawing.Icon]::FromHandle($bitmap.GetHicon())
    try {
        $stream = [System.IO.File]::Create($BuildIconPath)
        try {
            $icon.Save($stream)
        }
        finally {
            $stream.Dispose()
        }
    }
    finally {
        $icon.Dispose()
    }
}
finally {
    $bitmap.Dispose()
}

python -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --name mWrapper `
    --icon $BuildIconPath `
    --add-data "$IconPath;mwrapper/resources/icons" `
    --distpath $DistPath `
    --workpath $WorkPath `
    --specpath $WorkPath `
    $LauncherPath

if (-not (Test-Path -LiteralPath (Join-Path $AppDir "mWrapper.exe"))) {
    throw "mWrapper.exe was not created: $AppDir"
}

if (Test-Path -LiteralPath $ZipPath) {
    Remove-Item -LiteralPath $ZipPath -Force
}

$AppContents = Get-ChildItem -LiteralPath $AppDir
$compressed = $false
for ($attempt = 1; $attempt -le 5; $attempt++) {
    try {
        if (Test-Path -LiteralPath $ZipPath) {
            Remove-Item -LiteralPath $ZipPath -Force
        }
        Compress-Archive -LiteralPath $AppContents.FullName -DestinationPath $ZipPath -Force -ErrorAction Stop
        $compressed = $true
        break
    }
    catch {
        if ($attempt -eq 5) {
            throw
        }
        Start-Sleep -Seconds 2
    }
}

if (-not $compressed) {
    throw "Failed to create $ZipPath"
}

Write-Host "Created $ZipPath"
