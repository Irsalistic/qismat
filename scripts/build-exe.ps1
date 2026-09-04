# Build a Windows .exe with PyInstaller
# Usage: powershell -ExecutionPolicy Bypass -File scripts/build-exe.ps1

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

python -m pip install pyinstaller flask requests beautifulsoup4
python -m PyInstaller --noconfirm prize-bond-checker.spec

Write-Host "Built dist\prize-bond-checker.exe"
Write-Host "Copy bonds.txt next to the exe, then run: prize-bond-checker.exe web --open"
