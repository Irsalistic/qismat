#!/usr/bin/env python3
"""Backward-compatible entry point."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from prize_bond_checker.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
