from pathlib import Path

import pytest

from prize_bond_checker.bonds import load_bonds, normalize_bond
from prize_bond_checker.checker import find_wins
from prize_bond_checker.scraper import parse_draw_html

FIXTURES = Path(__file__).parent / "fixtures"


def test_normalize_bond_zero_pads():
    assert normalize_bond("22667") == "022667"
    assert normalize_bond(" 010204 ") == "010204"


def test_normalize_bond_rejects_empty():
    with pytest.raises(ValueError):
        normalize_bond("abc")


def test_load_bonds(tmp_path: Path):
    bonds_file = tmp_path / "bonds.txt"
    bonds_file.write_text("# comment\n022667\n010204\n", encoding="utf-8")

    bonds = load_bonds(bonds_file)
    assert bonds == {"022667", "010204"}


def test_parse_draw_html_extracts_all_tiers():
    html = (FIXTURES / "sample_draw.html").read_text(encoding="utf-8")
    draw = parse_draw_html(html, denomination=200, draw_date="2026-03-16")

    assert draw.draw_number == "105"
    assert draw.city == "Faisalabad"
    assert draw.prizes["1st"] == {"591284"}
    assert draw.prizes["2nd"] == {"293000", "811470", "721418", "473127", "659859"}
    assert "022667" in draw.prizes["3rd"]
    assert "010204" in draw.prizes["3rd"]


def test_find_wins_returns_tier_and_amount():
    html = (FIXTURES / "sample_draw.html").read_text(encoding="utf-8")
    draw = parse_draw_html(html, denomination=200, draw_date="2026-03-16")
    wins = find_wins({"022667", "123456"}, draw)

    assert len(wins) == 1
    assert wins[0].bond == "022667"
    assert wins[0].tier == "3rd"
    assert wins[0].amount == "Rs. 1,250"
