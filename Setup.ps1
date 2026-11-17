param([string]$PythonPath, [switch]$SkipFFmpeg)
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$projectRoot = $PSScriptRoot
Set-Location -LiteralPath $projectRoot
if (-not $PythonPath) {
    $candidates = @()
    foreach ($name in @('python','python3','py')) {
        $command = Get-Command $name -ErrorAction SilentlyContinue
        if ($command) { $candidates += $command.Source }
    }
    $runtimePackages = Get-ChildItem -LiteralPath 'C:\Program Files\WindowsApps' -Directory -Filter 'OpenAI.CodexPrimaryRuntime*' -ErrorAction SilentlyContinue
    foreach ($package in $runtimePackages) { $candidates += Join-Path $package.FullName 'dependencies\python\python.exe' }
    foreach ($candidate in $candidates) {
        if (-not (Test-Path -LiteralPath $candidate)) { continue }
        try {
            & $candidate -c "import sys; sys.exit(0 if sys.version_info[:2] == (3,12) else 1)" 2>$null
            if ($LASTEXITCODE -eq 0) { $PythonPath = $candidate; break }
        } catch { }
    }
}
if (-not $PythonPath) { throw 'Python 3.12 is required. Ask ChatGPT/Codex to install it, then rerun Setup.ps1.' }
$venvPython = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $venvPython)) {
    & $PythonPath -m venv (Join-Path $projectRoot '.venv')
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the Python environment.' }
}
& $venvPython -m pip install -r (Join-Path $projectRoot 'requirements.lock.txt')
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
if (-not $SkipFFmpeg) {
    $toolRoot = Join-Path $projectRoot '.tools'
    $ffmpegExe = Join-Path $toolRoot 'ffmpeg\ffmpeg-9.0.2-essentials_build\bin\ffmpeg.exe'
    if (-not (Test-Path -LiteralPath $ffmpegExe)) {
        New-Item -ItemType Directory -Path $toolRoot -Force | Out-Null
        $archivePath = Join-Path $toolRoot 'ffmpeg-9.0.2.zip'
        Invoke-WebRequest -Uri 'https://github.com/GyanD/codexffmpeg/releases/download/9.0.2/ffmpeg-9.0.2-essentials_build.zip' -OutFile $archivePath -TimeoutSec 120
        $actual = (Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash
        if ($actual -ne '60f467265b1e312373dbcd92200c2618a74850f98d3d078e94296bb3fa2047ba') { throw 'FFmpeg checksum mismatch; refusing to install.' }
        Expand-Archive -LiteralPath $archivePath -DestinationPath (Join-Path $toolRoot 'ffmpeg') -Force
    }
}
& $venvPython -m swarag doctor
if ($LASTEXITCODE -ne 0) { throw 'The installation did not pass its health check.' }
Write-Host 'Swarag Video Director is ready. Open this folder in ChatGPT Work/Codex and describe your edit.'
