$ErrorActionPreference = 'Stop'
$python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'Run Setup.ps1 first, or ask ChatGPT to set up the editor.' }
Push-Location -LiteralPath $PSScriptRoot
try {
    if ($args.Count -eq 0) { & $python -m swarag doctor }
    else { & $python -m swarag @args }
    exit $LASTEXITCODE
} finally { Pop-Location }
