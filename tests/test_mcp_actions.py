from pathlib import Path

import pytest

mcp = pytest.importorskip("mcp")

from prize_bond_checker import mcp_server


def test_mcp_add_bond_and_list(monkeypatch, tmp_path: Path):
    bonds = tmp_path / "bonds.txt"
    bonds.write_text("[200]\n022667\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    result = mcp_server.add_bond("477670", 200, "ali")
    assert result["ok"] is True
    assert result["added"] == ["477670"]

    listed = mcp_server.list_bonds()
    numbers = {item["number"] for item in listed["bonds"]}
    assert numbers == {"022667", "477670"}

    speech = mcp_server.add_bonds_from_speech("oh two two six six seven")
    assert speech["ok"] is True
    assert speech["skipped"] == ["022667"]


def test_mcp_add_bond_rejects_bad_number(monkeypatch, tmp_path: Path):
    monkeypatch.chdir(tmp_path)
    result = mcp_server.add_bond("abc", 200, "")
    assert result["ok"] is False
    assert "hint" in result
