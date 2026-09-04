"""Install or print a daily auto-check (Windows Task Scheduler or cron)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from prize_bond_checker.constants import LOG_FILENAME

TASK_NAME = "PrizeBondCheckerDaily"


def check_args() -> str:
    return "--all --latest --notify --skip-checked --summary --ai-provider none"


def ensure_runner(workdir: Path) -> Path:
    """Write a small .bat so Task Scheduler does not have to fight quoting."""
    runner = workdir / "run-daily-check.bat"
    python = sys.executable
    log_path = workdir / LOG_FILENAME
    runner.write_text(
        "@echo off\r\n"
        f'cd /d "{workdir}"\r\n'
        f'"{python}" -m prize_bond_checker {check_args()} >> "{log_path}" 2>&1\r\n',
        encoding="utf-8",
    )
    return runner


def cron_line(workdir: Path, hour: int = 20, minute: int = 0) -> str:
    return (
        f"{minute} {hour} * * * cd {workdir} && "
        f"{sys.executable} -m prize_bond_checker {check_args()} "
        f">> {workdir / LOG_FILENAME} 2>&1"
    )


def install_windows_task(workdir: Path, hour: int = 20, minute: int = 0) -> str:
    start = f"{hour:02d}:{minute:02d}"
    runner = ensure_runner(workdir)
    completed = subprocess.run(
        [
            "schtasks",
            "/Create",
            "/TN",
            TASK_NAME,
            "/TR",
            str(runner),
            "/SC",
            "DAILY",
            "/ST",
            start,
            "/F",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "unknown error").strip()
        raise RuntimeError(detail)
    return (completed.stdout or f"Created daily task {TASK_NAME} at {start}.").strip()


def remove_windows_task() -> str:
    completed = subprocess.run(
        ["schtasks", "/Delete", "/TN", TASK_NAME, "/F"],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "unknown error").strip()
        raise RuntimeError(detail)
    return (completed.stdout or f"Removed task {TASK_NAME}.").strip()


def task_exists() -> bool:
    completed = subprocess.run(
        ["schtasks", "/Query", "/TN", TASK_NAME],
        check=False,
        capture_output=True,
        text=True,
    )
    return completed.returncode == 0
