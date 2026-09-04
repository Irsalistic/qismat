@echo off
cd /d "%~dp0"
python -m prize_bond_checker web --open
if errorlevel 1 python check_prize_bonds.py web --open
if errorlevel 1 (
  echo.
  echo Could not start the dashboard. Install dependencies first:
  echo   pip install -r requirements.txt
  echo   pip install -e .
  pause
)
