from pathlib import Path

import pytest

from prize_bond_checker.bonds import (
    extract_bonds_from_text,
    import_bonds_from_file,
    load_bonds,
    merge_import,
    save_bonds,
)


def test_extract_bonds_from_comma_separated():
    text = "477670, 436083, 022667, 954217"
    assert extract_bonds_from_text(text) == {"477670", "436083", "022667", "954217"}


def test_extract_bonds_from_multiline_and_spaces():
    text = """
    477670 436083
    022667,954217
    """
    assert len(extract_bonds_from_text(text)) == 4


def test_extract_bonds_from_csv_with_headers():
    text = "bond_number,notes\n477670,home\n436083,office\n"
    bonds = extract_bonds_from_text(text)
    assert "477670" in bonds
    assert "436083" in bonds


def test_import_from_csv_file(tmp_path: Path):
    source = tmp_path / "bonds.csv"
    source.write_text("bond\n477670\n436083\n022667\n", encoding="utf-8")
    target = tmp_path / "bonds.txt"

    imported, added, total = merge_import(target, source)
    assert imported == 3
    assert added == 3
    assert total == 3
    assert load_bonds(target) == {"477670", "436083", "022667"}


def test_import_merges_without_duplicates(tmp_path: Path):
    target = tmp_path / "bonds.txt"
    save_bonds(target, {"477670", "022667"})

    source = tmp_path / "new.csv"
    source.write_text("477670,436083\n", encoding="utf-8")

    imported, added, total = merge_import(target, source)
    assert imported == 2
    assert added == 1
    assert total == 3


def test_import_replace_overwrites(tmp_path: Path):
    target = tmp_path / "bonds.txt"
    save_bonds(target, {"111111"})

    source = tmp_path / "new.csv"
    source.write_text("477670,436083\n", encoding="utf-8")

    imported, added, total = merge_import(target, source, replace=True)
    assert total == 2
    assert load_bonds(target) == {"477670", "436083"}


def test_import_from_txt_file(tmp_path: Path):
    source = tmp_path / "dump.txt"
    source.write_text("bonds: 477670 436083 022667", encoding="utf-8")
    bonds = import_bonds_from_file(source)
    assert len(bonds) == 3
