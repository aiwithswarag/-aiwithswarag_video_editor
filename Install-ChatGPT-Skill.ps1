param([string]$Destination = (Join-Path $env:USERPROFILE '.codex\skills\swarag-video-director'))
$ErrorActionPreference = 'Stop'
$source = Join-Path $PSScriptRoot '.agents\skills\swarag-video-director'
New-Item -ItemType Directory -Path $Destination -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $source 'SKILL.md') -Destination $Destination -Force
New-Item -ItemType Directory -Path (Join-Path $Destination 'scripts') -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $source 'scripts\run.py') -Destination (Join-Path $Destination 'scripts') -Force
@{ root = $PSScriptRoot } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $Destination 'installation.json') -Encoding utf8
Write-Host "Installed Swarag Video Director skill at $Destination"
