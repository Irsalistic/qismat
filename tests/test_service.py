from pathlib import Path

from prize_bond_checker.history import HistoryStore
from prize_bond_checker.portfolio import load_portfolio
from prize_bond_checker.scraper import parse_draw_html
from prize_bond_checker.service import check_portfolio

FIXTURES = Path(__file__).parent / "fixtures"


def test_check_portfolio_records_win_and_can_skip(tmp_path: Path):
    bonds = tmp_path / "bonds.txt"
    bonds.write_text("[200]\n022667\n123456\n", encoding="utf-8")
    html = (FIXTURES / "sample_draw.html").read_text(encoding="utf-8")
    store = HistoryStore(tmp_path / "history.sqlite")
    portfolio = load_portfolio(bonds)

    outcomes = check_portfolio(
        portfolio,
        denomination=200,
        draw_date="2026-03-16",
        use_latest=False,
        history=store,
        fetch_html=lambda *args, **kwargs: html,
        fetch_latest=lambda *args, **kwargs: "2026-03-16",
        parse_html=parse_draw_html,
    )

    assert len(outcomes) == 1
    assert outcomes[0].error is None
    assert [win.bond for win in outcomes[0].wins] == ["022667"]
    assert store.has_check(200, "2026-03-16") is True

    skipped = check_portfolio(
        portfolio,
        denomination=200,
        draw_date="2026-03-16",
        use_latest=False,
        history=store,
        skip_checked=True,
        fetch_html=lambda *args, **kwargs: html,
        parse_html=parse_draw_html,
    )
    assert skipped[0].skipped is True


def test_check_all_uses_each_section(tmp_path: Path):
    bonds = tmp_path / "bonds.txt"
    bonds.write_text("[200]\n022667\n[750]\n111111\n", encoding="utf-8")
    html = (FIXTURES / "sample_draw.html").read_text(encoding="utf-8")
    portfolio = load_portfolio(bonds)
    seen: list[int] = []

    def fake_latest(denomination: int) -> str:
        seen.append(denomination)
        return "2026-03-16"

    outcomes = check_portfolio(
        portfolio,
        check_all=True,
        fetch_html=lambda *args, **kwargs: html,
        fetch_latest=fake_latest,
        parse_html=parse_draw_html,
    )
    assert [item.denomination for item in outcomes] == [200, 750]
    assert seen == [200, 750]
