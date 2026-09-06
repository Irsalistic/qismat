# Daily auto-check via Windows Task Scheduler
# Usage: powershell -ExecutionPolicy Bypass -File scripts/install-daily-check.ps1

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

python -m qismat schedule --install
if ($LASTEXITCODE -ne 0) {
    python check_prize_bonds.py schedule --install
}
