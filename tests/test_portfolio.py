from pathlib import Path

import pytest

from prize_bond_checker.portfolio import add_holding, load_portfolio, remove_holding


def test_load_flat_file(tmp_path: Path):
    path = tmp_path / "bonds.txt"
    path.write_text("# comment\n22667\n010204\n", encoding="utf-8")
    portfolio = load_portfolio(path)
    assert {item.number for item in portfolio.holdings} == {"022667", "010204"}
    assert portfolio.has_sections is False
    assert portfolio.grouped()[200][0].number in {"022667", "010204"}


def test_load_sections_and_owners(tmp_path: Path):
    path = tmp_path / "bonds.txt"
    path.write_text(
        "[200]\n477670\n\n[750:parents]\n123456\n",
        encoding="utf-8",
    )
    portfolio = load_portfolio(path)
    grouped = portfolio.grouped()
    assert [item.number for item in grouped[200]] == ["477670"]
    assert grouped[750][0].owner == "parents"
    assert portfolio.holdings_for(750, include_unsectioned=False)[0].number == "123456"


def test_unsectioned_numbers_follow_explicit_denomination(tmp_path: Path):
    path = tmp_path / "bonds.txt"
    path.write_text("022667\n", encoding="utf-8")
    portfolio = load_portfolio(path)
    holdings = portfolio.holdings_for(750, include_unsectioned=True)
    assert [item.number for item in holdings] == ["022667"]


def test_add_and_remove_holding(tmp_path: Path):
    path = tmp_path / "bonds.txt"
    assert add_holding(path, "22667", 200, "ali") is True
    assert add_holding(path, "022667", 200, "ali") is False
    portfolio = load_portfolio(path)
    assert portfolio.holdings[0].owner == "ali"
    assert remove_holding(path, "022667", 200) is True
    text = path.read_text(encoding="utf-8")
    assert "[200:ali]" not in text
    with pytest.raises(ValueError, match="No bond numbers"):
        load_portfolio(path)


def test_rejects_unknown_denomination_section(tmp_path: Path):
    path = tmp_path / "bonds.txt"
    path.write_text("[999]\n123456\n", encoding="utf-8")
    with pytest.raises(ValueError, match="unsupported denomination"):
        load_portfolio(path)
