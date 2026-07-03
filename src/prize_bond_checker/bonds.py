"""Load and normalize bond numbers from a file."""

from __future__ import annotations

import re
from pathlib import Path


def normalize_bond(value: str) -> str:
    digits = re.sub(r"\D", "", value.strip())
    if not digits:
        raise ValueError(f"Invalid bond number: {value!r}")
    return digits.zfill(6)[-6:]


def load_bonds(path: Path) -> set[str]:
    if not path.exists():
        raise FileNotFoundError(f"Bond file not found: {path}")

    bonds: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        bonds.add(normalize_bond(line))

    if not bonds:
        raise ValueError(f"No bond numbers found in {path}")

    return bonds
