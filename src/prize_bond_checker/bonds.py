"""Load, import, and save bond numbers — supports bulk files."""

from __future__ import annotations

import re
from pathlib import Path

BOND_PATTERN = re.compile(r"\b\d{6}\b")


def normalize_bond(value: str) -> str:
    digits = re.sub(r"\D", "", value.strip())
    if not digits:
        raise ValueError(f"Invalid bond number: {value!r}")
    return digits.zfill(6)[-6:]


def extract_bonds_from_text(text: str) -> set[str]:
    """Find every 6-digit bond number in any text (CSV, Excel export, paste dump)."""
    return {normalize_bond(match.group(0)) for match in BOND_PATTERN.finditer(text)}


def read_source_file(path: Path) -> str:
    suffix = path.suffix.lower()

    if suffix in {".xlsx", ".xlsm"}:
        return _read_xlsx(path)

    if suffix == ".xls":
        raise ValueError(
            "Old .xls files are not supported. Open in Excel and Save As .xlsx or .csv"
        )

    return path.read_text(encoding="utf-8", errors="ignore")


def _read_xlsx(path: Path) -> str:
    try:
        import openpyxl
    except ImportError as exc:
        raise ImportError(
            "Excel import requires openpyxl. Install with: pip install openpyxl"
        ) from exc

    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    chunks: list[str] = []

    for sheet in workbook.worksheets:
        for row in sheet.iter_rows(values_only=True):
            for cell in row:
                if cell is not None:
                    chunks.append(str(cell))

    workbook.close()
    return "\n".join(chunks)


def import_bonds_from_file(path: Path) -> set[str]:
    if not path.exists():
        raise FileNotFoundError(f"Import file not found: {path}")

    text = read_source_file(path)
    bonds = extract_bonds_from_text(text)

    if not bonds:
        raise ValueError(
            f"No 6-digit bond numbers found in {path}. "
            "Supported: .txt, .csv, .xlsx — bonds can be separated by commas, spaces, or new lines."
        )

    return bonds


def load_bonds(path: Path) -> set[str]:
    if not path.exists():
        raise FileNotFoundError(f"Bond file not found: {path}")

    bonds = extract_bonds_from_text(path.read_text(encoding="utf-8"))

    if not bonds:
        raise ValueError(f"No bond numbers found in {path}")

    return bonds


def save_bonds(path: Path, bonds: set[str]) -> None:
    header = "# Prize bond numbers (one per line)\n# Import bulk: python check_prize_bonds.py --import your_file.csv\n"
    body = "\n".join(sorted(bonds))
    path.write_text(f"{header}{body}\n", encoding="utf-8")


def merge_import(path: Path, source: Path, replace: bool = False) -> tuple[int, int, int]:
    """Import from source into path. Returns (imported_count, added_count, total_count)."""
    imported = import_bonds_from_file(source)

    if replace or not path.exists():
        merged = imported
        added = len(imported)
    else:
        existing = load_bonds(path)
        merged = existing | imported
        added = len(merged) - len(existing)

    save_bonds(path, merged)
    return len(imported), added, len(merged)
