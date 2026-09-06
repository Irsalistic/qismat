from qismat.cli import build_parser, resolve_settings
from qismat.notify import format_alert
from qismat.service import CheckOutcome


def test_parser_accepts_new_flags():
    args = build_parser().parse_args(["--all", "--latest", "--notify", "--skip-checked"])
    assert args.check_all is True
    assert args.notify is True
    assert args.skip_checked is True


def test_default_all_when_portfolio_has_sections():
    args = build_parser().parse_args([])
    denomination, draw_date, want_summary, check_all = resolve_settings(args, True)
    assert check_all is True
    assert want_summary is True
    assert denomination is None


def test_format_alert_skipped_draw():
    text = format_alert(
        [CheckOutcome(denomination=200, bond_count=4, draw_date="2026-06-15", skipped=True)]
    )
    assert "skipped" in text.lower()
    assert "No wins" in text
