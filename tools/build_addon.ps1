Param(
    [string]$Package = 'AnkiAutoImage',
    [string]$Name = 'Auto Images (Google/Nadeshiko/GenAI)',
    [string]$Homepage = 'https://ankiweb.net/shared/addons/',
    [string]$Output = 'AnkiAutoImage.ankiaddon',
    [switch]$SkipVendor
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Move to repo root (this script lives in tools/)
$scriptDir = Split-Path -Parent $PSCommandPath
$root = Split-Path -Parent $scriptDir
Set-Location $root

Write-Host "[1/4] Vendoring dependencies (use -SkipVendor to skip)" -ForegroundColor Cyan
if (-not $SkipVendor) {
    & py -3 tools\vendor_deps.py
}

Write-Host "[2/4] Cleaning caches" -ForegroundColor Cyan
Get-ChildItem -Recurse -Directory -Filter __pycache__ | Remove-Item -Recurse -Force -ErrorAction Ignore
Get-ChildItem -Recurse -Filter *.pyc | Remove-Item -Force -ErrorAction Ignore

Write-Host "[3/4] Staging files" -ForegroundColor Cyan
$stage = Join-Path $env:TEMP 'anki_autoimage_stage'
Remove-Item $stage -Recurse -Force -ErrorAction Ignore
New-Item $stage -ItemType Directory | Out-Null

$files = @(
  '__init__.py','tools.py','anki_util.py','ddg_api.py','yahoo_api.py',
  'google_cse.py','google_genai.py','nadeshiko_api.py','pexels_api.py',
  'browser_provider.py','logger.py','config.json','README.md','nadeshiko-api.json'
)
foreach ($f in $files) { Copy-Item $f -Destination $stage }
if (Test-Path 'vendor') { Copy-Item 'vendor' -Destination $stage -Recurse }

# Add manifest.json expected by AnkiWeb installer
$manifest = @{ package = $Package; name = $Name; homepage = $Homepage } | ConvertTo-Json -Compress
Set-Content -Path (Join-Path $stage 'manifest.json') -Value $manifest -Encoding UTF8

Write-Host "[4/4] Creating archive" -ForegroundColor Cyan
$zip = Join-Path $root 'AnkiAutoImage.zip'
Remove-Item $zip -ErrorAction Ignore
Compress-Archive -Path (Join-Path $stage '*') -DestinationPath $zip -Force
$dest = Join-Path $root $Output
Remove-Item $dest -ErrorAction Ignore
Rename-Item -Path $zip -NewName (Split-Path $dest -Leaf)

Write-Host "Done ->" (Resolve-Path $dest) -ForegroundColor Green

