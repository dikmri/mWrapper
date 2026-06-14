$ErrorActionPreference = "Stop"

$Repository = "dikmri/mWrapper"
$Version = if ($env:MWRAPPER_VERSION) { $env:MWRAPPER_VERSION } else { "latest" }
$InstallDir = if ($env:MWRAPPER_INSTALL_DIR) {
    $env:MWRAPPER_INSTALL_DIR
} else {
    Join-Path $env:LOCALAPPDATA "mWrapper\app"
}
$NoDesktopShortcut = $env:MWRAPPER_NO_DESKTOP_SHORTCUT -eq "1"
$LaunchAfterInstall = $env:MWRAPPER_LAUNCH -eq "1"

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

function Get-ReleaseInfo {
    param([string]$Repo, [string]$RequestedVersion)

    $headers = @{ "User-Agent" = "mWrapper-installer" }
    if ($RequestedVersion -eq "latest") {
        $url = "https://api.github.com/repos/$Repo/releases/latest"
    } else {
        $url = "https://api.github.com/repos/$Repo/releases/tags/$RequestedVersion"
    }

    Invoke-RestMethod -Uri $url -Headers $headers
}

function New-Shortcut {
    param(
        [string]$ShortcutPath,
        [string]$TargetPath,
        [string]$WorkingDirectory
    )

    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($ShortcutPath)
    $shortcut.TargetPath = $TargetPath
    $shortcut.WorkingDirectory = $WorkingDirectory
    $shortcut.IconLocation = $TargetPath
    $shortcut.Save()
}

$release = Get-ReleaseInfo -Repo $Repository -RequestedVersion $Version
$asset = $release.assets |
    Where-Object { $_.name -like "mWrapper-*-windows.zip" -or $_.name -eq "mWrapper-windows.zip" } |
    Select-Object -First 1

if (-not $asset) {
    throw "Windows exe zip asset was not found in release $($release.tag_name)."
}

$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("mWrapper-install-" + [Guid]::NewGuid().ToString("N"))
$zipPath = Join-Path $tempRoot $asset.name
$extractPath = Join-Path $tempRoot "extract"
$resolvedInstallDir = [System.IO.Path]::GetFullPath($InstallDir)
$installDriveRoot = [System.IO.Path]::GetPathRoot($resolvedInstallDir).TrimEnd("\")
if ($resolvedInstallDir.TrimEnd("\") -eq $installDriveRoot) {
    throw "Install directory must not be a drive root: $resolvedInstallDir"
}

try {
    New-Item -ItemType Directory -Force -Path $tempRoot, $extractPath | Out-Null

    Write-Host "Downloading mWrapper $($release.tag_name): $($asset.browser_download_url)"
    Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $zipPath -Headers @{ "User-Agent" = "mWrapper-installer" }

    Expand-Archive -LiteralPath $zipPath -DestinationPath $extractPath -Force
    $sourceExe = Get-ChildItem -LiteralPath $extractPath -Recurse -Filter "mWrapper.exe" | Select-Object -First 1
    if (-not $sourceExe) {
        throw "mWrapper.exe was not found in downloaded archive."
    }

    if (Test-Path -LiteralPath $resolvedInstallDir) {
        Remove-Item -LiteralPath $resolvedInstallDir -Recurse -Force
    }
    New-Item -ItemType Directory -Force -Path $resolvedInstallDir | Out-Null

    Get-ChildItem -LiteralPath $sourceExe.Directory.FullName | Copy-Item -Destination $resolvedInstallDir -Recurse -Force

    $installedExe = Join-Path $resolvedInstallDir "mWrapper.exe"
    if (-not (Test-Path -LiteralPath $installedExe)) {
        throw "Install failed. mWrapper.exe was not copied to $resolvedInstallDir."
    }

    $programsDir = [Environment]::GetFolderPath("Programs")
    $startMenuDir = Join-Path $programsDir "mWrapper"
    New-Item -ItemType Directory -Force -Path $startMenuDir | Out-Null
    New-Shortcut -ShortcutPath (Join-Path $startMenuDir "mWrapper.lnk") -TargetPath $installedExe -WorkingDirectory $resolvedInstallDir

    if (-not $NoDesktopShortcut) {
        $desktopDir = [Environment]::GetFolderPath("DesktopDirectory")
        New-Shortcut -ShortcutPath (Join-Path $desktopDir "mWrapper.lnk") -TargetPath $installedExe -WorkingDirectory $resolvedInstallDir
    }

    Write-Host "mWrapper $($release.tag_name) installed to $resolvedInstallDir"
    Write-Host "Start menu shortcut was created."

    if ($LaunchAfterInstall) {
        Start-Process -FilePath $installedExe -WorkingDirectory $resolvedInstallDir
    }
}
finally {
    if (Test-Path -LiteralPath $tempRoot) {
        Remove-Item -LiteralPath $tempRoot -Recurse -Force
    }
}
