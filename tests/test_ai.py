from pathlib import Path

import pytest

from prize_bond_checker.ai.ask import parse_natural_language
from prize_bond_checker.ai.summary import fallback_summary, generate_summary
from prize_bond_checker.latest import _extract_draw_dates, fetch_latest_draw_date
from prize_bond_checker.scraper import parse_draw_html

FIXTURES = Path(__file__).parent / "fixtures"


def test_extract_latest_draw_date_from_homepage_fixture():
    html = (FIXTURES / "sample_homepage.html").read_text(encoding="utf-8")
    dates = _extract_draw_dates(html, denomination=200)
    assert dates == {"2026-06-15", "2026-03-16"}
    assert max(dates) == "2026-06-15"


def test_parse_natural_language_without_ai():
    parsed = parse_natural_language("check my 200 bonds for the latest draw", provider=None)
    assert parsed.denomination == 200
    assert parsed.use_latest is True
    assert parsed.draw_date is None


def test_parse_natural_language_with_explicit_date():
    parsed = parse_natural_language("check 200 bonds on 2026-03-16", provider=None)
    assert parsed.denomination == 200
    assert parsed.draw_date == "2026-03-16"
    assert parsed.use_latest is False


def test_fallback_summary_no_wins():
    html = (FIXTURES / "sample_draw.html").read_text(encoding="utf-8")
    draw = parse_draw_html(html, denomination=200, draw_date="2026-03-16")
    summary = fallback_summary(31, draw, wins=[])

    assert "31 bond" in summary
    assert "No matches" in summary
    assert "105" in summary or "2026-03-16" in summary


def test_generate_summary_without_provider_uses_fallback():
    html = (FIXTURES / "sample_draw.html").read_text(encoding="utf-8")
    draw = parse_draw_html(html, denomination=200, draw_date="2026-03-16")

    summary, used_ai = generate_summary(2, draw, wins=[], provider=None)
    assert used_ai is False
    assert "No matches" in summary


def test_fetch_latest_draw_date_raises_when_missing(monkeypatch):
    class FakeResponse:
        ok = True
        text = "<html><body>No draws here</body></html>"

        @staticmethod
        def raise_for_status():
            return None

    monkeypatch.setattr("prize_bond_checker.latest.requests.get", lambda *a, **k: FakeResponse())

    with pytest.raises(ValueError, match="Could not find"):
        fetch_latest_draw_date(200)
