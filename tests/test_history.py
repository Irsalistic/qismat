from pathlib import Path

from qismat.history import HistoryStore
from qismat.models import DrawResult, Win


def test_history_records_checks_and_wins(tmp_path: Path):
    store = HistoryStore(tmp_path / "history.sqlite")
    draw = DrawResult(
        denomination=200,
        draw_date="2026-03-16",
        draw_number="105",
        city="Faisalabad",
        prizes={"1st": set(), "2nd": set(), "3rd": {"022667"}},
    )
    wins = [Win(bond="022667", tier="3rd", amount="Rs. 1,250", owner="ali")]

    store.record(draw, bond_count=2, wins=wins, source_url="https://example.test")

    assert store.has_check(200, "2026-03-16") is True
    assert store.has_check(200, "2026-06-15") is False

    stats = store.stats()
    assert stats.check_count == 1
    assert stats.win_count == 1
    assert stats.denominations == [200]

    recent = store.recent_checks()
    assert recent[0].city == "Faisalabad"
    assert recent[0].win_count == 1

    ledger = store.all_wins()
    assert ledger[0].bond == "022667"
    assert ledger[0].owner == "ali"
