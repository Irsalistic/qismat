"""Compare owned bonds against a draw result."""

from __future__ import annotations

from prize_bond_checker.constants import PRIZE_AMOUNTS
from prize_bond_checker.models import DrawResult, Win


def find_wins(bonds: set[str], draw: DrawResult) -> list[Win]:
    amounts = PRIZE_AMOUNTS.get(draw.denomination, PRIZE_AMOUNTS[200])
    wins: list[Win] = []

    for tier in ("1st", "2nd", "3rd"):
        for bond in sorted(bonds & draw.prizes[tier]):
            wins.append(Win(bond=bond, tier=tier, amount=amounts[tier]))

    return wins
