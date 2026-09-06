"""Shared add/list helpers for the dashboard, CLI, and MCP server."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from qismat.constants import DEFAULT_BONDS_FILE, DEFAULT_DENOMINATION, HISTORY_FILENAME
from qismat.history import HistoryStore
from qismat.portfolio import add_holding, load_portfolio, remove_holding
from qismat.voice import SpokenAdd, parse_spoken_add, spoken_confirmation


@dataclass
class AddResult:
    added: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    denomination: int = DEFAULT_DENOMINATION
    owner: str | None = None
    heard: str | None = None
    warnings: list[str] = field(default_factory=list)
    confirmation: str = ""

    @property
    def message(self) -> str:
        bits: list[str] = []
        if self.added:
            bits.append("Added " + ", ".join(self.added))
        if self.skipped:
            bits.append("already in the list: " + ", ".join(self.skipped))
        text = "; ".join(bits) if bits else "No bonds changed."
        if self.owner:
            text += f" ({self.owner})"
        text += f" · Rs. {self.denomination}"
        return text


def resolve_bonds_file(explicit: Path | None = None) -> Path:
    if explicit:
        return explicit
    cwd_file = Path.cwd() / DEFAULT_BONDS_FILE
    if cwd_file.exists():
        return cwd_file
    package_root = Path(__file__).resolve().parents[2]
    return package_root / DEFAULT_BONDS_FILE


def history_file_for(bonds_file: Path) -> Path:
    return bonds_file.with_name(HISTORY_FILENAME)


def add_numbers(
    path: Path,
    numbers: list[str],
    denomination: int = DEFAULT_DENOMINATION,
    owner: str | None = None,
) -> AddResult:
    result = AddResult(denomination=denomination, owner=owner)
    for number in numbers:
        if add_holding(path, number, denomination, owner):
            result.added.append(number)
        else:
            result.skipped.append(number)
    return result


def add_from_speech(
    path: Path,
    transcript: str,
    default_denomination: int = DEFAULT_DENOMINATION,
    default_owner: str | None = None,
) -> AddResult:
    parsed: SpokenAdd = parse_spoken_add(transcript)
    denomination = parsed.denomination or default_denomination
    owner = parsed.owner or default_owner
    result = add_numbers(path, parsed.numbers, denomination, owner)
    result.heard = parsed.heard
    result.warnings = parsed.warnings
    result.confirmation = spoken_confirmation(parsed, denomination)
    return result


def portfolio_payload(path: Path) -> dict:
    payload: dict = {"file": str(path), "exists": path.exists(), "bonds": [], "count": 0}
    if not path.exists():
        return payload
    try:
        portfolio = load_portfolio(path)
    except ValueError:
        return payload
    rows = []
    for item in portfolio.holdings:
        rows.append(
            {
                "number": item.number,
                "denomination": item.denomination,
                "owner": item.owner,
            }
        )
    payload["bonds"] = rows
    payload["count"] = len(rows)
    payload["denominations"] = portfolio.denominations()
    return payload


def history_payload(path: Path, limit: int = 20) -> dict:
    store = HistoryStore(history_file_for(path))
    stats = store.stats()
    return {
        "check_count": stats.check_count,
        "win_count": stats.win_count,
        "last_checked_at": stats.last_checked_at,
        "checks": [
            {
                "checked_at": item.checked_at,
                "denomination": item.denomination,
                "draw_date": item.draw_date,
                "draw_number": item.draw_number,
                "city": item.city,
                "bond_count": item.bond_count,
                "win_count": item.win_count,
            }
            for item in store.recent_checks(limit)
        ],
        "wins": [
            {
                "bond": item.bond,
                "tier": item.tier,
                "amount": item.amount,
                "owner": item.owner,
                "denomination": item.denomination,
                "draw_date": item.draw_date,
            }
            for item in store.all_wins(limit)
        ],
    }


def remove_number(path: Path, number: str, denomination: int | None = None) -> bool:
    return remove_holding(path, number, denomination)
