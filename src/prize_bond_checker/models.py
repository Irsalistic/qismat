"""Data models for draw results."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Win:
    bond: str
    tier: str
    amount: str
    owner: str | None = None


@dataclass
class DrawResult:
    denomination: int
    draw_date: str
    draw_number: str | None = None
    city: str | None = None
    prizes: dict[str, set[str]] = field(default_factory=lambda: {"1st": set(), "2nd": set(), "3rd": set()})

    @property
    def total_winners(self) -> int:
        return sum(len(numbers) for numbers in self.prizes.values())

    def summary(self) -> str:
        return (
            f"1st={len(self.prizes['1st'])} winner(s), "
            f"2nd={len(self.prizes['2nd'])} winner(s), "
            f"3rd={len(self.prizes['3rd'])} winner(s)"
        )

    def top_winners(self) -> dict[str, list[str]]:
        return {tier: sorted(numbers) for tier, numbers in self.prizes.items() if tier in ("1st", "2nd")}
