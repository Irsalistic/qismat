"""Shared check pipeline used by the CLI and the local dashboard."""

from __future__ import annotations

from dataclasses import dataclass, field

import requests

from qismat.checker import find_wins
from qismat.constants import BASE_URL, DEFAULT_DENOMINATION
from qismat.history import HistoryStore
from qismat.latest import fetch_latest_draw_date
from qismat.models import DrawResult, Win
from qismat.portfolio import Portfolio
from qismat.scraper import fetch_draw_html, parse_draw_html


@dataclass
class CheckOutcome:
    denomination: int
    bond_count: int
    draw_date: str | None = None
    draw: DrawResult | None = None
    wins: list[Win] = field(default_factory=list)
    skipped: bool = False
    error: str | None = None
    source_url: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None

    def to_dict(self) -> dict:
        draw = self.draw
        return {
            "denomination": self.denomination,
            "bond_count": self.bond_count,
            "draw_date": self.draw_date,
            "draw_number": draw.draw_number if draw else None,
            "city": draw.city if draw else None,
            "prize_summary": draw.summary() if draw else None,
            "wins": [
                {
                    "bond": win.bond,
                    "tier": win.tier,
                    "amount": win.amount,
                    "owner": win.owner,
                }
                for win in self.wins
            ],
            "skipped": self.skipped,
            "error": self.error,
            "source_url": self.source_url,
        }


def check_denomination(
    bonds: set[str],
    denomination: int,
    *,
    draw_date: str | None = None,
    use_latest: bool = False,
    owners: dict[str, str] | None = None,
    history: HistoryStore | None = None,
    skip_checked: bool = False,
    fetch_html=fetch_draw_html,
    fetch_latest=fetch_latest_draw_date,
    parse_html=parse_draw_html,
) -> CheckOutcome:
    if not bonds:
        return CheckOutcome(
            denomination=denomination,
            bond_count=0,
            error="No bonds to check for this denomination.",
        )

    try:
        resolved_date = fetch_latest(denomination) if use_latest or not draw_date else draw_date
    except (requests.RequestException, ValueError) as exc:
        return CheckOutcome(
            denomination=denomination,
            bond_count=len(bonds),
            draw_date=draw_date,
            error=f"Could not find latest draw: {exc}",
        )

    source_url = BASE_URL.format(denomination=denomination, draw_date=resolved_date)
    if skip_checked and history is not None and history.has_check(denomination, resolved_date):
        return CheckOutcome(
            denomination=denomination,
            bond_count=len(bonds),
            draw_date=resolved_date,
            skipped=True,
            source_url=source_url,
        )

    try:
        html = fetch_html(denomination, resolved_date)
        draw = parse_html(html, denomination, resolved_date)
    except requests.RequestException as exc:
        return CheckOutcome(
            denomination=denomination,
            bond_count=len(bonds),
            draw_date=resolved_date,
            error=f"Failed to fetch draw: {exc}",
            source_url=source_url,
        )
    except ValueError as exc:
        return CheckOutcome(
            denomination=denomination,
            bond_count=len(bonds),
            draw_date=resolved_date,
            error=f"Parse error: {exc}",
            source_url=source_url,
        )

    wins = find_wins(bonds, draw, owners)
    if history is not None:
        history.record(draw, len(bonds), wins, source_url=source_url)

    return CheckOutcome(
        denomination=denomination,
        bond_count=len(bonds),
        draw_date=resolved_date,
        draw=draw,
        wins=wins,
        source_url=source_url,
    )


def check_portfolio(
    portfolio: Portfolio,
    *,
    denomination: int | None = None,
    draw_date: str | None = None,
    use_latest: bool = False,
    check_all: bool = False,
    history: HistoryStore | None = None,
    skip_checked: bool = False,
    default_denomination: int = DEFAULT_DENOMINATION,
    fetch_html=fetch_draw_html,
    fetch_latest=fetch_latest_draw_date,
    parse_html=parse_draw_html,
) -> list[CheckOutcome]:
    if check_all:
        grouped = portfolio.grouped(default_denomination)
        targets = list(grouped.keys())
    else:
        target = denomination or default_denomination
        grouped = {target: portfolio.holdings_for(target, include_unsectioned=True)}
        targets = [target]

    outcomes: list[CheckOutcome] = []
    for denom in targets:
        holdings = grouped.get(denom, [])
        bonds = {item.number for item in holdings}
        owners = {item.number: item.owner for item in holdings if item.owner}
        outcomes.append(
            check_denomination(
                bonds,
                denom,
                draw_date=None if check_all else draw_date,
                use_latest=use_latest or check_all or not draw_date,
                owners=owners,
                history=history,
                skip_checked=skip_checked,
                fetch_html=fetch_html,
                fetch_latest=fetch_latest,
                parse_html=parse_html,
            )
        )
    return outcomes
