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

function Convert-PngToIco {
    param(
        [Parameter(Mandatory = $true)][string]$SourcePng,
        [Parameter(Mandatory = $true)][string]$DestinationIco,
        [int[]]$Sizes = @(256, 128, 64, 48, 32, 16)
    )

    Add-Type -AssemblyName System.Drawing
    $source = [System.Drawing.Bitmap]::new($SourcePng)
    try {
        $images = New-Object System.Collections.Generic.List[object]
        foreach ($size in $Sizes) {
            $bitmap = [System.Drawing.Bitmap]::new($size, $size, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
            $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
            $stream = [System.IO.MemoryStream]::new()
            try {
                $graphics.Clear([System.Drawing.Color]::Transparent)
                $graphics.CompositingQuality = [System.Drawing.Drawing2D.CompositingQuality]::HighQuality
                $graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
                $graphics.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
                $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality

                $scale = [Math]::Min($size / $source.Width, $size / $source.Height)
                $width = [Math]::Max(1, [int][Math]::Round($source.Width * $scale))
                $height = [Math]::Max(1, [int][Math]::Round($source.Height * $scale))
                $x = [int][Math]::Floor(($size - $width) / 2)
                $y = [int][Math]::Floor(($size - $height) / 2)
                $graphics.DrawImage($source, $x, $y, $width, $height)
                $bitmap.Save($stream, [System.Drawing.Imaging.ImageFormat]::Png)
                $images.Add([pscustomobject]@{
                    Size = $size
                    Bytes = $stream.ToArray()
                })
            }
            finally {
                $stream.Dispose()
                $graphics.Dispose()
                $bitmap.Dispose()
            }
        }

        $file = [System.IO.File]::Create($DestinationIco)
        $writer = [System.IO.BinaryWriter]::new($file)
        try {
            $writer.Write([UInt16]0)
            $writer.Write([UInt16]1)
            $writer.Write([UInt16]$images.Count)
            $offset = 6 + (16 * $images.Count)
            foreach ($image in $images) {
                $sizeByte = if ($image.Size -eq 256) { 0 } else { [byte]$image.Size }
                $writer.Write([byte]$sizeByte)
                $writer.Write([byte]$sizeByte)
                $writer.Write([byte]0)
                $writer.Write([byte]0)
                $writer.Write([UInt16]1)
                $writer.Write([UInt16]32)
                $writer.Write([UInt32]$image.Bytes.Length)
                $writer.Write([UInt32]$offset)
                $offset += $image.Bytes.Length
            }
            foreach ($image in $images) {
                $writer.Write([byte[]]$image.Bytes)
            }
        }
        finally {
            $writer.Dispose()
            $file.Dispose()
        }
    }
    finally {
        $source.Dispose()
    }
}

Convert-PngToIco -SourcePng $IconPath -DestinationIco $BuildIconPath

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
